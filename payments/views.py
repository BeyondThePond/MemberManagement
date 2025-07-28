from __future__ import annotations

from datetime import datetime

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
    setup_form_class = CancellablePaymentMethodForm
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

        # by default, we are not in payment update mode
        self.payment_update_mode = False
        self.payment_update_error = None

        # if the subscription object is not the first unset component
        # then we shouldn't set it up right now and redirect instead
        if not super().should_setup_component():
            return False

        membership = self.request.user.alumni.membership
        desired_tier = membership.desired_tier

        # if there is no desired_tier, then the subscription object is
        # the first unset tier and we should set it up right now.
        if desired_tier is None:
            return True

        # we are in update_payment mode mode
        self.payment_update_mode = True

        # try updating the instance right now
        instance, err = membership.change_tier()
        if err is not None:
            # abort the tier upgrade
            membership.desired_tier = None
            membership.save()

            # and store the payment error to be displayed
            self.payment_update_error = err

            return False

        # if we don't have an instance yet, we need the user to enter payment details
        return instance is None

    def dispatch_should_not(self) -> HttpResponse:
        if not self.payment_update_mode:
            return super().dispatch_should_not()

        if self.payment_update_error is None:
            tier = self.request.user.alumni.membership.tier
            messages.success(
                self.request,
                "Tier has been changed to {}".format(TierField.get_description(tier)),
            )
        else:
            messages.error(
                self.request,
                "Unable to change tier: {}. Please try again or contact support. ".format(
                    self.payment_update_error
                ),
            )

        # if the subscription was in update mode and we shouldn't set it up
        # then we should immediately redirect to the memebership page
        return self.redirect_response("update_membership", reverse=True)

    def dispatch_form(self, form: CancellablePaymentMethodForm) -> HttpResponse:
        if self.payment_update_mode:
            messages.info(
                self.request,
                "Please enter your payment details to complete the tier change. ",
            )

        return super().dispatch_form(form)

    def form_valid(
        self, form: CancellablePaymentMethodForm
    ) -> Optional[SubscriptionInformation]:
        """Form has been validated"""

        # if the membership is the starter
        membership = self.request.user.alumni.membership
        if (
            membership.member.category != AlumniCategoryField.REGULAR
            and form.user_go_to_starter
        ):
            form.add_error(
                None,
                "Non-regular Alumni are not allowed to use the free starter tier. ",
            )
            return None

        # Attach the payment source to the customer
        _, err = form.attach_to_customer(membership.customer)

        # if the error is not, return
        if err is not None:
            form.add_error(
                None,
                "Something went wrong when talking to our payment service provider. Please try again later or contact support. ",
            )
            return None

        # we went to the starter tier
        if not form.user_go_to_starter:
            instance = membership.create_subscription()
        else:
            instance = membership.cancel_create_subscription()

        if instance is None:
            form.add_error(
                None,
                "Something went wrong trying to create the subscription. Please try again later or contact support. ",
            )

        return instance

    def dispatch_success(self, validated: SubscriptionInformation) -> HttpResponse:
        """called upon successful setup"""

        # if this was not created from an update operation, do nothing
        if not validated.created_from_update:
            return super().dispatch_success(validated)

        # we suceeded
        messages.success(
            self.request,
            "Tier has been changed to {}".format(
                TierField.get_description(self.request.user.alumni.membership.tier)
            ),
        )
        return self.redirect_response("update_membership", reverse=True)


@method_decorator(require_setup_completed, name="dispatch")
class UpdatePaymentView(FormView):
    template_name = "payments/subscribe.html"
    form_class = PaymentMethodForm

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "title": "Update Payment Information",
                "updating": True,
                "next_text": "AUTHORIZE PAYMENT NOW",
                "alumni": self.request.user.alumni,
                "allow_go_to_starter": False,
            }
        )
        return context

    def form_valid(self, form: PaymentMethodForm) -> HttpResponse:
        # Attach the payment source to the customer
        customer = self.request.user.alumni.membership.customer
        _, err = form.attach_to_customer(customer)

        # if the error is not, return
        if err is not None:
            form.add_error(
                None,
                "Something went wrong when talking to our payment service provider. Please try again later or contact support. ",
            )
            return self.form_invalid(form)

        messages.success(self.request, "Payment method has been updated. ")

        return self.form_invalid(form)


@method_decorator(require_setup_completed, name="dispatch")
class UpdateTierView(RedirectResponseMixin, FormView):
    template_name = "payments/tier.html"
    form_class = MembershipInformationForm

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "title": "Change Membership Tier",
                "updating": True,
                "next_text": "Change Tier",
                "confirm_text": "Change Tier",
                "alumni": self.request.user.alumni,
            }
        )
        return context

    def form_valid(self, form: MembershipInformationForm) -> HttpResponse:
        membership = self.request.user.alumni.membership

        # update the desired tier to what the user selected
        desired_tier = form.cleaned_data["tier"]
        membership.desired_tier = desired_tier
        membership.save()

        # redirect to the setup_subscription page
        return self.redirect_response("setup_subscription", reverse=True)


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
class PaymentsView(PaymentsTableMixin, RedirectView):
    template_name = "payments/view.html"

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        """Redirects to the Stripe customer portal for the user"""
        customer = self.request.user.alumni.membership.customer

        # if the user is not a member, redirect to the signup page
        if customer is None:
            return self.reverse("setup_signup")

        # otherwise, redirect to the stripe customer portal
        portal_url = self.request.build_absolute_uri(reverse("portal"))
        url, err = stripewrapper.get_customer_portal_url(customer, portal_url)
        if err is not None:
            messages.error(
                self.request,
                "Something went wrong when trying to redirect you to the payment portal. Please try again later or contact support. ",
            )
            return self.reverse("payments_view")

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
