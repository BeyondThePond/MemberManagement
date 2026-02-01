from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, login, views
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from .utils.auth import generate_login_token

from alumni.models import Alumni as UserModel

from MemberManagement import mailutils
from . import forms

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest


class TokenEmailSentView(views.TemplateView):
    template_name = "auth/token_sent.html"


def email_token_login(request: HttpRequest) -> HttpResponse:
    """Tries to login a user with a token they received via email"""
    if request.method != "POST":
        # Render a template to cause a POST request
        get_token = request.GET.get("token", None)
        next_url = request.GET.get("next", None)
        return render(
            request,
            "auth/token_login.html",
            context={"token": get_token, "next": next_url},
        )

    token = request.POST.get("token", None)

    # Naming of parameter is 'sesame' to fit name used by django-sesame
    res = authenticate(request, sesame=token)

    if res is not None:
        login(request, res)
        next_url = request.POST.get("next", None)
        # Validate the next URL to prevent open redirects
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return HttpResponseRedirect(next_url)
        else:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    else:
        return render(request, "auth/token_login.html", context={"error": True})


def google_token_login(request: HttpRequest) -> HttpResponse:
    """Tries to log a user in using a token supplied by Google. Called only by AJAX"""
    if request.method != "POST":
        raise SuspiciousOperation("Wrong request method")

    token = request.POST["token"]

    res = authenticate(request, token=token)

    if res is not None:
        login(request, res)
        return HttpResponse("OK")
    else:
        return HttpResponseForbidden("NOK")


class ClientIdLoginView(views.LoginView):
    # Injects the OAuth client ID into the template context
    extra_context = {
        "client_id": settings.GSUITE_OAUTH_CLIENT_ID,
    }

    def get_context_data(self, **kwargs):
        context = super(views.LoginView, self).get_context_data(**kwargs)
        context["googlefail"] = self.request.GET.get("error", "") == "googlefail"
        context.update(self.extra_context)

        return context

    form_class = forms.EmailForm

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return HttpResponseRedirect(redirect_to)
        return super(views.LoginView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return super(views.LoginView, self).get_form_kwargs()

    def form_valid(self, form):
        """Forward the user, no matter if we found them or not. Don't want to leak email existance information."""
        if form.is_valid():
            next_url = self.get_success_url()
            email = form.cleaned_data["email"]

            try:
                user = UserModel.objects.get(email=email)
                token_str = generate_login_token(user.profile)
                abs_url = "{}?token={}&next={}".format(
                    self.request.build_absolute_uri(reverse(email_token_login)),
                    token_str,
                    next_url,
                )

                mailutils.send_email(
                    user.email,
                    "Jacobs Alumni Association - Login Link",
                    "emails/token_email.html",
                    name=user.givenName,
                    login_url=abs_url,
                )

                if settings.DEBUG:
                    print(abs_url)
            except UserModel.DoesNotExist:
                # Can't complain to the user here, or we'll give away that we don't know this address.
                pass

        return HttpResponseRedirect(reverse("token_sent"))
