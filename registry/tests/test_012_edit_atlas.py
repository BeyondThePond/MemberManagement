from __future__ import annotations

import pytest
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from MemberManagement.tests.integration import IntegrationTest

pytestmark = pytest.mark.skip(reason="Atlas is no longer used.")


@unittest.skip("Atlas is no longer used.")
class EditAtlasTest(IntegrationTest, StaticLiveServerTestCase):
    fixtures = ["registry/tests/fixtures/integration.json"]
    user = "Mounfem"

    def test_noedit(self) -> None:
        """Tests that entering nothing doesn't change anything"""

        # enter nothing
        self.submit_form("edit_atlas", "input_id_submit")
        self.assert_url_equal("edit_atlas")

        atlas = self.user.alumni.atlas
        self.assertEqual(atlas.included, True)
        self.assertEqual(atlas.birthdayVisible, True)
        self.assertEqual(atlas.contactInfoVisible, True)

    def test_signup_atlas_birthday(self) -> None:
        self.submit_form(
            "edit_atlas",
            "input_id_submit",
            select_checkboxes={
                "id_included": True,
                "id_birthdayVisible": True,
                "id_contactInfoVisible": False,
            },
        )
        self.assert_url_equal("edit_atlas")

        atlas = self.user.alumni.atlas
        self.assertEqual(atlas.included, True)
        self.assertEqual(atlas.birthdayVisible, True)
        self.assertEqual(atlas.contactInfoVisible, False)

    def test_signup_atlas_contact(self) -> None:
        self.submit_form(
            "edit_atlas",
            "input_id_submit",
            select_checkboxes={
                "id_included": True,
                "id_birthdayVisible": False,
                "id_contactInfoVisible": True,
            },
        )
        self.assert_url_equal("edit_atlas")

        atlas = self.user.alumni.atlas
        self.assertEqual(atlas.included, True)
        self.assertEqual(atlas.birthdayVisible, False)
        self.assertEqual(atlas.contactInfoVisible, True)

    def test_signup_atlas_minimal(self) -> None:
        self.submit_form(
            "edit_atlas",
            "input_id_submit",
            select_checkboxes={
                "id_included": True,
                "id_birthdayVisible": False,
                "id_contactInfoVisible": False,
            },
        )
        self.assert_url_equal("edit_atlas")

        atlas = self.user.alumni.atlas
        self.assertEqual(atlas.included, True)
        self.assertEqual(atlas.birthdayVisible, False)
        self.assertEqual(atlas.contactInfoVisible, False)

    def test_signup_atlas_empty(self) -> None:
        self.submit_form(
            "edit_atlas",
            "input_id_submit",
            select_checkboxes={
                "id_included": False,
                "id_birthdayVisible": False,
                "id_contactInfoVisible": False,
            },
        )
        self.assert_url_equal("edit_atlas")

        atlas = self.user.alumni.atlas
        self.assertEqual(atlas.included, False)
        self.assertEqual(atlas.birthdayVisible, False)
        self.assertEqual(atlas.contactInfoVisible, False)
