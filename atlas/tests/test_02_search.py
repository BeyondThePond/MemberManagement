from __future__ import annotations
from urllib.parse import quote

import pytest
import unittest
from unittest import mock

from alumni.models import Alumni
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from datetime import timezone, datetime

from selenium.webdriver.common.by import By

from MemberManagement.tests.integration import IntegrationTest

pytestmark = pytest.mark.skip(reason="Atlas is no longer used.")


@unittest.skip("Atlas is no longer used.")
class SearchResultsTest(IntegrationTest, StaticLiveServerTestCase):
    fixtures = ["registry/tests/fixtures/integration.json"]
    user = "Mounfem"

    def _assert_search_results(self, query: str, names: List[str]) -> None:
        """Asserts that a given query results in the given results"""
        self.submit_form(
            "atlas_home", "id_button_search", send_form_keys={"searchInput": query}
        )
        self._assert_on_result_page(query, names)

    def _assert_on_result_page(self, query: str, names: List[str]) -> None:
        """Asserts that a given set of search results are showing up on the current search page"""
        quoted_query = "+".join(map(quote, query.split(" ")))
        self.assert_url_equal("atlas_search", get_params={"query": quoted_query})

        # get the links to the actual search results
        search_result_links = self.selenium.find_elements(
            By.CLASS_NAME, "search_result_link"
        )
        got_result_list = [l.get_attribute("href") for l in search_result_links]

        # get the expected links to the search results
        alumni = [Alumni.objects.get(profile__username=name).pk for name in names]
        expected_result_list = [
            self.live_server_url + self._resolve_url("atlas_profile", kwargs={"id": pk})
            for pk in alumni
        ]

        # check that they are equal
        self.assertListEqual(got_result_list, expected_result_list)

    def test_search_results_simple(self) -> None:
        self._assert_search_results("Elena", ["eilie"])  # name
        self._assert_search_results("Bremen", ["Ramila"])  # city
        self._assert_search_results(
            "Bachelor of Computer Science IUB", ["Mounfem"]
        )  # other degrees
        self._assert_search_results("Spanish", ["Mounfem"])  # other languages
        self._assert_search_results("CSS", ["Mounfem"])  # programming languages
        self._assert_search_results("Human Rights", ["Mounfem"])  # areas of interest
        self._assert_search_results("Court Judge Inc", ["Aint1975"])  # employer
        self._assert_search_results("Researcher", ["Irew1996"])  # position

    def test_search_results_notincluded(self) -> None:
        self._assert_search_results("Yuan", [])  # he's not included

    def test_search_advanced_college(self) -> None:
        submit_button = self.fill_out_form("atlas_home", "id_button_search")

        self.select_dropdown("aft_id_select_college", "Krupp")
        self.selenium.find_element(By.ID, "aft_id_button_college").click()

        # click and assert results
        submit_button.click()
        self._assert_on_result_page(" college: 1", ["eilie", "Ramila"])

    def test_search_advanced_college_andname(self) -> None:
        submit_button = self.fill_out_form(
            "atlas_home", "id_button_search", send_form_keys={"searchInput": "Elena"}
        )

        self.select_dropdown("aft_id_select_college", "Krupp")
        self.selenium.find_element(By.ID, "aft_id_button_college").click()

        # click and assert results
        submit_button.click()
        self._assert_on_result_page("Elena college: 1", ["eilie"])
