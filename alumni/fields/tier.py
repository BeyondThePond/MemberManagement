from __future__ import annotations

from MemberManagement import settings

from .custom import CustomTextChoiceField

__all__ = ["TierField"]


class TierField(CustomTextChoiceField):
    STARTER = "st"
    CONTRIBUTOR = "co"
    PATRON = "pa"

    CHOICES = [
        (CONTRIBUTOR, "Contributor – Standard membership for 39€ p.a."),
        (STARTER, "Starter – Free Membership for 0€ p.a."),
        (PATRON, "Patron – Premium membership for 249€ p.a."),
    ]

    STRIPE_IDS = {
        CONTRIBUTOR: "contributor-membership",
        STARTER: "starter-membership",
        PATRON: "patron-membership",
    }

    STRIPE_ID_TO_TIER = {
        # Legacy IDs
        "contributor-membership": CONTRIBUTOR,
        "patron-membership": PATRON,
        "starter-membership": STARTER,
        # New IDs
        settings.STRIPE_CONTRIBUTOR_PRODUCT_ID: CONTRIBUTOR,
        settings.STRIPE_PATRON_PRODUCT_ID: PATRON,
        settings.STRIPE_STARTER_PRODUCT_ID: STARTER,
    }

    @staticmethod
    def get_description(value):
        for k, v in TierField.CHOICES:
            if k == value:
                return v

    @staticmethod
    def get_stripe_id(value):
        return TierField.STRIPE_IDS[value]

    @staticmethod
    def get_tier_from_stripe_id(stripe_id: str) -> str:
        """Maps a Stripe plan ID to a membership tier."""

        return TierField.STRIPE_ID_TO_TIER.get(stripe_id, "Unknown")
