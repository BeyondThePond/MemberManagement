from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateResponseMixin, View

from alumni.fields import GenderField, TierField
from alumni.models import (
    Address,
    Alumni,
    Approval,
    JacobsData,
    JobInformation,
    Skills,
    SocialMedia,
)
from atlas.models import AtlasSettings
from MemberManagement.mixins import RedirectResponseMixin
from payments import stripewrapper
from payments.models import MembershipInformation, SubscriptionInformation
from registry.decorators import require_alumni

from ..forms import (
    AddressForm,
    AtlasSettingsForm,
    JacobsForm,
    JobInformationForm,
    RegistrationForm,
    SetupCompletedForm,
    SkillsForm,
    SocialMediaForm,
)
from ..utils import generate_username
from .api import FormValidationView

if TYPE_CHECKING:
    from typing import Any, Optional, Dict, Union
    from django.http import HttpResponse
    from django.forms import Form
    from django.db.models import Model
    from datetime import datetime


@method_decorator(login_required, name="dispatch")
class SetupView(RedirectResponseMixin, View):
    def get(self, *args: Any, **kwargs: Any) -> HttpResponse:
        component = self.request.user.alumni.get_first_unset_component()

        if component is None:
            return self.redirect_response("portal", reverse=True)
        else:
            uri, reverse = component.component_setup_url()
            return self.redirect_response(uri, reverse=reverse)


class SetupViewBase(RedirectResponseMixin, TemplateResponseMixin, View):
    """A base class for all setup views"""

    http_method_names = ["get", "post"]
    template_name: str = "setup/setup.html"

    setup_name: Optional[str] = None
    setup_subtitle: str = ""
    setup_next_text: str = ""
    setup_form_class: Type[Form] = None
    setup_redirect_url: str = "setup"

    def has_setup_component(self) -> bool:
        """Function that is called on every request to check if this component has been setup"""

        raise NotImplementedError

    def should_setup_component(self) -> bool:
        """Function that is called to perform pre-setup hooks and check if further (user-based) setup is required"""

        raise NotImplementedError

    def dispatch_already_set(self) -> HttpResponse:
        """Called when the setup component is already setup"""

        raise NotImplementedError

    def dispatch_should_not(self) -> HttpResponse:
        """Called when the setup component is not setup and also should not be"""

        return self.dispatch_already_set()

    def form_valid(self, form: Form) -> Any:
        """Called when the setup form has been successfully submitted"""
        raise NotImplementedError

    def dispatch_success(self, validated: Any) -> HttpResponse:
        """Called on True-ish return of form_valid() with the returned value"""

        return self.redirect_response(self.__class__.setup_redirect_url, reverse=True)

    def get_context(self, form: Form) -> Dict[str, Any]:
        """Builds the context for instatiating the content when a page is rendered"""

        return {
            "form": form,
            "title": self.__class__.setup_name,
            "subtitle": self.__class__.setup_subtitle,
            "next_text": self.__class__.setup_next_text,
        }

    def dispatch_form(self, form: Form) -> HttpResponse:
        """Called to dispatch the form to be filled out"""

        return self.render_to_response(self.get_context(form))

    def dispatch(self, *args: Any, **kwargs: Any) -> HttpResponse:
        """Dispatches this form"""

        # if we already have the setup component
        # then call the appropriate dispatch method
        if self.has_setup_component():
            return self.dispatch_already_set()

        # if we should not setup this component next
        # then call the apporpriate redirect
        if not self.should_setup_component():
            return self.dispatch_should_not()

        # Create the form instance
        form = self.__class__.setup_form_class(self.request.POST or None)

        # and if it is valid
        if self.request.method == "POST" and form.is_valid():
            form.clean()

            # if we have a valid form with some success
            # then we dispatch it
            success = self.form_valid(form)
            if success is not None:
                return self.dispatch_success(success)

        # else render the form
        return self.dispatch_form(form)


