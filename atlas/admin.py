from __future__ import annotations

from django.contrib import admin

from .models import GeoLocation, AtlasSettings

# Register your models here.


class GeoAdmin(admin.ModelAdmin):
    list_filter = ("country",)
    list_display = ("country", "zip", "lat", "lon")
    search_fields = ("country", "zip")


class AtlasSettingsInline(admin.StackedInline):
    model = AtlasSettings
    extra = 0


admin.site.register(GeoLocation, GeoAdmin)
