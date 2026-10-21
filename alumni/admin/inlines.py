from __future__ import annotations
from django.contrib import admin

from ..models import (
    Address,
    JobInformation,
    SocialMedia,
    JacobsData,
    Approval,
    Skills,
    SetupCompleted,
)

from atlas.admin import AtlasSettingsInline
from payments.admin import MembershipInformationInline, SubscriptionInformationInline


class JacobsDataInline(admin.StackedInline):
    verbose_name = "University Data"
    verbose_name_plural = "University Data"
    extra = 0
    model = JacobsData


class SocialMediaInline(admin.StackedInline):
    extra = 0
    model = SocialMedia


class AddressInline(admin.StackedInline):
    extra = 0
    model = Address


class JobInformationInline(admin.StackedInline):
    extra = 0
    model = JobInformation


class ApprovalInline(admin.StackedInline):
    extra = 0
    model = Approval


class SkillsInline(admin.StackedInline):
    extra = 0
    model = Skills


class SetupCompletedInline(admin.StackedInline):
    extra = 0
    model = SetupCompleted


class AlumniAdminInlines:
    inlines = [
        SetupCompletedInline,
        ApprovalInline,
        AddressInline,
        SocialMediaInline,
        JacobsDataInline,
        JobInformationInline,
        SkillsInline,
        MembershipInformationInline,
        SubscriptionInformationInline,
        AtlasSettingsInline,
    ]
