from __future__ import annotations

from django.contrib.auth.decorators import login_required

from django.urls import reverse
from django.shortcuts import redirect

from django.http import HttpResponseForbidden

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable
    from django.contrib.auth.models import User
    from django.http import HttpResponse, HttpRequest


def user_has_alumni(user: User) -> bool:
    """Safely checks if a user has an alumni"""
    try:
        user.alumni
        return True
    except:
        return False


def require_alumni(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """A decorator that requires a user to have an associated alumni object.

    If the user is not logged in, they are redirected to the login page.
    If the user is logged in and does not have an alumni, an error message is shown.
    """

    @login_required
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not user_has_alumni(request.user):
            return HttpResponseForbidden(
                "User missing Alumni. Contact Support if this is unexpected. "
            )

        return view(request, *args, **kwargs)

    return wrapper


def require_setup_completed(
    view: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    """A decorator for views that ensures that and alumni has setup all components"""

    @require_alumni
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # if we are missing a component, return to the main page
        if not request.user.alumni.setup_completed:
            return redirect(reverse("setup"))

        # else use the normal one
        return view(request, *args, **kwargs)

    # and return the wrapper
    return wrapper
