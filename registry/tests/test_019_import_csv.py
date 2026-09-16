from django.test import TestCase

from alumni.models import Alumni
from registry.management.commands.import_csv import import_csv_rows


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
