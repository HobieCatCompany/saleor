from django.http import Http404, HttpResponse
from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.utils.translation import pgettext
from .utils import export_orders_ready_to_fulfill_to_csv


from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse

from ..account.models import Address, User
from ..checkout.views.discount import add_voucher_form, validate_voucher

from ..checkout.models import Checkout
from ..core import analytics
from ..core.utils import get_client_ip
from ..core.exceptions import InsufficientStock
from ..core.taxes.errors import TaxError
from ..core.taxes import zero_taxed_money
from ..core.taxes.interface import (
    calculate_checkout_total,
)

from ..discount.models import NotApplicable
from .forms import CheckoutShippingMethodForm

from ..checkout.utils import (
    get_checkout_context,
    update_shipping_address_in_anonymous_checkout,
    update_shipping_address_in_checkout,
    get_or_empty_db_checkout,
    is_valid_shipping_method,
    update_billing_address_in_checkout_with_shipping,
    create_order,
    prepare_order_data,
)

from ..checkout.views.validators import (
    validate_checkout,
    validate_is_shipping_required,
    validate_shipping_address,
    validate_shipping_method,
)

from ..order.emails import send_order_confirmation
from ..payment import ChargeStatus, TransactionKind, get_payment_gateway
from ..payment.interface import AddressData
from ..payment.utils import (
    create_payment,
    create_payment_information,
    gateway_process_payment,
)

def export_orders_to_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment;filename="hobie_cat_orders.csv"'
    response.content = export_orders_ready_to_fulfill_to_csv()      

    if len(response.content) == 0:
        raise Http404

    return response

@get_or_empty_db_checkout(Checkout.objects.for_display())
@validate_voucher
@validate_checkout
@validate_is_shipping_required
@add_voucher_form
def shipping(request, checkout):
    """Display the shipping step for a user who is not logged in."""
    user_form, address_form, updated = update_shipping_address_in_anonymous_checkout(
        checkout, request.POST or None, request.country
    )

    discounts = request.discounts
    is_valid_shipping_method(checkout, discounts)

    form = CheckoutShippingMethodForm(
        request.POST or None,
        discounts=discounts,
        instance=checkout,
        initial={"shipping_method": checkout.shipping_method},
    )

    if updated and form.is_valid():
        form.save()
        return redirect("checkout:hobie-billing")

    ctx = get_checkout_context(checkout, request.discounts)
    ctx.update({"address_form": address_form, "user_form": user_form})

    ctx.update({"shipping_method_form": form})

    return TemplateResponse(request, "hobie/shipping.html", ctx)


@get_or_empty_db_checkout(Checkout.objects.for_display())
@validate_voucher
@validate_checkout
@add_voucher_form
def billing(request, checkout):
    """Display order summary with billing forms for an unauthorized user.

    Will create an order if all data is valid.
    """
    #note_form = CheckoutNoteForm(request.POST or None, instance=checkout)
    #if note_form.is_valid():
    #    note_form.save()

    user_addresses = (
        checkout.user.addresses.all() if checkout.user else Address.objects.none()
    )

    addresses_form, address_form, updated = update_billing_address_in_checkout_with_shipping(  # noqa
        checkout, user_addresses, request.POST or None, request.country
    )

    if updated:
        return redirect("checkout:hobie-payment")

    ctx = get_checkout_context(checkout, request.discounts)
    ctx.update(
        {
            "additional_addresses": user_addresses,
            "address_form": address_form,
            "addresses_form": addresses_form,
            #"note_form": note_form,
        }
    )
    return TemplateResponse(request, "hobie/billing.html", ctx)


@get_or_empty_db_checkout(Checkout.objects.for_display())
@validate_voucher
@validate_checkout
@add_voucher_form
def start_payment(request, checkout):
    payment_gateway, gateway_config = get_payment_gateway('stripe')
    connection_params = gateway_config.connection_params
    extra_data = {"customer_user_agent": request.META.get("HTTP_USER_AGENT")}

    checkout_total = (
        calculate_checkout_total(checkout=checkout, discounts=request.discounts)
        - checkout.get_total_gift_cards_balance()
    )

    checkout_total = max(checkout_total, zero_taxed_money(checkout_total.currency))

    with transaction.atomic():
        payment = create_payment(
            gateway='stripe',
            currency=checkout_total.gross.currency,
            email=checkout.email,
            billing_address=checkout.billing_address,
            customer_ip_address=get_client_ip(request),
            total=checkout_total.gross.amount,
            checkout=checkout,
            extra_data=extra_data,
        )

        #if (
        #    order.is_fully_paid()
        #    or payment.charge_status == ChargeStatus.FULLY_REFUNDED
        #):
        #    return redirect(order.get_absolute_url())

        payment_info = create_payment_information(payment, billing_address=AddressData(**checkout.billing_address.as_data()), shipping_address=AddressData(**checkout.shipping_address.as_data()))
        form = payment_gateway.create_form(
            data=request.POST or None,
            payment_information=payment_info,
            connection_params=connection_params,
        )
        if form.is_valid():
            try:
                gateway_process_payment(
                    payment=payment, payment_token=form.get_payment_token()
                )
            except Exception as exc:
                form.add_error(None, str(exc))
            else:
                order = _handle_order_placement(request, checkout)
                transaction.on_commit(lambda: send_order_confirmation.delay(order.pk))
                return redirect("order:payment-success", token=order.token)

    client_token = payment_gateway.get_client_token(config=gateway_config)

    ctx = get_checkout_context(checkout, request.discounts)

    ctx.update({
        "form": form,
        "payment": payment,
        "client_token": settings.PAYMENT_GATEWAYS['stripe']['config']['connection_params']['public_key'],
        #"order": order,
    })

    return TemplateResponse(request, "hobie/payment.html", ctx)


@transaction.atomic()
def _handle_order_placement(request, checkout):
    """Try to create an order and redirect the user as necessary.

    This function creates an order from checkout and performs post-create actions
    such as removing the checkout instance, sending order notification email
    and creating order history events.
    """
    try:
        # Run checks an prepare the data for order creation
        order_data = prepare_order_data(
            checkout=checkout,
            tracking_code=analytics.get_client_id(request),
            discounts=request.discounts,
        )
    except InsufficientStock:
        return redirect("checkout:index")
    except NotApplicable:
        messages.warning(
            request, pgettext("Checkout warning", "Please review your checkout.")
        )
        return redirect("checkout:summary")
    except TaxError as tax_error:
        messages.warning(
            request,
            pgettext(
                "Checkout warning", "Unable to calculate taxes - %s" % str(tax_error)
            ),
        )
        return redirect("checkout:summary")

    # Push the order data into the database
    order = create_order(checkout=checkout, order_data=order_data, user=request.user)

    # remove checkout after order is created
    checkout.delete()

    return order