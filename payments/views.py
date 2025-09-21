from __future__ import annotations

from datetime import datetime

from django.forms import Form
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.utils import formats
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView, RedirectView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from django.conf import settings

from alumni.fields import TierField, AlumniCategoryField
from payments import stripewrapper
from registry.decorators import require_setup_completed
from registry.views.setup import SetupComponentView

from MemberManagement.mixins import RedirectResponseMixin

from .forms import (
    MembershipInformationForm,
    PaymentMethodForm,
    CancellablePaymentMethodForm,
)
from .models import SubscriptionInformation, PaymentIntent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict, Any, Optional, Tuple, List
    from .models import MembershipInformation
    from django.http import HttpResponse
from django.http import HttpResponseRedirect
import stripe


class SignupView(SetupComponentView):
    setup_name = "Tier Selection"
    setup_subtitle = "How much do you want to support us?"
    setup_form_class = MembershipInformationForm

    template_name = "payments/tier.html"

    def get_context(self, form: MembershipInformationForm) -> Dict[str, Any]:
        context = super().get_context(form)
        context.update({"confirm_text": "Confirm Membership", "updating": False})
        return context

    def form_valid(
        self, form: MembershipInformationForm
    ) -> Optional[MembershipInformation]:

        # Create the stripe customer
        customer, err = stripewrapper.create_customer(self.request.user.alumni)
        if err is not None:
            form.add_error(
                None,
                "Something went wrong when talking to our payment service provider. Please try again later or contact support. ",
            )
            return None

        # store the information
        instance = form.save(commit=False)
        instance.member = self.request.user.alumni
        instance.customer = customer
        instance.save()

        # if we selected the starter tier, create subscription information now
        if instance.tier == TierField.STARTER:
            SubscriptionInformation.create_starter_subscription(
                self.request.user.alumni
            )

        return instance


class SubscribeView(SetupComponentView):
    setup_name = "Payment Information"
    setup_subtitle = ""
    setup_form_class = Form
    setup_next_text = "CONFIRM MEMBERSHIP & AUTHORIZE PAYMENT NOW"

    template_name = "payments/subscribe.html"

    def get_context(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context(*args, **kwargs)
        context.update(
            {
                "alumni": self.request.user.alumni,
                "allow_go_to_starter": True,
            }
        )
        return context

    @classmethod
    def setup_class(cls) -> SubscriptionInformation:
        return SubscriptionInformation

    def should_setup_component(self) -> bool:
        """Check if we should setup this component"""

        # Use Django queries to check if any active subscription exists
        now = datetime.now()
        if self.request.user.alumni.subscriptioninformation_set.filter(
            start__lte=now, end__gte=now
        ).exists():
            return False

        alumni = self.request.user.alumni

        # Call the Stripe API with the customer ID and sync with local SubscriptionInformation
        subscription = SubscriptionInformation.sync_from_stripe(alumni)

        if subscription is None:
            return True

        # If we now have an active subscription, we do not need to set up the component
        if (
            subscription.start is not None
            and subscription.start <= now
            and (subscription.end is None or subscription.end >= now)
        ):
            return False

        # By default, we should set up the component
        return True

    def form_valid(self, form: CancellablePaymentMethodForm) -> Optional[str]:
        """Form has been validated"""

        # Create a Stripe portal session for the user to complete subscription
        membership = self.request.user.alumni.membership
        customer_id = membership.customer

        # Build return URL to redirect back after portal session
        return_url = self.request.build_absolute_uri(reverse("setup_subscription"))

        # Determine the price ID dynamically based on the tier the user selected
        tier = membership.tier
        price_id_map = {
            TierField.CONTRIBUTOR: settings.STRIPE_CONTRIBUTOR_PRICE_ID,
            TierField.PATRON: settings.STRIPE_PATRON_PRICE_ID,
            TierField.STARTER: settings.STRIPE_STARTER_PRICE_ID,
        }
        price_id = price_id_map.get(tier)

        if not price_id:
            form.add_error(
                None,
                "Invalid membership tier selected. Please contact support. ",
            )
            return None

        # Create the portal session via the Stripe API directly
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                mode="subscription",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                success_url=return_url,
                cancel_url=return_url,
            )
            portal_url = session.url
            err = None
        except Exception as e:
            portal_url = None
            err = str(e)

        if err is not None or not portal_url:
            form.add_error(
                None,
                "Something went wrong when creating the checkout session. Please try again later or contact support. ",
            )
            return None

        # Redirect the user to the Stripe portal session
        return portal_url

    def dispatch_success(self, validated: str) -> HttpResponse:
        """Called on True-ish return of form_valid() with the returned value"""

        return self.redirect_response(validated, reverse=False)


