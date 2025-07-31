from __future__ import annotations

from django.db import models


from django.utils import timezone
from datetime import datetime, timedelta

from alumni.models import Alumni
from alumni.fields import TierField, AlumniCategoryField

from registry.alumni import AlumniComponentMixin

from payments import stripewrapper

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, Any, Tuple
    from datetime import datetime, timedelta


@Alumni.register_component(6)
class MembershipInformation(AlumniComponentMixin, models.Model):
    """The (payment-related) membership information of an Alumni Member"""

    SETUP_COMPONENT_NAME = "membership"

    member: Alumni = models.OneToOneField(
        Alumni, related_name="membership", on_delete=models.CASCADE
    )

    tier: str = TierField(default=TierField.CONTRIBUTOR, help_text="Membership Tier")

    desired_tier: Optional[str] = TierField(
        null=True, blank=True, help_text="Desired Membership Tier"
    )

    customer: Optional[str] = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The stripe customer id for the user",
    )

    stripe_check: Optional[bool] = models.BooleanField(
        null=True, blank=True, help_text="Internal Column used by Stripe checking"
    )

    def create_subscription(self) -> Optional[SubscriptionInformation]:
        """Creates a new subscription when newly entered payment details are available"""

        # if we have a 'desired_tier' this should be used to create the subscription
        # as there are now payment methods available.
        if self.desired_tier is not None:
            tier = self.desired_tier
            update_mode = True
        else:
            tier = self.tier
            update_mode = False

        # Create a stripe subscription on the given plan

        plan = TierField.get_stripe_id(tier)
        sub_id, err = stripewrapper.create_subscription(self.customer, plan)
        if err is not None:
            return None

        # if we updated the tier
        if update_mode:
            if self.member.subscription is not None:
                self.member.subscription.set_end()
            self.tier = self.desired_tier
            self.desired_tier = None
            self.save()

        # finally create the actual subscription object
        instance = SubscriptionInformation.start_new_subscription(
            self.member, sub_id, length=None, tier=tier
        )
        if update_mode and instance is not None:
            instance.created_from_update = True
        return instance

    def cancel_create_subscription(self) -> Optional[SubscriptionInformation]:
        """Cancels creating a susbcription and goes to the starter tier instead"""

        if self.desired_tier is not None:
            update_mode = True
        else:
            update_mode = False

        # if we already have a subscription
        sub = self.member.subscription
        the_sub = None
        if sub is not None:
            # if it is starter => done
            if sub.tier != TierField.STARTER:
                raise Exception(
                    "Can not cancel creating subscription: Existing subscription is not Starter Tier. "
                )

            the_sub = sub

        # create the subscription
        if the_sub is None:
            the_sub = SubscriptionInformation.create_starter_subscription(self.member)

        # store the new state
        self.tier = TierField.STARTER
        self.desired_tier = None
        self.save()

        # log if we were in update mode
        the_sub.created_from_update = update_mode

        # and return it
        return the_sub

    def change_tier(self) -> Tuple[Optional[SubscriptionInformation], Optional[str]]:
        """Designates this user as changing tier"""

        # the tier we want to switch to
        desired_tier = self.desired_tier

        # if the desired tier is none, we are already done
        if desired_tier is None:
            return self.member.subscription, None

        # we are already on the desired tier
        # so remove the desired_tier flag
        if desired_tier == self.tier:
            self.desired_tier = None
            self.save()
            return self.member.subscription, None

        # There are 3*2 = 6 possiblitlies for switche

        # we close the current subscription and start a new starter one
        # Contributor -> Starter
        # Patron -> Starter
        if desired_tier == TierField.STARTER:
            return self._downgrade_to_starter()

        # we need to ask for payment details because we don't have them yet
        # - Starter -> Contributor
        # - Starter -> Patron
        if self.tier == TierField.STARTER:
            return self._upgrade_to_paid(desired_tier)

        # we switch between paid tiers and pro-rate
        # Contributor -> Patron
        # Patron -> Contributor
        return self._switch_paid_tier(desired_tier)

    def _downgrade_to_starter(
        self,
    ) -> Tuple[Optional[SubscriptionInformation], Optional[str]]:
        if self.member.category != AlumniCategoryField.REGULAR:
            return (
                None,
                "Non-regular Alumni are not allowed to downgrade to the free tier. ",
            )

        # cancel the active subscription
        sub = self.member.subscription
        if sub is not None:
            if not sub.cancel():
                return None, "Unable to cancel active subscription"

        # set the tier to starter
        self.tier = TierField.STARTER
        self.desired_tier = None
        self.save()

        # create a new starter subscription
        instance = SubscriptionInformation.create_starter_subscription(self.member)

        # remove all the payment sources
        _, err = stripewrapper.clear_all_payment_sources(self.customer)
        if err is not None:
            return None, "Unable to remove payment methods"

        # and return the instance
        return instance, None

    def _upgrade_to_paid(self, desired_tier: str) -> Tuple[None, None]:
        """Upgrades from the free to the desired tier"""

        # store the 'desired' tier, so that we know to ask for payment details
        self.desired_tier = desired_tier
        self.save()

        return None, None

    def _switch_paid_tier(
        self, desired_tier: str
    ) -> Tuple[Optional[SubscriptionInformation], Optional[str]]:
        """Switches the paid tier"""

        # find the current subscription
        sub = self.member.subscription
        if sub is None or sub.subscription is None:
            return None, "Cannot find current subscription"
        subscription = sub.subscription

        # update the remote subscription
        plan = TierField.get_stripe_id(desired_tier)
        _, err = stripewrapper.update_subscription(subscription, plan)
        if err is not None:
            return None, "Unable to switch subscription to new plan"

        # end the current subscription, set the new tier
        sub.set_end()
        self.tier = desired_tier
        self.desired_tier = None
        self.save()

        # Create the new subscription
        instance = SubscriptionInformation.start_new_subscription(
            self.member, subscription, tier=desired_tier
        )
        return instance, None

    @classmethod
    def allow_tier_and_category(cls, tier: str, category: str) -> bool:
        """Checks if a given category and tier of alumni is allowed"""

        # regular alumni are allowed to pick any category
        if category == AlumniCategoryField.REGULAR:
            return True

        # other types only can't be starter
        return tier != TierField.STARTER


