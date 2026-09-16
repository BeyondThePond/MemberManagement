from __future__ import annotations
from urllib.parse import quote

import pytest
import unittest
from unittest import mock

from alumni.models import Alumni
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from MemberManagement.tests.integration import IntegrationTest

pytestmark = pytest.mark.skip(reason="Atlas is no longer used.")


@unittest.skip("Atlas is no longer used.")
class ProfileTest(IntegrationTest, StaticLiveServerTestCase):
    fixtures = ["registry/tests/fixtures/integration.json"]
    user = "Mounfem"

    def test_socials_visible(self) -> None:
        user = Alumni.objects.get(profile__username="Mounfem").profile.pk
        self.load_live_url("atlas_profile", url_kwargs={"id": user})
        self.assert_element_exists("#id_socials")
        self.assert_element_exists("#id_contact")

    def test_socials_invisble(self) -> None:
        user = Alumni.objects.get(profile__username="Aint1975").profile.pk
        self.load_live_url("atlas_profile", url_kwargs={"id": user})
        self.assert_element_not_exists("#id_socials")
        self.assert_element_not_exists("#id_contact")

    def test_profile_hidden(self) -> None:
        user = Alumni.objects.get(profile__username="Douner").profile.pk
        self.load_live_url("atlas_profile", selector="body", url_kwargs={"id": user})
        self.assert_element_not_exists(".main-container")
