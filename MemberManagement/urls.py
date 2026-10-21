from __future__ import annotations

"""MemberManagement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from .views import HomeView, HealthCheckDynamic, HealthCheckStatic

urlpatterns = [
    # Static Views
    path("", HomeView.as_view(), name="root"),
    path("healthcheck/", HealthCheckDynamic.as_view(), name="healthcheck"),
    path("healthcheck/static/", HealthCheckStatic.as_view(), name="healthcheck"),
    path(
        "imprint/",
        RedirectView.as_view(
            url="https://jacobs-alumni.de/imprint/",
            permanent=False,
        ),
        name="imprint",
    ),
    # Root redirects
    path(
        "register/",
        RedirectView.as_view(pattern_name="register", permanent=False),
        name="root_register",
    ),
    path(
        "privacy/",
        RedirectView.as_view(
            url="https://jacobs-alumni.de/privacy/",
            permanent=False,
        ),
        name="privacy",
    ),
    path(
        "vote/",
        RedirectView.as_view(pattern_name="registry_vote", permanent=False),
        name="root_vote",
    ),
    # And recursively go into all the apps
    path("portal/", include("registry.urls")),
    path("admin/", include("alumni.urls")),
    path("impersonate/", include("impersonate.urls")),
    path("auth/", include("custom_auth.urls")),
    path("atlas/", include("atlas.urls")),
    path("payments/", include("payments.urls")),
    path("receipts/", include("donation_receipts.urls")),
    path("donations/", include("donations.urls")),
]

# make an http 500 handler in case things go wrong
error_handler = TemplateView.as_view(template_name="base/error.html")


def handler500(request):
    return error_handler(request)
