from __future__ import annotations

from django.contrib import admin

from ..models import Alumni

from .search import AlumniSearch
from .inlines import AlumniAdminInlines
from .list import AlumniListDisplay, AlumniListFilter
from .actions import AlumniAdminActions
from .import_csv import AlumniCsvImport


class AlumniAdmin(
    AlumniCsvImport,
    AlumniSearch,
    AlumniListFilter,
    AlumniAdminInlines,
    AlumniListDisplay,
    AlumniAdminActions,
    admin.ModelAdmin,
):
    pass


admin.site.register(Alumni, AlumniAdmin)
