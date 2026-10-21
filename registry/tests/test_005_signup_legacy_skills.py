from __future__ import annotations

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from MemberManagement.tests.integration import IntegrationTest


class SkillsTest(IntegrationTest, StaticLiveServerTestCase):
    fixtures = ["registry/tests/fixtures/signup_04_job.json"]
    user = "Mounfem"

    def test_signup_skills_complete(self) -> None:
        self.submit_form(
            "setup_skills",
            "input_id_submit",
            send_form_keys={
                "id_otherDegrees": "Bachelor of Computer Science from IUB",
                "id_spokenLanguages": "German, English, Spanish",
                "id_programmingLanguages": "HTML, CSS, JavaScript, Python",
                "id_areasOfInterest": "Start-Ups, Surfing, Big Data, Human Rights",
            },
            select_checkboxes={
                "id_alumniMentor": True,
            },
        )

        self.assert_url_equal(
            "setup_membership",
            "Check that the user gets redirected to the membership page",
        )

        skills = self.user.alumni.skills
        self.assertEqual(skills.otherDegrees, "Bachelor of Computer Science from IUB")
        self.assertEqual(skills.spokenLanguages, "German, English, Spanish")
        self.assertEqual(skills.programmingLanguages, "HTML, CSS, JavaScript, Python")
        self.assertEqual(
            skills.areasOfInterest, "Start-Ups, Surfing, Big Data, Human Rights"
        )
        self.assertEqual(skills.alumniMentor, True)

    def test_signup_job_empty(self) -> None:
        self.submit_form(
            "setup_skills",
            "input_id_submit",
            send_form_keys={
                "id_otherDegrees": "",
                "id_spokenLanguages": "",
                "id_programmingLanguages": "",
                "id_areasOfInterest": "",
            },
            select_checkboxes={
                "id_alumniMentor": False,
            },
        )

        self.assert_url_equal(
            "setup_membership",
            "Check that the user gets redirected to the membership page",
        )

        skills = self.user.alumni.skills
        self.assertEqual(skills.otherDegrees, "")
        self.assertEqual(skills.spokenLanguages, "")
        self.assertEqual(skills.programmingLanguages, "")
        self.assertEqual(skills.areasOfInterest, "")
        self.assertEqual(skills.alumniMentor, False)
