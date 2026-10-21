from __future__ import annotations
from django.contrib import admin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterator, Tuple, List, Type
    from datetime import datetime
    from ..models import Alumni
    from django.http import HttpRequest
    from django.db.models import QuerySet, FieldListFilter
    from django.contrib.admin import ModelAdmin


class AlumniListDisplay:
    def alumni_fullName(self, x: Alumni) -> str:
        return x.fullName

    alumni_fullName.short_description = "Full Name"

    def approval_approval(self, x: Alumni) -> str:
        return x.approval.approval

    approval_approval.short_description = "Approved"
    approval_approval.boolean = "true"
    approval_approval.admin_order_field = "approval__approval"

    def setup_date(self, x: Alumni) -> datetime:
        return x.setup.date

    setup_date.short_description = "Setup Completed"
    setup_date.admin_order_field = "setup__date"

    def approval_autocreated(self, x: Alumni) -> str:
        return x.approval.autocreated

    approval_autocreated.short_description = "Auto"
    approval_autocreated.boolean = "true"
    approval_autocreated.admin_order_field = "approval__autocreated"

    def profile_googleassociation(self, x: Alumni) -> bool:
        results = x.profile.googleassociation_set
        return results.exists()

    profile_googleassociation.short_description = "Linked"
    profile_googleassociation.boolean = True
    profile_googleassociation.admin_order_field = "profile__googleassociation"

    def approval_gsuite(self, x: Alumni) -> str:
        return x.approval.gsuite

    approval_gsuite.short_description = "Alumni E-Mail"
    approval_gsuite.admin_order_field = "approval__gsuite"

    def membership_tier(self, x: Alumni) -> str:
        return x.membership.tier

    membership_tier.short_description = "Tier"
    membership_tier.admin_order_field = "membership__tier"

    def atlas_included(self, x: Alumni) -> bool:
        return x.atlas.included

    atlas_included.short_description = "Atlas"
    atlas_included.boolean = True
    atlas_included.admin_order_field = "atlas__included"

    def jacobs_transferOptout(self, x: Alumni) -> bool:
        return x.jacobs.transferOptout

    jacobs_transferOptout.short_description = "Data Transfer Optout"
    jacobs_transferOptout.boolean = True
    jacobs_transferOptout.admin_order_field = "jacobs__transferOptout"

    def jacobs_degree(self, x: Alumni) -> str:
        return x.jacobs.degree

    jacobs_degree.short_description = "Degree"
    jacobs_degree.admin_order_field = "jacobs__degree"

    def jacobs_graduation(self, x: Alumni) -> str:
        return x.jacobs.graduation

    jacobs_graduation.short_description = "Class"
    jacobs_graduation.admin_order_field = "jacobs__graduation"

    def jacobs_major(self, x: Alumni) -> str:
        return x.jacobs.major

    jacobs_major.short_description = "Major"
    jacobs_major.admin_order_field = "jacobs__major"

    def jacobs_college(self, x: Alumni) -> str:
        return x.jacobs.college

    jacobs_college.short_description = "College"
    jacobs_college.admin_order_field = "jacobs__college"

    list_display = (
        # basic information
        "alumni_fullName",
        "email",
        "sex",
        # member email
        "approval_approval",
        "setup_date",
        "approval_autocreated",
        "profile_googleassociation",
        "approval_gsuite",
        # category + subscription
        "category",
        "membership_tier",
        # visible in atlas
        "atlas_included",
        # Jacobs Information
        "jacobs_transferOptout",
        "jacobs_degree",
        "jacobs_graduation",
        "jacobs_major",
        "jacobs_college",
    )


class SetupCompletedFilter(admin.SimpleListFilter):
    title = "Setup Status"
    parameter_name = "completed"

    def lookups(
        self, request: HttpRequest, modeladmin: ModelAdmin
    ) -> List[Tuple[str, str]]:
        return [("1", "Completed"), ("0", "Incomplete")]

    def queryset(self, request: HttpRequest, queryset: QuerySet):
        val = self.value()
        if val == "1":
            return queryset.filter(setup__isnull=False)
        elif val == "0":
            return queryset.filter(setup__isnull=True)
        else:
            return queryset


def custom_titled_filter(title: str) -> Type[FieldListFilter]:
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class AlumniListFilter:
    # filters to the left
    list_filter = (
        ("approval__approval", custom_titled_filter("Application Approval")),
        SetupCompletedFilter,
        ("approval__autocreated", custom_titled_filter("Automatically Imported")),
        ("category", custom_titled_filter("Alumni Category")),
        ("membership__tier", custom_titled_filter("Alumni Tier")),
        ("jacobs__transferOptout", custom_titled_filter("Data Transfer Optout")),
        ("atlas__included", custom_titled_filter("Included in Alumni Atlas")),
        ("jacobs__degree", custom_titled_filter("University Degree")),
        ("jacobs__graduation", custom_titled_filter("University Class")),
        ("jacobs__major", custom_titled_filter("University Major")),
    )
