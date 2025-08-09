from __future__ import annotations

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from .integration import IntegrationTest

PORTAL_FIXED = [
    "portal",
    "edit",
    "edit_address",
    "edit_social",
    "edit_jacobs",
    "edit_job",
    "edit_skills",
    "edit_atlas",
]
PORTAL_SETUP_URLS = [
    "root",
    "root_register",
    "register",
    "setup",
    "setup_address",
    "setup_social",
    "setup_jacobs",
    "setup_job",
    "setup_skills",
    "setup_atlas",
    "setup_setup",
]
SETUP_PROTECTED_URLS = (
    PORTAL_SETUP_URLS
    + PORTAL_FIXED
    + [
        "registry_vote",
        "setup_membership",
    ]
)


class AccessTest(IntegrationTest, StaticLiveServerTestCase):
    """Checks that the homepage redirects appropriatly for the different stages of approval"""

    def test_none(self) -> None:
        self.assert_url_follow("root", "root", "Root is not redirected when logged out")
        self.assert_url_follow(
            "root_register",
            "register",
            "root_register is redirected to register when logged out",
        )
        self.assert_url_follow(
            "register", "register", "register url is not redirected when logged out"
        )
        self.assert_url_follow(
            "root_vote",
            "login",
            "vote url is redirected when not logged in",
            new_url_reverse_get_params={"next": "registry_vote"},
        )

        for url in SETUP_PROTECTED_URLS:
            if url in ["root", "register", "root_register"]:
                continue
            self.assert_url_follow(
                url,
                "login",
                "{} is protected by login".format(url),
                new_url_reverse_get_params={"next": url},
            )

    def test_setup_address(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_00_register.json")
        self.login("Mounfem")

        # check that all the protected urls go to the first page of the setup
        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_address", "{} is protected by setup".format(url)
            )

    def test_setup_social(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_01_address.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_social", "{} is protected by setup".format(url)
            )

    def test_setup_jacobs(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_02_social.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_jacobs", "{} is protected by setup".format(url)
            )

    def test_setup_job(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_03_jacobs.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_job", "{} is protected by setup".format(url)
            )

    def test_setup_skills(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_04_job.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_skills", "{} is protected by setup".format(url)
            )

    def test_setup_atlas(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_05_skills.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_atlas", "{} is protected by setup".format(url)
            )

    def test_setup_tier(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_06_atlas.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(
                url, "setup_membership", "{} is protected by setup".format(url)
            )

    def test_setup_starter(self) -> None:
        self.load_fixture("registry/tests/fixtures/signup_07a_starter.json")
        self.login("Mounfem")

        for url in SETUP_PROTECTED_URLS:
            self.assert_url_follow(url, "setup_setup")

    def test_setup_completed(self) -> None:
        self.load_fixture(
            "registry/tests/fixtures/signup_09_finalize.json",
        )
        self.login("Mounfem")

        for url in PORTAL_FIXED:
            self.assert_url_follow(url, url, "{} is not protected by setup".format(url))

        for url in PORTAL_SETUP_URLS:
            self.assert_url_follow(
                url, "portal", "{} is not allowed after setup".format(url)
            )
