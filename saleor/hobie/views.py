from django.http import Http404, HttpResponse
from .utils import export_orders_ready_to_fulfill_to_csv


from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse

from ..checkout.views.discount import add_voucher_form, validate_voucher

from ..checkout.models import Checkout

from ..checkout.forms import CheckoutShippingMethodForm

from ..checkout.utils import (
    get_checkout_context,
    update_shipping_address_in_anonymous_checkout,
    update_shipping_address_in_checkout,
    get_or_empty_db_checkout,
    is_valid_shipping_method,
    update_billing_address_in_anonymous_checkout,
    
)

from ..checkout.views.validators import (
    validate_checkout,
    validate_is_shipping_required,
    validate_shipping_address,
    validate_shipping_method,
)

def export_orders_to_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment;filename="hobie_cat_orders.csv"'
    response.content = export_orders_ready_to_fulfill_to_csv()      

    if len(response.content) == 0:
        raise Http404

    return response

#HOBIE from saleor/checkout/views.py
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

    if updated:
        return redirect("checkout:hobie-billing")

    ctx = get_checkout_context(checkout, request.discounts)
    ctx.update({"address_form": address_form, "user_form": user_form})

    discounts = request.discounts
    is_valid_shipping_method(checkout, discounts)

    form = CheckoutShippingMethodForm(
        request.POST or None,
        discounts=discounts,
        instance=checkout,
        initial={"shipping_method": checkout.shipping_method},
    )
    if form.is_valid():
        form.save()
        return redirect("checkout:hobie-billing")

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

    user_form, address_form, updated = update_billing_address_in_anonymous_checkout(
        checkout, request.POST or None, request.country
    )

    #if updated:
    #    return _handle_order_placement(request, checkout)

    ctx = get_checkout_context(checkout, request.discounts)
    ctx.update(
        {"address_form": address_form, "note_form": note_form, "user_form": user_form}
    )
    return TemplateResponse(request, "hobie/billing.html", ctx)