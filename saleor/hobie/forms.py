
from django.utils.translation import npgettext_lazy, pgettext_lazy
from django import forms
from ..shipping.models import ShippingMethod
from ..checkout.forms import ShippingMethodChoiceField
from ..checkout.models import Checkout

class CheckoutShippingMethodForm(forms.ModelForm):
    shipping_method = ShippingMethodChoiceField(
        queryset=ShippingMethod.objects.all(),
        label=pgettext_lazy("Shipping method form field label", "Shipping method"),
        empty_label=None,
    )

    class Meta:
        model = Checkout
        fields = ["shipping_method"]

    def __init__(self, *args, **kwargs):
        discounts = kwargs.pop("discounts")
        super().__init__(*args, **kwargs)
        #shipping_address = self.instance.shipping_address #HOBIE commented out
        #country_code = shipping_address.country.code #HOBIE commendted out
        country_code = 'US' #HOBIE
        shipping_address = None #HOBIE 
        qs = ShippingMethod.objects.applicable_shipping_methods(
            price=calculate_checkout_subtotal(self.instance, discounts).gross,
            weight=self.instance.get_total_weight(),
            country_code=country_code,
        )
        self.fields["shipping_method"].queryset = qs
        self.fields["shipping_method"].shipping_address = shipping_address

        if self.initial.get("shipping_method") is None:
            shipping_methods = qs.all()
            if shipping_methods:
                self.initial["shipping_method"] = shipping_methods[0]