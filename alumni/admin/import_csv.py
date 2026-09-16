from __future__ import annotations

import csv
from io import TextIOWrapper

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from registry.management.commands.import_csv import DEFAULT_COLUMNS, import_csv_rows


class AlumniCsvImport:
    change_list_template = "admin/alumni/alumni/change_list.html"

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="alumni_alumni_import_csv",
            )
        ] + super().get_urls()

    def import_csv_view(self, request):
        if request.method == "POST":
            upload = request.FILES.get("csv")
            columns = request.POST.get("columns", DEFAULT_COLUMNS).split(",")
            no_stripe = request.POST.get("no_stripe") == "on"

            if upload is None:
                messages.error(request, "Choose a CSV file to import.")
            else:
                try:
                    return self.import_csv_upload(request, upload, columns, no_stripe)
                except Exception as e:
                    messages.error(request, "CSV import failed: {}".format(e))

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import alumni CSV",
            "default_columns": DEFAULT_COLUMNS,
        }
        return render(request, "admin/alumni/alumni/import_csv.html", context)

    def import_csv_upload(self, request, upload, columns, no_stripe):
        reader = csv.reader(
            TextIOWrapper(upload.file, encoding="utf-8-sig", newline="")
        )
        header = next(reader, [])
        rows = list(reader)

        check = import_csv_rows(rows, columns, no_stripe=True, simulate=True)
        if check.failures:
            return self.error_csv_response(header or columns, check)

        result = import_csv_rows(rows, columns, no_stripe=no_stripe)
        if result.failures:
            return self.error_csv_response(header or columns, result)

        self.message_user(request, "Imported {} user(s).".format(len(result.created)))
        return redirect("admin:alumni_alumni_changelist")

    def error_csv_response(self, header, result):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="import_errors.csv"'

        writer = csv.writer(response)
        writer.writerow(["row_number", "error"] + list(header))
        for failure in result.failures:
            writer.writerow([failure.row_number, failure.error] + failure.row)

        return response