def make_user(
    given_name: str,
    middle_name: str,
    family_name: str,
    email: str,
    nationality: Union[str, List[str]],
    birthday: datetime,
    member_type: str,
    member_tier: str,
    skip_stripe: bool,
) -> User:
    """This function creates an returns a new alumni user. All exceptions should be caught by the parent"""

    # first generate a new username
    username = generate_username(
        given_name,
        middle_name,
        family_name,
    )

    with transaction.atomic():
        # create a user, may fail because of race conditions
        # but that failure should be caught by the caller
        user = User.objects.create_user(username=username)

        # create an alumni
        # may fail, as the email is duplicate-free
        alumni = Alumni.objects.create(
            profile=user,
            givenName=given_name,
            middleName=middle_name,
            familyName=family_name,
            email=email,
            sex=GenderField.UNSPECIFIED,
            birthday=birthday,
            nationality=nationality,  # TODO: Need to add this field
            category=member_type,
        )

        # create all the objects related to the alumni
        # assumed to never fail
        approval = Approval.objects.create(member=alumni, approval=False, gsuite=None)
        address = Address.objects.create(member=alumni)
        socials = SocialMedia.objects.create(member=alumni)
        jacobs = JacobsData.objects.create(member=alumni)
        job = JobInformation.objects.create(member=alumni)
        skills = Skills.objects.create(member=alumni)
        atlas = AtlasSettings.objects.create(member=alumni)

        # if needed, create a starter subscription
        if member_tier == TierField.STARTER:
            SubscriptionInformation.create_starter_subscription(alumni)

        # which may fail, and if it does should add an error
        stripe_customer = ""
        if not skip_stripe:
            stripe_customer, err = stripewrapper.create_customer(alumni)
            if err is not None:
                raise CustomerCreationFailed()

        membership = MembershipInformation.objects.create(
            member=alumni, tier=member_tier, customer=stripe_customer
        )

    return user


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RegisterView(SetupViewBase):
    setup_name = "Register"
    setup_subtitle = "Enter your Data"
    setup_next_text = "Continue Application"
    template_name = "setup/register.html"
    setup_form_class = RegistrationForm

    def has_setup_component(self) -> bool:
        return self.request.user.is_authenticated

    def get_context(self, form: RegistrationForm) -> Dict[str, Any]:
        context = super().get_context(form)
        context.update(
            {
                "form_valid": json.dumps(FormValidationView.validate_form_tojson(form)),
            }
        )
        return context

    def should_setup_component(self) -> bool:
        return True

    def dispatch_already_set(self) -> HttpResponse:
        return self.redirect_response("root", reverse=True)

    def form_valid(self, form: RegistrationForm) -> Optional[True]:
        """Called when the form is valid and an instance is to be created"""

        # extract out the cleaned data
        cleaned_data = form.cleaned_data

        given_name = cleaned_data["givenName"]
        middle_name = cleaned_data["middleName"]
        family_name = cleaned_data["familyName"]
        email = cleaned_data["email"]
        nationality = cleaned_data["nationality"]
        birthday = cleaned_data["birthday"]
        member_type = cleaned_data["memberCategory"]
        member_tier = cleaned_data["memberTier"]

        # create a user
        user = None

        try:
            user = make_user(
                given_name,
                middle_name,
                family_name,
                email,
                nationality,
                birthday,
                member_type,
                member_tier,
                skip_stripe=False,
            )

        # FIXME: This integrity error is currently assumed to be an already existing email
        except IntegrityError as ie:
            form.add_error(
                "email",
                "An Alumni with that email address already exists. Did you mean to login instead? ",
            )
            return None
        except CustomerCreationFailed:
            form.add_error(
                None,
                "Error when talking to our payment provider. Please try again later or contact support. ",
            )
            return None

        # if all that worked, login the user
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")

        # and finally return
        return True


class CustomerCreationFailed(Exception):
    pass


@method_decorator(require_alumni, name="dispatch")
class SetupComponentView(SetupViewBase):
    """A view for setting up components"""

    setup_next_text = "Continue"

    @classmethod
    def setup_class(cls) -> Type[Model]:
        return cls.setup_form_class.Meta.model

    def has_setup_component(self) -> bool:
        return self.request.user.alumni.has_component(self.__class__.setup_class())

    def should_setup_component(self) -> bool:
        component = self.request.user.alumni.get_first_unset_component()
        if component is None:
            return False

        return component is self.__class__.setup_class()

    def dispatch_already_set(self) -> HttpResponse:
        return self.redirect_response("portal", reverse=True)

    def form_valid(self, form: Form) -> Model:
        """Called when the form is valid and an instance is to be created"""
        instance = form.save(commit=False)
        instance.member = self.request.user.alumni
        instance.save()

        return instance


class AddressSetup(SetupComponentView):
    setup_name = "General Information - Residential Address"
    setup_subtitle = ""
    setup_form_class = AddressForm


class SocialSetup(SetupComponentView):
    setup_name = "Social Media Data"
    setup_subtitle = ""
    setup_form_class = SocialMediaForm


class JacobsSetup(SetupComponentView):
    setup_name = "Alumni Data"
    setup_subtitle = (
        "Tell us what you did at Constructor University, former Jacobs University"
    )
    setup_form_class = JacobsForm


class JobSetup(SetupComponentView):
    setup_name = "Professional Information"
    setup_subtitle = "What did you do after studying at Constructor University, former Jacobs University?"
    setup_form_class = JobInformationForm


class SkillsSetup(SetupComponentView):
    setup_name = "Education And Skills"
    setup_subtitle = ""
    setup_form_class = SkillsForm


class AtlasSetup(SetupComponentView):
    setup_name = "Atlas Setup"
    setup_subtitle = "A Map & Search Interface for Alumni"
    setup_form_class = AtlasSettingsForm


class CompletedSetup(SetupComponentView):
    setup_name = "Almost Done"
    setup_subtitle = ""
    setup_form_class = SetupCompletedForm
    setup_next_text = "Finalize Application & Continue to Portal"

    template_name = "setup/completed.html"
