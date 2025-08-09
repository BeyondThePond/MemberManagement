from __future__ import annotations

import datetime
from datetime import timedelta, date
from unittest import mock, SkipTest

from django.contrib.auth.models import User

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from datetime import timezone, datetime, date

from selenium.webdriver.common.by import By

from alumni.fields import (
    AlumniCategoryField,
    CollegeField,
    GenderField,
    TierField,
    DegreeField,
    ClassField,
    MajorField,
    IndustryField,
    JobField,
)
from alumni.models import Alumni
from MemberManagement.tests.integration import IntegrationTest, IntegrationTestBase

from selenium.webdriver.common.keys import Keys

MOCKED_TIME = datetime(2019, 9, 19, 16, 41, 17, 40, tzinfo=timezone.utc)
MOCKED_END = MOCKED_TIME + timedelta(days=2 * 365)
MOCKED_CUSTOMER = "cus_Fq8yG7rLrc6sKZ"

import os


class SignupTestBase(IntegrationTestBase):
    tier: str
    expect_subscription_created: bool

    def fill_out_nationality(self, *nations):
        """Fills out the nationality multiselect with the given nations"""

        # find the element and scroll it into view
        element = self.find_element("#id_nationality > div")
        self.selenium.execute_script("arguments[0].scrollIntoView(true)", element)

        # select each nation
        for nation in nations:
            element.click()
            element.send_keys(nation)
            element.find_element(By.XPATH, './/span[text()="' + nation + '"]').click()

    def assert_related_created(self, alumni: Alumni):
        """Checks that all related objects were created"""

        # approval object
        obj = alumni.approval
        self.assertEqual(obj.approval, False)
        self.assertEqual(obj.gsuite, None)
        self.assertEqual(obj.time, None)
        self.assertEqual(obj.autocreated, False)

        # address object
        obj = alumni.address
        self.assertEqual(obj.address_line_1, None)
        self.assertEqual(obj.address_line_2, None)
        self.assertEqual(obj.city, None)
        self.assertEqual(obj.zip, None)
        self.assertEqual(obj.state, None)
        self.assertEqual(obj.country, None)

        # social media object
        obj = alumni.social
        self.assertEqual(obj.facebook, None)
        self.assertEqual(obj.linkedin, None)
        self.assertEqual(obj.twitter, None)
        self.assertEqual(obj.instagram, None)
        self.assertEqual(obj.homepage, None)

        # jacobs data
        obj = alumni.jacobs
        self.assertEqual(obj.college, None)
        self.assertEqual(obj.degree, None)
        self.assertEqual(obj.graduation, ClassField.OTHER)
        self.assertEqual(obj.major, MajorField.OTHER)
        self.assertEqual(obj.comments, None)

        # job data
        obj = alumni.job
        self.assertEqual(obj.employer, None)
        self.assertEqual(obj.position, None)
        self.assertEqual(obj.industry, IndustryField.OTHER)
        self.assertEqual(obj.job, JobField.OTHER)

        # skills
        obj = alumni.skills
        self.assertEqual(obj.otherDegrees, None)
        self.assertEqual(obj.spokenLanguages, None)
        self.assertEqual(obj.programmingLanguages, None)
        self.assertEqual(obj.areasOfInterest, None)
        self.assertEqual(obj.alumniMentor, False)

        # atlas
        obj = alumni.atlas
        self.assertEqual(obj.included, False)
        self.assertEqual(obj.birthdayVisible, False)
        self.assertEqual(obj.contactInfoVisible, False)

        # membership
        obj = alumni.membership
        self.assertEqual(obj.tier, self.__class__.tier)
        self.assertEqual(obj.customer, MOCKED_CUSTOMER)

        # if we don't expect a subscription to be created, then we return immediatly
        if not self.__class__.expect_subscription_created:
            self.assertEqual(alumni.subscription, None)
            return

        # check that the subscription was created
        obj = alumni.subscription
        self.assertEqual(obj.start, MOCKED_TIME)
        self.assertEqual(obj.end, MOCKED_END)
        self.assertEqual(obj.subscription, None)
        self.assertEqual(obj.external, False)
        self.assertEqual(obj.tier, self.__class__.tier)

    def assert_related_not_created(self):
        """Asserts that the alumni and related objects have not been created"""

        self.assertEqual(
            Alumni.objects.first(), None, "Check that no alumni was created"
        )
        self.assertEqual(User.objects.first(), None, "Check that no user was created")

    def skipInCI(self):
        if os.environ.get("CI") == "true":
            raise SkipTest("Skipping test in CI")

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_ok_anna(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fill out the signup form ok
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "1948-11-07",  # TODO: not sure how this should work
            },
            select_checkboxes={"id_tos": True},
        )

        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()

        # check that we went to the subscription page
        if self.__class__.expect_subscription_created:
            self.assert_url_equal(
                "setup_setup",
                "Check that the user is redirected to the final setup url",
            )
        else:
            self.assert_url_equal(
                "setup_subscription",
                "Check that the user is redirected to the subscription url",
            )

        # check that the right alumni object was created
        obj = Alumni.objects.first()
        self.assertEqual(obj.profile.username, "afreytag")
        self.assertEqual(obj.givenName, "Anna")
        self.assertEqual(obj.middleName, "")
        self.assertEqual(obj.familyName, "Freytag")
        self.assertEqual(obj.email, "AnnaFreytag@dayrep.com")
        self.assertEqual(obj.existingEmail, None)
        self.assertEqual(obj.resetExistingEmailPassword, False)
        self.assertEqual(obj.sex, GenderField.UNSPECIFIED)
        self.assertEqual(obj.birthday, date(1948, 11, 7))
        self.assertListEqual(list(map(lambda c: c.name, obj.nationality)), ["Germany"])
        self.assertEqual(obj.category, AlumniCategoryField.REGULAR)

        # check that the related object was created
        self.assert_related_created(obj)
        mocked.assert_has_calls([mock.call(obj)])

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_ok_anna1(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fake an existing user
        User.objects.create_user("afreytag")

        # fill out the signup form ok
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "1948-11-07",  # TODO: not sure how this should work
            },
            select_checkboxes={"id_tos": True},
        )

        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()

        # check that we went to the subscription page
        if self.__class__.expect_subscription_created:
            self.assert_url_equal(
                "setup_setup",
                "Check that the user is redirected to the final setup url",
            )
        else:
            self.assert_url_equal(
                "setup_subscription",
                "Check that the user is redirected to the subscription url",
            )

        # check that the right alumni object was created
        obj = Alumni.objects.first()
        self.assertEqual(obj.profile.username, "afreytag1")
        self.assertEqual(obj.givenName, "Anna")
        self.assertEqual(obj.middleName, "")
        self.assertEqual(obj.familyName, "Freytag")
        self.assertEqual(obj.email, "AnnaFreytag@dayrep.com")
        self.assertEqual(obj.existingEmail, None)
        self.assertEqual(obj.resetExistingEmailPassword, False)
        self.assertEqual(obj.sex, GenderField.UNSPECIFIED)
        self.assertEqual(obj.birthday, date(1948, 11, 7))
        self.assertListEqual(list(map(lambda c: c.name, obj.nationality)), ["Germany"])
        self.assertEqual(obj.category, AlumniCategoryField.REGULAR)

        # check that the related object was created
        self.assert_related_created(obj)
        mocked.assert_has_calls([mock.call(obj)])

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_ok_anna2(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fake existing users
        User.objects.create_user("afreytag")
        User.objects.create_user("afreytag1")

        # fill out the signup form ok
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Charlotte Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "1948-11-07",
            },
            select_checkboxes={"id_tos": True},
        )
        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()

        # check that we went to the subscription page
        if self.__class__.expect_subscription_created:
            self.assert_url_equal(
                "setup_subscription",
                "Check that the user is redirected to the final setup url",
            )
        else:
            self.assert_url_equal(
                "portal_register",
                "Check that the user is redirected to the subscription url",
            )

        # check that the right alumni object was created
        obj = Alumni.objects.first()
        self.assertEqual(obj.profile.username, "afreytag2")
        self.assertEqual(obj.givenName, "Anna")
        self.assertEqual(obj.middleName, "Charlotte")
        self.assertEqual(obj.familyName, "Freytag")
        self.assertEqual(obj.email, "AnnaFreytag@dayrep.com")
        self.assertEqual(obj.existingEmail, None)
        self.assertEqual(obj.resetExistingEmailPassword, False)
        self.assertEqual(obj.sex, GenderField.UNSPECIFIED)
        self.assertEqual(obj.birthday, date(1948, 11, 7))
        self.assertListEqual(list(map(lambda c: c.name, obj.nationality)), ["Germany"])
        self.assertEqual(obj.category, AlumniCategoryField.REGULAR)

        # check that the related object was created
        self.assert_related_created(obj)
        mocked.assert_has_calls([mock.call(obj)])

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(None, "Debug failure")
    )
    def test_signup_fail_stripe(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fill out the signup form ok
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "1948-11-07",
            },
            select_checkboxes={"id_tos": True},
        )

        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()
        self.find_element(None)

        self.assert_url_equal("register")
        mocked.assert_called()
        self.assert_related_not_created()

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_fail_notos(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fill out the signup form ok
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "1948-11-07",
            },
            select_checkboxes={"id_tos": False},
        )

        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()
        self.find_element(None)

        self.assert_url_equal("register")
        mocked.assert_not_called()
        self.assert_related_not_created()

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_fail_restricedemail(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        for domain in ["jacobs-alumni.de", "jacobs-university.de"]:
            # fill out the signup form ok
            btn = self.fill_out_form(
                "register",
                "input_id_submit",
                send_form_keys={
                    "id_fullname": "Anna Freytag",
                    "id_email": "AnnaFreytag@" + domain,
                },
                script_value={
                    "id_birthday": "1948-11-07",
                },
                select_checkboxes={"id_tos": True},
            )

            # select tier and nationality
            self.find_element("#id_tier_" + self.__class__.tier).click()
            self.fill_out_nationality("Germany")

            # click and wait for page load
            btn.click()
            self.find_element(None)

            self.assert_url_equal("register")
            mocked.assert_not_called()
            self.assert_related_not_created()

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_fail_tooyoung(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fill out the signup form ok
        btn = self.submit_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "2012-01-01",
            },
            select_checkboxes={"id_tos": True},
        )

        self.assert_url_equal("register")
        mocked.assert_not_called()
        self.assert_related_not_created()

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_fail_existingemail(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # create an alumni with the existing email
        user = User.objects.create(username="afreytag")
        alumni = Alumni.objects.create(
            profile=user,
            givenName="Anna",
            familyName="Freytag",
            email="AnnaFreytag@dayrep.com",
            sex=GenderField.UNSPECIFIED,
            birthday=date.today(),
            category=AlumniCategoryField.REGULAR,
        )

        # fill signup form
        btn = self.fill_out_form(
            "register",
            "input_id_submit",
            send_form_keys={
                "id_fullname": "Anna Freytag",
                "id_email": "AnnaFreytag@dayrep.com",
            },
            script_value={
                "id_birthday": "2012-01-01",
            },
            select_checkboxes={"id_tos": True},
        )

        # select tier and nationality
        self.find_element("#id_tier_" + self.__class__.tier).click()
        self.fill_out_nationality("Germany")

        # click and wait for page load
        btn.click()
        self.find_element(None)

        # remove the dummy objects
        alumni.delete()
        user.delete()

        self.assert_url_equal("register")
        mocked.assert_not_called()
        self.assert_related_not_created()

    @mock.patch("django.utils.timezone.now", mock.Mock(return_value=MOCKED_TIME))
    @mock.patch(
        "payments.stripewrapper.create_customer", return_value=(MOCKED_CUSTOMER, None)
    )
    def test_signup_empty(self, mocked: mock.Mock) -> None:
        self.skipInCI()

        # fill out an empty form
        self.submit_form("register", "input_id_submit")

        self.assert_url_equal("register")
        mocked.assert_not_called()
        self.assert_related_not_created()


class StarterSignupTest(SignupTestBase, IntegrationTest, StaticLiveServerTestCase):
    tier = TierField.STARTER
    expect_subscription_created = True


class ContributorSignupTest(SignupTestBase, IntegrationTest, StaticLiveServerTestCase):
    tier = TierField.CONTRIBUTOR
    expect_subscription_created = False


class PatronSignupTest(SignupTestBase, IntegrationTest, StaticLiveServerTestCase):
    tier = TierField.PATRON
    expect_subscription_created = False
