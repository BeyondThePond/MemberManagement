import base64
import uuid
from os import path
from typing import Iterable

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.db.models import signals
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.template import Context

from datetime import datetime
from django.utils.timezone import get_current_timezone

from djmoney.models import fields
from django.conf import settings

from djmoney.money import Money

import pdfrender

from MemberManagement import mailutils
from payments.models import PaymentIntent
from registry.models import Alumni

from .utils import _convert_to_written

STRIPE = "stripe"
BANK_ACCOUNT = "bank"
OTHER = "other"

# A list of choices for funding sources
_PAYMENT_STREAMS = (
    (STRIPE, "Stripe"),
    (BANK_ACCOUNT, "Bank Account"),
    (OTHER, "Other"),
)


# Create your models here.
class DonationReceipt(models.Model):
    external_id = models.UUIDField(default=uuid.uuid4, editable=False)
    payment_stream = models.CharField(max_length=32, choices=_PAYMENT_STREAMS)
    payment_reference = models.CharField(
        max_length=256,
        help_text=_(
            "The unique reference to this payment. \
For bank accounts, use the SEPA transfer ID. For other payment sources, leave a short note."
        ),
    )

    received_on = models.DateField(help_text=_("The day this donation was received."))
    received_from = models.ForeignKey(
        get_user_model(),
        help_text=_(
            "The user that this donation receipt should be shown to in the portal."
        ),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    issued_on = models.DateField(
        help_text=_("The day this receipt was issued."), auto_now=True
    )

    # Once finalized = True, all changes via Django admin will be blocked
    finalized = models.BooleanField(
        help_text=_("Once finalized, the receipt details will no longer be editable."),
        default=False,
    )

    email_name = models.CharField(
        help_text=_('How to adress the person donating, as in "Dear email name"'),
        max_length=64,
        default="",
    )
    email_to = models.EmailField(
        help_text=_("The email address to send the receipt to."), default=""
    )
    email_sent = models.BooleanField(
        help_text=_("If this is ticked, an email has been sent."), default=False
    )

    # Internal memo field - can stay empty
    internal_notes = models.TextField(blank=True)

    # Decimal(14, 4) is GAAP standard
    amount = fields.MoneyField(max_digits=14, decimal_places=4, default_currency="EUR")

    sender_info = models.TextField(
        help_text=_(
            "The full name and postal address of the donation sender, on multiple lines of text."
        )
    )

    receipt_pdf = models.FileField(editable=False)

    def _generate_pdf(self):
        context = {"receipt": self, "portal_version": settings.PORTAL_VERSION}

        if settings.DEBUG or settings.ENABLE_DEVEL_WARNING:
            context.update({"giant_floating_text": "MUSTER"})

        with open(settings.SIGNATURE_IMAGE, "rb") as sig_image:
            encoded = base64.b64encode(sig_image.read())
            context["sig_image_b64"] = "data:image/png;base64," + encoded.decode(
                "ascii"
            )

        f = ContentFile(
            pdfrender.render_to_bytes(
                settings.DONATION_RECEIPT_TEMPLATE, context=context
            )
        )

        self.receipt_pdf.save("receipt-{}.pdf".format(self.external_id), f)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.finalized and not self.receipt_pdf:
            self._generate_pdf()

    def __str__(self):
        return str(self.external_id)

    @property
    def download_filename(self):
        return "Beyond the Pond Donation Receipt {date}.pdf".format(
            date=self.received_on
        )


def _get_donating_alum(stripe_customer_id):
    return Alumni.objects.get(membership__customer=stripe_customer_id)


@receiver(signals.post_save, sender="alumni.Address")
def _trigger_receipt_generation(sender, instance, created, **kwargs):
    """When a previously missing address becomes available, check to see if we can generate more receipts now"""

    if kwargs.get("raw", False):
        return

    try:
        stripe_customer_id = instance.member.membership.customer

        pis: Iterable[PaymentIntent] = PaymentIntent.objects.filter(
            data__customer=stripe_customer_id
        )
        for pi in pis:
            _maybe_generate_donation_receipt(sender, pi, False)
    except ObjectDoesNotExist:
        pass


@receiver(signals.post_save, sender="payments.PaymentIntent")
def _maybe_generate_donation_receipt(sender, instance, created, **kwargs):
    if kwargs.get("raw", False):
        return

    data = instance.data

    if data["status"] != "succeeded" or data["currency"] != "eur":
        return

    try:
        donation_sender = _get_donating_alum(data["customer"])
    except Alumni.DoesNotExist:
        return

    try:
        if not donation_sender.address:
            return
    except ObjectDoesNotExist:
        return

    if not donation_sender.address.is_filled():
        return

    create_date = datetime.fromtimestamp(data["created"], tz=get_current_timezone())
    if not create_date:
        return

    amount = Money(
        amount=data["amount_received"] / 100, currency=data["currency"].upper()
    )

    sender_info = (
        donation_sender.fullName + "\n" + donation_sender.address.envelope_format
    )

    receipt, created = DonationReceipt.objects.get_or_create(
        payment_stream=STRIPE,
        payment_reference=data["id"],
        defaults={
            "received_on": create_date,
            "received_from": donation_sender.profile,
            "sender_info": sender_info,
            "amount": amount,
            "email_to": donation_sender.email,
            "email_name": donation_sender.givenName,
        },
    )

    if receipt.finalized:
        return

    receipt.finalized = settings.FINALIZE_AUTOMATICALLY

    receipt.save()


@receiver(signals.post_save, sender=DonationReceipt)
def _maybe_email_donation_receipt(sender, instance, created, **kwargs):
    if kwargs.get("raw", False):
        return

    receipt = instance
    if receipt.receipt_pdf and not receipt.email_sent:
        mail = mailutils.prepare_email(
            receipt.email_to,
            "Beyond the Pond Alumni Association - Donation Receipt",
            "emails/new_receipt.html",
            receipt=receipt,
        )

        pdf = receipt.receipt_pdf
        pdf.open()

        mail.attach(receipt.download_filename, pdf.read(), "application/pdf")

        mail.send()

        receipt.email_sent = True
        receipt.save()
