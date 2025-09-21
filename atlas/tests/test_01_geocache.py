from __future__ import annotations

from django.test import TestCase
from atlas.models import GeoLocation
from alumni.models import Address
from django.core import management
import os

import unittest

GEOCACHE_TEST_ENABLED = os.environ.get("ENABLE_GEOCACHE_TEST", "0") == "1"


class GeoCacheTest(TestCase):
    fixtures = ["registry/tests/fixtures/integration.json"]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        if GEOCACHE_TEST_ENABLED:
            management.call_command(
                "geocache",
                url="https://github.com/BeyondThePond/geonames.org-mirror/releases/download/v2020.01/allCountries.zip",
            )

    def test_download(self) -> None:
        if not GEOCACHE_TEST_ENABLED:
            return self.skipTest("Skipping, set ENABLE_GEOCACHE_TEST=1 to enable")

        self.assertEqual(
            GeoLocation.objects.count(), 852799, "Correct number of objects received"
        )

    def test_get_all_coords(self) -> None:
        if not GEOCACHE_TEST_ENABLED:
            return self.skipTest("Skipping, set ENABLE_GEOCACHE_TEST=1 to enable")

        self.assertListEqual(
            list(Address.all_valid_coords()),
            [
                [51.1181, 12.3907],
                [51.9716, 9.5193],
                [29.7992, -90.8096],
                [36.6916, -82.02],
                [53.1094, 8.7814],
                [46.7667, 23.6],
            ],
            "check that all_coordinates returns the right coordinates",
        )
