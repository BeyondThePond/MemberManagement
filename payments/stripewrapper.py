from __future__ import annotations
from alumni.models import Alumni
from typing import TypeVar, Optional, Callable, List, Any, Dict, Tuple

import stripe as stripeapi
from raven.contrib.django.raven_compat.models import client
from datetime import datetime, time
import time
import pytz

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar, Callable, Optional, List

    T = TypeVar["T"]
    from datetime import date


def _safe(
    operation: Callable[[stripeapi], T]
) -> Callable[[T], (Optional[T], Optional[str])]:
    """Performs a potentially unsafe operation that interacts with the stripe api"""

    result = None

    try:
        result = operation(stripeapi)
    except stripeapi.error.StripeError as e:
        client.captureException()
        return None, e

    return result, None


def _as_safe_operation(
    f: Callable[..., T]
) -> Callable[..., Tuple[Optional[T], Optional[str]]]:
    """Wraps a function with _safe"""

    def _wrapper(*args, **kwargs):
        return _safe(lambda stripe: f(stripe, *args, **kwargs))

    return _wrapper


def check_customer_stripe_props(alumni: Alumni, customer: str) -> List[str]:
    """Returns a list of errors for the customer"""

    header = "Customer {0!r} (for user {1!r}): ".format(
        customer["id"], alumni.profile.username
    )

    # errors to be populated
    errors = []

    # Compare fields that aren't identical
    props = _get_stripe_customer_props(alumni)
    for p in props.keys():
        expected = props[p]
        got = customer[p]
        if expected != got:
            errors.append(
                header
                + "Property {0!r}: Expected {1!r}, but got {2!r}".format(
                    p, expected, got
                )
            )

    # TODO: Check plan subscription

    # return the errors
    return errors


@_as_safe_operation
def create_customer(stripe: stripeapi, alumni_instance: Alumni) -> str:
    """Creates a new customer for a given alumni"""

    props = _get_stripe_customer_props(alumni_instance)
    customer = stripe.Customer.create(**props)
    return customer.id


@_as_safe_operation
def clear_all_payment_sources(stripe: stripeapi, customer_id: str) -> str:
    """Removes all payment sources from an alumni"""

    for source in stripe.Customer.retrieve(customer_id).sources.list().data:
        # cards can be deleted
        if source.object == "card":
            source.delete()

        # everything else can be detached
        else:
            source.detach()

    return True


@_as_safe_operation
def update_payment_method(
    stripe: stripeapi,
    customer_id: str,
    source_id: Optional[str],
    card_id: Optional[str],
) -> Optional[bool]:
    """Sets the default payment method for a customer to source or card"""

    # clear all existing methods
    cleared, err = clear_all_payment_sources(customer_id)
    if err != None:
        return

    # update the source and card id
    update = {}
    if source_id:
        update["source"] = source_id
    else:
        update["card"] = card_id

    stripe.Customer.modify(customer_id, **update)
    return True


@_as_safe_operation
def create_subscription(stripe: stripeapi, customer_id: str, plan_id: str) -> str:
    """Creates a subscription and returns its id"""

    subscription = stripe.Customer.retrieve(customer_id).subscriptions.create(
        plan=plan_id
    )
    return subscription.id


@_as_safe_operation
def update_subscription(
    stripe: stripeapi, subscription_id: str, new_plan_id: str
) -> str:
    """Updates the subscription with the given id to the one with the new id"""

    subscription = stripe.Subscription.retrieve(subscription_id)
    proration_date = int(time.time())

    stripe.Subscription.modify(
        subscription.id,
        items=[
            {
                "id": subscription["items"]["data"][0].id,
                "plan": new_plan_id,
            }
        ],
        proration_date=proration_date,
    )

    return True


@_as_safe_operation
def get_payment_table(stripe: stripeapi, customer_id: str) -> List[Dict[str, Any]]:
    """gets a table of payments for a customer"""
    invoices = [
        _invoice_to_dict(invoice_instance, upcoming=False)
        for invoice_instance in stripe.Invoice.list(customer=customer_id)
    ]

    try:
        upcoming = stripe.Invoice.upcoming(customer=customer_id)
    except stripe.error.InvalidRequestError as e:
        upcoming = None

    if upcoming is not None:
        invoices = [_invoice_to_dict(upcoming, upcoming=True)] + invoices

    return invoices


def _invoice_to_dict(
    invoice_instance: stripeapi.Invoice, upcoming: bool
) -> Dict[str, Any]:
    """Turns an invoice instance into a dict for downstream consumption"""
    return {
        "lines": [l for l in invoice_instance.lines],
        "date": invoice_instance.date,
        "total": [invoice_instance.total, invoice_instance.currency],
        "upcoming": upcoming,
        "paid": invoice_instance.paid,
        "closed": invoice_instance.closed,
    }


