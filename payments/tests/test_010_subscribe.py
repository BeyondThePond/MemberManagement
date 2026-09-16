from __future__ import annotations

from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SubscribeCheckoutTestBase:
    user = "Mounfem"
    expected_price_id = None

    def setUp(self) -> None:
        self.user_obj = User.objects.get(username=self.user)
        self.client.force_login(self.user_obj)

    def test_signup_checkout_page_renders(self) -> None:
        response = self.client.get(reverse("setup_subscription"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "button_id_presubmit")

    @mock.patch("payments.views.stripe.checkout.Session.create")
    def test_signup_redirects_to_stripe_checkout(self, checkout_create: mock.Mock):
        checkout_create.return_value = mock.Mock(
            url="https://checkout.stripe.test/session"
        )

        response = self.client.post(reverse("setup_subscription"), {"checkout": "1"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.test/session")
        checkout_create.assert_called_once()
        call_kwargs = checkout_create.call_args.kwargs
        self.assertEqual(
            call_kwargs["customer"], self.user_obj.alumni.membership.customer
        )
        self.assertEqual(
            call_kwargs["line_items"],
            [{"price": self.expected_price_id, "quantity": 1}],
        )

    @mock.patch("payments.views.stripe.checkout.Session.create")
    def test_signup_checkout_error_stays_on_page(self, checkout_create: mock.Mock):
        checkout_create.side_effect = Exception("Debug failure")

        response = self.client.post(reverse("setup_subscription"), {"checkout": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Something went wrong when creating the checkout session"
        )


class ContributorSubscribeTest(SubscribeCheckoutTestBase, TestCase):
    fixtures = ["registry/tests/fixtures/signup_07b_contributor.json"]
    expected_price_id = settings.STRIPE_CONTRIBUTOR_PRICE_ID


class PatronSubscribeTest(SubscribeCheckoutTestBase, TestCase):
    fixtures = ["registry/tests/fixtures/signup_07c_patron.json"]
    expected_price_id = settings.STRIPE_PATRON_PRICE_ID