@Alumni.register_component(7)
class SubscriptionInformation(AlumniComponentMixin, models.Model):
    SETUP_COMPONENT_NAME = "subscription"

    class Meta:
        ordering = ["-start"]

    member: Alumni = models.ForeignKey(Alumni, on_delete=models.CASCADE)

    start: datetime = models.DateTimeField(
        help_text="The start date for the subscription"
    )
    end: Optional[datetime] = models.DateTimeField(
        blank=True, null=True, help_text="The end date for the subscription"
    )

    subscription: Optional[str] = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="The Stripe Subscription ID for the given subscription",
    )
    external: bool = models.BooleanField(
        default=False, help_text="Subscription is managed externally"
    )

    tier: str = TierField(help_text="Membership Tier")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.created_from_update = False

    @classmethod
    def component_exists(cls, alumni: Alumni) -> bool:
        """Checks if an alumni has this component set"""

        # if we don't have a subscription the component does not exist
        if not SubscriptionInformation.objects.filter(member=alumni).exists():
            return False

        # if we have no membership, we don't have this component
        obj = MembershipInformation.objects.get(member=alumni)
        if obj is None:
            return False

        # if the desired_tier is already done, then we are done
        return obj.desired_tier is None

    def cancel(self) -> bool:
        """Cancels this subscription along with the stripe subscription"""
        if self.end is not None:
            raise Exception("Subscription already cancelled")

        if not self.subscription:
            raise Exception("Can not cancel subscription: No subscription")

        # cancel the subscription
        _, err = stripewrapper.cancel_subscription(self.subscription)
        if err is not None:
            return False

        # and set the end of the subscription
        self.set_end()

        return True

    def set_end(self) -> None:
        """Marks this subscription as having ended"""

        self.end = timezone.now()
        self.save()

    @property
    def active(self) -> bool:
        """Property indicating if the subscription is active"""

        return self.end is None or (self.end > timezone.now())

    @property
    def time_left(self) -> Optional[timedelta]:
        """Return the time left until the subscription expires or None"""

        # if we are not active or are no longer active
        if not self.active or self.end is None:
            return None

        # return the timedelta left
        return timezone.now() - self.end

    @classmethod
    def create_starter_subscription(cls, alumni: Alumni) -> SubscriptionInformation:
        # creates a new starter subscription
        return cls.start_new_subscription(
            alumni, None, length=timedelta(days=2 * 365), tier=TierField.STARTER
        )

    @classmethod
    def start_new_subscription(
        cls,
        alumni: Alumni,
        subscription: Optional[str],
        length: Optional[timedelta] = None,
        tier: Optional[str] = None,
    ) -> SubscriptionInformation:
        # the new subscription starts now
        start = timezone.now()

        # compute the end of the subscription
        end = None
        if length is not None:
            if not isinstance(length, timedelta):
                raise TypeError("Expected length to be datetime.timedelta or None")

            end = start + length

        # If we did not create an alumni membership, create a new one
        if tier is None:
            tier = alumni.membership.tier

        # and create the new subscription
        return cls.objects.create(
            member=alumni, start=start, end=end, subscription=subscription, tier=tier
        )

    @classmethod
    def sync_from_stripe(cls, alumni: Alumni) -> Optional[SubscriptionInformation]:
        """Syncs the SubscriptionInformation object with data from Stripe."""
        membership = alumni.membership

        if not membership or not membership.customer:
            return None

        # Retrieve the Stripe subscription for the customer
        stripe_subscriptions, err = stripewrapper.get_subscriptions_for_customer(
            membership.customer
        )

        if not stripe_subscriptions:
            return None

        # Assume the first subscription is the active one
        stripe_subscription = stripe_subscriptions[0]

        # Update or create the SubscriptionInformation object
        subscription_info, created = cls.objects.update_or_create(
            member=alumni,
            subscription=stripe_subscription["id"],
            defaults={
                "start": datetime.utcfromtimestamp(stripe_subscription["start_date"]),
                "end": datetime.utcfromtimestamp(stripe_subscription["end_date"])
                if stripe_subscription["end_date"]
                else None,
                "tier": TierField.get_tier_from_stripe_id(
                    stripe_subscription["plan"]["id"]
                ),
                "external": False,
            },
        )

        return subscription_info


class PaymentIntent(models.Model):
    stripe_id = models.CharField(max_length=256)
    data = models.JSONField()

    def __str__(self):
        return self.stripe_id