class PaymentsTableMixin:
    @classmethod
    def format_datetime(cls, epoch: int, format: str = "DATETIME_FORMAT") -> str:
        """Formats seconds since epoch as a readable date"""
        date_joined = datetime.fromtimestamp(epoch)
        return formats.date_format(date_joined, format)

    @classmethod
    def format_description(cls, line: Dict[str, any]) -> str:
        """Formats the description line of an invoice"""
        # if we have a description, return it
        if line.description is not None:
            return line.description

        # if we have a subscription show {{Name}} x timeframe
        if line.type == "subscription":
            name = "{} ({} - {})".format(
                line.plan.name,
                cls.format_datetime(line.period.start, "DATE_FORMAT"),
                cls.format_datetime(line.period.end, "DATE_FORMAT"),
            )
            return "{} x {}".format(line.quantity, name)

        # we have a normal line item, and there should have been a description
        else:
            raise Exception("Non-subscription without description")

    @classmethod
    def format_total(cls, amount: float, cur: str) -> str:
        """Formats the total"""
        if cur == "eur":
            return "%0.2f €" % (amount / 100)
        elif cur == "usd":
            return "%0.2f $" % (amount / 100)
        else:
            raise Exception("unknown currency {}".format(cur))

    @classmethod
    def get_invoice_table(
        cls, customer: Dict[str, Any]
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        invoices, err = stripewrapper.get_payment_table(customer)
        described = []

        if err is None:
            try:
                invoices = [
                    {
                        "lines": [cls.format_description(l) for l in iv["lines"]],
                        "date": cls.format_datetime(iv["date"]),
                        "total": cls.format_total(iv["total"][0], iv["total"][1]),
                        "paid": iv["paid"],
                        "closed": iv["closed"],
                        "upcoming": iv["upcoming"],
                    }
                    for iv in invoices
                ]
            except Exception as e:
                err = str(e)
        else:
            err = "Something went wrong. Please try again later or contact support. "

        return invoices, err

    @classmethod
    def format_method(cls, source: Dict[str, Any]) -> str:
        if source["kind"] == "card":
            return "{} Card ending in {} (valid until {}/{})".format(
                source["brand"],
                source["last4"],
                source["exp_month"],
                source["exp_year"],
            )
        elif source["kind"] == "sepa":
            return 'Bank Account ending in {} (<a href="{}" target="_blank">SEPA Mandate Reference {}</a>)'.format(
                source["last4"], source["mandate_url"], source["mandate_reference"]
            )
        else:
            return "Unknown Payment Method. Please contact support. "

    @classmethod
    def get_method_table(
        cls, customer: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        methods, err = stripewrapper.get_methods_table(customer)
        if err is None:
            methods = [cls.format_method(method) for method in methods]
        else:
            err = "Something went wrong. Please try again later or contact support. "

        return methods, err


@method_decorator(require_setup_completed, name="dispatch")
class PaymentsView(RedirectView):
    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        """Redirects to the Stripe customer portal for the user"""
        customer = self.request.user.alumni.membership.customer

        # if the user is not a member, redirect to the signup page
        if customer is None:
            return reverse("setup_signup")

        # otherwise, redirect to the stripe customer portal
        portal_url = self.request.build_absolute_uri(reverse("portal"))
        url, err = stripewrapper.get_customer_portal_url(customer, portal_url)
        if err is not None:
            messages.error(
                self.request,
                "Something went wrong when trying to redirect you to the payment portal. Please try again later or contact support. ",
            )
            return reverse("portal")

        return url


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    event, error = stripewrapper.make_stripe_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )

    if error:
        print(error)
        return HttpResponseBadRequest()

    # Handle the event
    if event.type.startswith("payment_intent."):
        payment_intent = event.data.object  # contains a stripe.PaymentIntent

        # Update the local database
        PaymentIntent.objects.update_or_create(
            stripe_id=payment_intent.id,
            defaults={"data": stripewrapper._pi_to_dict(payment_intent)},
        )

    return HttpResponse()
