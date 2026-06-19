# Payments with Stripe

Stripe is the default. The rules that keep billing from becoming a support
nightmare: **isolate the SDK, verify every webhook, and make webhook handling
idempotent.** Use `stripe>=15`.

## Isolate the SDK

Every Stripe call lives in `services/stripe/` — nothing else imports `stripe`.
That keeps routes mockable and gives one place to swap API styles.

```python
# services/stripe/client.py
import stripe
from myapp.config import get_settings

_s = get_settings()
stripe.api_key = _s.stripe_secret_key          # legacy global, used by webhook verify
client = stripe.StripeClient(_s.stripe_secret_key)  # modern client for API calls
```

Blocking SDK calls inside an async handler should be offloaded
(`await anyio.to_thread.run_sync(...)`) or use the async API surface
(`*.create_async`) where available.

## Checkout

Hosted Checkout for both one-time and subscription billing — let Stripe own the
payment page. Drive behavior with `metadata` so the webhook can fulfill correctly.

```python
# services/stripe/checkout.py
def create_checkout(price_id: str, customer_id: str, *, mode: str, user_id: int):
    return client.checkout.sessions.create({
        "mode": mode,                       # "payment" | "subscription"
        "customer": customer_id,
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/billing",
        "metadata": {"user_id": str(user_id)},
    })
```

Use Stripe's billing portal for self-serve plan changes/cancellation rather than
building your own.

## The Webhook — one endpoint, verified, idempotent

Exactly **one** unauthenticated route. Verify the signature with the raw body, then
dedupe on the event id before doing anything.

```python
# api/webhooks.py
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: SessionDep):
    payload = await request.body()                 # raw bytes — never the parsed JSON
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "invalid signature")

    if await already_processed(db, event["id"]):   # idempotency table
        return {"status": "duplicate"}
    await record_event(db, event["id"], event["type"])

    await dispatch(db, event)                       # by type; unknown types are a no-op
    return {"status": "ok"}
```

```python
async def dispatch(db, event):
    handlers = {
        "checkout.session.completed":      fulfill_checkout,
        "customer.subscription.updated":   sync_subscription,
        "customer.subscription.deleted":   cancel_subscription,
        "invoice.payment_failed":          flag_past_due,
    }
    handler = handlers.get(event["type"])
    if handler:                                     # never 500 on an event you don't handle
        await handler(db, event["data"]["object"])
```

### Non-negotiables

- **Verify with the raw request body.** Re-serializing the parsed JSON changes bytes
  and the signature check fails.
- **Idempotency table.** Stripe retries and may deliver duplicates. Persist handled
  event ids and skip repeats — fulfillment must be exactly-once.
- **Never 500 on an unknown event.** Return 200; an exception makes Stripe retry
  forever. Map unknown subscription statuses to a safe default rather than crashing.
- **Gate on configuration.** `billing_enabled` (both secret + webhook secret present)
  lets the app run in a demo/free mode when Stripe isn't configured.

## Provision the webhook in Terraform

Create the endpoint and read its signing secret as code, then pipe it straight into
the app's environment — no copy-pasting secrets from the dashboard.

```hcl
resource "stripe_webhook_endpoint" "app" {
  url            = "https://${var.app_host}/api/v1/stripe/webhook"
  enabled_events = ["checkout.session.completed",
                    "customer.subscription.updated",
                    "customer.subscription.deleted",
                    "invoice.payment_failed"]
}
# stripe_webhook_endpoint.app.secret -> set as MYAPP_STRIPE_WEBHOOK_SECRET on the service
```

## Marketplace / split payments

If you take a fee on payments between users, use Stripe Connect (Express accounts)
with destination charges and an explicit `application_fee_amount` / platform-fee
percentage. Keep the platform-billed flow (you charge the user) and the
pass-through flow (user charges user, you skim) as separate, clearly named code
paths.
