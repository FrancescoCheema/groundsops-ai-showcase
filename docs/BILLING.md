# Subscription billing

GroundsOps sells one plan per company workspace through Stripe Checkout and the
Stripe customer portal. Card data never touches GroundsOps servers.

## How it works

| Stage | Behaviour |
|---|---|
| Sign-up | A new workspace starts a free trial (`BILLING_TRIAL_DAYS`, default 14). |
| Trial | Everything works. A banner appears in the final 7 days. |
| Subscribe | An admin clicks **Subscribe** → Stripe Checkout. Unused trial days carry over to Stripe, so subscribing early never costs trial time. |
| Active | Stripe webhooks keep `subscription_status` and `current_period_end` in sync. |
| Payment failed (`past_due`) | Workspace stays writable while Stripe retries the card; admins see a warning banner. |
| Trial ended / canceled / unpaid | Workspace becomes **read-only**. Data stays viewable and exportable; create/update/delete requests return `402 Payment Required`. Billing endpoints stay reachable so the admin can subscribe. |
| Comped | Platform admins can set `comped` for beta customers and partners (`PUT /api/v1/platform/organizations/{id}/billing`). |

Platform administrators are never blocked. With `BILLING_ENABLED=false` (the default) none of
this applies, which keeps the public demo, CI and self-hosted installs unchanged.

## API

| Method | Path | Who |
|---|---|---|
| `GET` | `/api/v1/billing` | Any member — plan, status, trial days, access |
| `POST` | `/api/v1/billing/checkout` | Admin — returns a Stripe Checkout URL |
| `POST` | `/api/v1/billing/portal` | Admin — returns a Stripe customer-portal URL |
| `POST` | `/api/v1/billing/webhook` | Stripe only — HMAC-SHA256 signature verified, 5-minute replay window |
| `PUT` | `/api/v1/platform/organizations/{id}/billing` | Platform admin — comp a workspace or extend a trial |

## Stripe setup (test mode first)

1. In the Stripe dashboard (test mode) create a **Product** "GroundsOps Pro" with a monthly
   recurring **Price** in CAD. Copy the price ID (`price_...`).
2. **Developers → API keys**: copy the secret key (`sk_test_...`).
3. **Developers → Webhooks → Add endpoint**: `https://<your-domain>/api/v1/billing/webhook`
   with events `checkout.session.completed`, `customer.subscription.created`,
   `customer.subscription.updated`, `customer.subscription.deleted`. Copy the signing
   secret (`whsec_...`).
4. **Settings → Billing → Customer portal**: enable cancellation, payment-method updates
   and invoice history.
5. Optional: enable **Stripe Tax** and register for GST/PST, then set `STRIPE_AUTOMATIC_TAX=true`.
6. Put the values in `.env.staging` (never commit them):

   ```
   BILLING_ENABLED=true
   APP_PUBLIC_URL=https://<your-domain>
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_ID=price_...
   ```

7. Run `alembic upgrade head` (migration `0024_organization_billing`) and restart the API.
8. Test with card `4242 4242 4242 4242`, any future expiry and any CVC. Use `4000 0000 0000 0341`
   to simulate a failed renewal and check the `past_due` banner.

Going live is the same steps with live-mode keys and a live webhook endpoint.

## Existing workspaces

Workspaces created before billing was enabled start their trial from their creation date, so
older beta workspaces would be locked immediately. Comp them (or extend `trial_ends_at`)
before turning billing on:

```bash
curl -X PUT https://<your-domain>/api/v1/platform/organizations/<id>/billing \
  -H "Authorization: Bearer <platform-admin token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "comped"}'
```
