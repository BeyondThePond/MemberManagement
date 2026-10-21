from __future__ import annotations

from django.contrib.messages import get_messages
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import render, redirect

from ..decorators import require_setup_completed

from ..forms import (
    AlumniForm,
    AddressForm,
    JacobsForm,
    SocialMediaForm,
    JobInformationForm,
    SkillsForm,
    AtlasSettingsForm,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, Type
    from django.forms import Form
    from django.http import HttpRequest, HttpResponse


def editViewFactory(
    prop: Optional[str], FormClass: Type[Form], name: str
) -> Callable[[HttpRequest], HttpResponse]:
    """Generates an edit view for a given section of the profile"""

    @require_setup_completed
    def edit(request: HttpRequest) -> HttpResponse:
        next = request.GET.get("next")

        # figure out the edit url to redirect to
        if next:
            url = next
        elif prop is None:
            url = reverse("edit")
        else:
            url = reverse("edit_{}".format(prop))

        # load the instance
        if prop is None:
            instance = request.user.alumni
        else:
            instance = getattr(request.user.alumni, prop)

        if request.method == "POST":
            # load the form
            form = FormClass(request.POST, instance=instance)

            # check that the form is valid
            if form.is_valid():
                form.clean()

                # Create the Address form
                instance = form.save(commit=False)
                instance.save()

                # Add a success message
                messages.success(request, "Changes saved. ")

                # and then continue to the next page
                return redirect(url)

        # if we did not have any post data, simply create a new form
        else:
            form = FormClass(instance=instance)

        # and return the request
        return render(
            request,
            "portal/edit.html",
            {
                "form": form,
                "name": name,
                "next": next,
                "messsages": get_messages(request),
            },
        )

    return edit


edit = editViewFactory(None, AlumniForm, "General Information")
address = editViewFactory("address", AddressForm, "Address")
jacobs = editViewFactory("jacobs", JacobsForm, "University Data")
social = editViewFactory("social", SocialMediaForm, "Social Media")
job = editViewFactory("job", JobInformationForm, "Job Information")
skills = editViewFactory("skills", SkillsForm, "Education and Skills")
atlas = editViewFactory("atlas", AtlasSettingsForm, "Atlas")
