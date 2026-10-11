from django.test import TestCase
from datetime import date
from io import BytesIO
from openpyxl import Workbook

from alumni.fields import GenderField
from alumni.models import Alumni
from registry.management.commands.import_csv import (
    AlumniParser,
    columns_from_header,
    import_csv_rows,
    read_import_rows,
)


class ImportCsvRowsTest(TestCase):
    def test_simulate_catches_duplicate_email_in_csv_without_importing(self):
        columns = ["birthday_excel", "name_2", "name_1", "email"]
        rows = [
            ["2000-01-02", "Family", "Given", "same@example.com"],
            ["2001-02-03", "Other", "Person", "same@example.com"],
        ]

        result = import_csv_rows(rows, columns, no_stripe=True, simulate=True)

        self.assertEqual(Alumni.objects.count(), 0)
        self.assertEqual(len(result.created), 1)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].row_number, 3)

    def test_reads_xlsx_with_provided_headers(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["First Name", "Last Name", "Birthday", "Nationality", "Gender"])
        sheet.append(
            ["Justine Alexandra ", "Prinsloo", "01.04.2003", "South Africa", "w"]
        )
        file = BytesIO()
        workbook.save(file)
        file.seek(0)

        header, rows = read_import_rows(file, "members.xlsx")

        self.assertEqual(
            columns_from_header(header),
            ["name_1", "name_2", "birthday", "nationality_1", "sex"],
        )
        self.assertEqual(
            rows[0],
            ["Justine Alexandra ", "Prinsloo", "01.04.2003", "South Africa", "w"],
        )
        parsed, targets = AlumniParser().parse(
            columns_from_header(header),
            rows,
            required=["given_name", "family_name", "birthday"],
        )
        self.assertEqual(parsed[0]["given_name"], "Justine Alexandra")
        self.assertEqual(parsed[0]["birthday"], date(2003, 4, 1))
        self.assertEqual(parsed[0]["nationality_1"], "ZA")
        self.assertEqual(parsed[0]["gender"], GenderField.FEMALE)