@_as_safe_operation
def get_methods_table(stripe: stripeapi, customer_id: str) -> List[Dict[str, str]]:
    """Gets a list of payment sources for a customer"""

    sources = stripe.Customer.retrieve(customer_id).sources.list().data
    return [_source_to_dict(source_instance) for source_instance in sources]


def _source_to_dict(source_instance: stripeapi.Source) -> Dict[str, str]:
    """Turns a source instance into a dict for downstream consumption"""
    if source_instance.object == "card":
        return {
            "kind": "card",
            "brand": source_instance.brand,
            "exp_month": source_instance.exp_month,
            "exp_year": source_instance.exp_year,
            "last4": source_instance.last4,
        }
    elif source_instance.type == "sepa_debit":
        return {
            "kind": "sepa",
            "last4": source_instance.sepa_debit.last4,
            "mandate_reference": source_instance.sepa_debit.mandate_reference,
            "mandate_url": source_instance.sepa_debit.mandate_url,
        }

    return {"kind": "unknown"}


@_as_safe_operation
def cancel_subscription(stripe: stripeapi, subscription_id: str) -> bool:
    """Cancels a subscription"""

    stripe.Subscription.delete(subscription_id)
    return True


@_as_safe_operation
def get_customer_created(stripe: stripeapi, customer_id: str) -> datetime:
    """Gets the time when a customer was created"""

    timestamp = stripe.Customer.retrieve(customer_id).created
    return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)


# todo: make api upgrade safe
@_as_safe_operation
def map_customers(stripe: stripeapi, fn: Callable[[Dict[str, str]], None]) -> int:
    """Calls a function on every customer"""

    # iterate over all the customers
    customers = stripe.Customer.list(limit=100)
    count = 0
    for customer_instance in customers.auto_paging_iter():
        fn(_customer_to_dict(customer_instance))
        count += 1
    return count


def _customer_to_dict(customer_instance: stripeapi.Customer) -> Dict[str, str]:
    """Turns a stripe customer instance into a dict for downstream consumption"""
    return {
        "id": customer_instance.id,
        "description": customer_instance.description,
        "email": customer_instance.email,
    }


@_as_safe_operation
def update_customer(
    stripe: stripeapi, customer_id: str, alumni_instance: Alumni
) -> bool:
    """Updates a stripe customer with standard properties"""
    props = _get_stripe_customer_props(alumni_instance)
    stripe.Customer.modify(customer_id, **props)
    return True


def _get_stripe_customer_props(alumni_instance: Alumni) -> Dict[str, str]:
    """Gets props for a stripe customer given an alumni"""

    return {
        "description": "Alumni Customer for {0!r} ({1!r})".format(
            alumni_instance.fullName, alumni_instance.profile.username
        ),
        "email": alumni_instance.email,
    }


def _pi_to_dict(pi_instance: stripeapi.PaymentIntent) -> Dict[str, str]:
    """Turns a stripe PaymentIntent instance into a dict for downstream consumption"""
    return {
        "id": pi_instance.id,
        "created": pi_instance.created,
        "customer": pi_instance.customer,
        "amount": pi_instance.amount,
        "amount_capturable": pi_instance.amount_capturable,
        "amount_received": pi_instance.amount_received,
        "status": pi_instance.status,
        "currency": pi_instance.currency,
    }


# todo: make api upgrade safe
@_as_safe_operation
def map_payment_intents(
    stripe: stripeapi,
    fn: Callable[[Dict[str, str]], None],
    since: Optional[date] = None,
) -> int:
    """Calls a function on every PaymentIntent"""

    created = None
    if since:
        created = {"gte": int(time.mktime(since.timetuple()))}

    # iterate over all the paymentintents
    pis = stripe.PaymentIntent.list(limit=100, created=created)
    count = 0
    for pi_instance in pis.auto_paging_iter():
        fn(_pi_to_dict(pi_instance))
        count += 1
    return count


@_as_safe_operation
def make_stripe_event(
    stripe: stripeapi, payload: str, sig_header: str, endpoint_secret: str
):
    return stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)


@_as_safe_operation
def get_customer_portal_url(stripe: stripeapi, customer_id, return_url) -> str:
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=return_url
    )
    return session.url


@_as_safe_operation
def get_subscriptions_for_customer(stripe: stripeapi, customer_id: str):
    """Retrieve all subscriptions for a given customer."""
    subscriptions = stripe.Subscription.list(customer=customer_id)
    return [
        {
            "id": sub.id,
            "start_date": sub.start_date,
            "end_date": sub.ended_at,
            "plan": {"id": sub.plan.id},
        }
        for sub in subscriptions.auto_paging_iter()
    ]
