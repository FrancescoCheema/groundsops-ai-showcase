"use client";

import { AlertTriangle, CreditCard, ExternalLink, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { formatDateTime } from "@/features/shared/format";
import { request } from "@/lib/api";

export type BillingState = {
  enabled: boolean;
  plan_name: string;
  status: string;
  has_access: boolean;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  current_period_end: string | null;
  has_billing_account: boolean;
  can_manage: boolean;
  checkout_available: boolean;
};

const statusLabels: Record<string, string> = {
  trialing: "Free trial",
  active: "Active",
  past_due: "Payment issue",
  comped: "Complimentary",
  canceled: "Canceled",
  unpaid: "Unpaid",
  incomplete: "Awaiting payment",
  incomplete_expired: "Expired",
  paused: "Paused",
};

export function useBilling(token: string) {
  const [billing, setBilling] = useState<BillingState>();
  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      setBilling(await request<BillingState>("/api/v1/billing", token));
    } catch {
      setBilling(undefined);
    }
  }, [token]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return { billing, refresh };
}

async function redirectTo(path: string, token: string) {
  const { url } = await request<{ url: string }>(path, token, { method: "POST" });
  window.location.assign(url);
}

function BillingActions({ billing, token, compact = false }: { billing: BillingState; token: string; compact?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!billing.can_manage || !billing.checkout_available) return null;
  const subscribed = ["active", "past_due"].includes(billing.status);
  const run = async (path: string) => {
    setBusy(true);
    setError("");
    try {
      await redirectTo(path, token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Billing is unavailable right now.");
      setBusy(false);
    }
  };
  return (
    <div className="billing-actions">
      {!subscribed && (
        <button type="button" className={compact ? "primary compact" : "primary"} disabled={busy} onClick={() => void run("/api/v1/billing/checkout")}>
          <Sparkles /> {busy ? "Opening checkout…" : "Subscribe"}
        </button>
      )}
      {billing.has_billing_account && (
        <button type="button" className={compact ? "secondary compact" : "secondary"} disabled={busy} onClick={() => void run("/api/v1/billing/portal")}>
          <ExternalLink /> {subscribed ? "Manage billing" : "Billing history"}
        </button>
      )}
      {error && <small className="billing-error" role="alert">{error}</small>}
    </div>
  );
}

/** Workspace-wide banner for an ending trial, a failed payment or a locked workspace. */
export function BillingBanner({ billing, token }: { billing?: BillingState; token: string }) {
  if (!billing?.enabled || billing.status === "comped") return null;
  let tone: "info" | "warning" | "locked";
  let text: string;
  if (!billing.has_access) {
    tone = "locked";
    text = billing.status === "trialing"
      ? "Your free trial has ended. Your data is safe and viewable — subscribe to keep making changes."
      : "Your subscription is inactive. Your data is safe and viewable — subscribe to keep making changes.";
  } else if (billing.status === "past_due") {
    tone = "warning";
    text = "We couldn't process your last payment. Update your card to avoid interruption.";
  } else if (billing.status === "trialing" && billing.trial_days_remaining <= 7) {
    tone = "info";
    text = `${billing.trial_days_remaining} ${billing.trial_days_remaining === 1 ? "day" : "days"} left in your free trial.`;
  } else {
    return null;
  }
  return (
    <div className={`billing-banner ${tone}`} role={tone === "info" ? "status" : "alert"}>
      {tone === "info" ? <Sparkles /> : <AlertTriangle />}
      <span>
        {text}
        {!billing.can_manage && " Ask a workspace admin to update billing."}
      </span>
      <BillingActions billing={billing} token={token} compact />
    </div>
  );
}

/** Plan and payment details for the settings sheet. */
export function BillingSettings({ billing, token }: { billing?: BillingState; token: string }) {
  if (!billing?.enabled) return null;
  const detail = billing.status === "trialing"
    ? billing.has_access && billing.trial_ends_at
      ? `Trial ends ${formatDateTime(billing.trial_ends_at)} (${billing.trial_days_remaining} ${billing.trial_days_remaining === 1 ? "day" : "days"} left)`
      : "Trial ended"
    : billing.current_period_end
      ? `${billing.status === "canceled" ? "Ended" : "Renews"} ${formatDateTime(billing.current_period_end)}`
      : billing.status === "comped"
        ? "Provided at no cost by GroundsOps"
        : "";
  return (
    <div className="settings-section billing-settings">
      <h3>Plan and billing</h3>
      <div className="billing-plan">
        <span className="tool-icon"><CreditCard /></span>
        <div>
          <strong>{billing.plan_name}</strong>
          <small>{detail}</small>
        </div>
        <span className={`billing-status ${billing.status}`}>{statusLabels[billing.status] || billing.status}</span>
      </div>
      {billing.can_manage ? (
        billing.checkout_available ? (
          <>
            <p className="settings-note">Payments are processed securely by Stripe. GroundsOps never sees or stores card details. Subscribing during the trial keeps your remaining trial days.</p>
            <BillingActions billing={billing} token={token} />
          </>
        ) : (
          <p className="settings-note">Online checkout is not configured for this deployment.</p>
        )
      ) : (
        <p className="settings-note">Only workspace admins can change billing.</p>
      )}
    </div>
  );
}
