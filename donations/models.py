import datetime
from uuid import uuid4

import stripe
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext
from djmoney.models import fields as money_fields

from MemberManagement import mailutils
from alumni import models as alumni_models
from donation_receipts.models import _get_donating_alum


class DonationTarget(models.Model):
    """These are options a user can choose to donate towards"""

    label = models.CharField(max_length=512)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class Donation(models.Model):
    """These are created when a user fires a donation. We create a Stripe checkout session and send them there."""

    # This can be used to build a success URL for Stripe Checkout
    external_id = models.UUIDField(default=uuid4)

    # A user can specify what to donate towards - or leave it blank
    target = models.ForeignKey(
        DonationTarget,
        verbose_name=gettext("Donating towards"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        limit_choices_to={"active": True},
    )
    amount = money_fields.MoneyField(
        max_digits=10,
        decimal_places=2,
        currency_choices=(
            ("EUR", "Euros"),
            ("USD", "US Dollars"),
        ),
        default_currency="EUR",
        help_text='Use "." as the decimal separator, i.e. "1000.23" means 1000 Euros and 23 Cents. ',
    )

    # Anonymous donations get linked to a stripe customer with this
    # This also gives us the anonymous user email
    payment_id = models.CharField(max_length=64)

    # When the donation has been processed successfully, this is set.
    completed = models.DateTimeField(null=True, blank=True)

    # Alumni donations use the existing donation receipt flow, no fields required here


@receiver(signals.post_save, sender="payments.PaymentIntent")
def _maybe_complete_donation(sender, instance, created, **kwargs):
    data = instance.data

    if data["status"] == "succeeded":
        try:
            donation = Donation.objects.get(payment_id=data["id"])
            donation.completed = datetime.datetime.now()
            donation.save()
        except Donation.DoesNotExist:
            pass


@receiver(signals.post_save, sender="donations.Donation")
def _maybe_email_donor(sender, instance: Donation, created, **kwargs):
    if not instance.completed:
        return

    pi: stripe.PaymentIntent = stripe.PaymentIntent.retrieve(instance.payment_id)

    try:
        alum = _get_donating_alum(pi.customer)

        if alum:
            return

    except alumni_models.Alumni.DoesNotExist:
        pass

    receipt_email = pi.receipt_email

    domain = Site.objects.get_current().domain

    mail = mailutils.prepare_email(
        receipt_email,
        "Beyond the Pond Alumni Association - Thank You!",
        "emails/donation_complete.html",
        object=instance,
        domain=domain,
    )

    mail.send()
