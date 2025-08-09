from __future__ import annotations

from payments import stripewrapper

from django import forms

from payments.models import MembershipInformation

from alumni.fields import PaymentTypeField

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class MembershipInformationForm(forms.ModelForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.fields["tier"].help_text = None

    class Meta:
        model = MembershipInformation
        fields = ["tier"]


class PaymentMethodForm(forms.Form):
    pass


class CancellablePaymentMethodForm(PaymentMethodForm):
    pass
