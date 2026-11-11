"use client";

import { FormEvent, useState } from "react";

import type { Invoice } from "@/lib/api";
import { request } from "@/lib/api";
import { formatMoney } from "@/features/shared/format";

export function InvoicePayments({ invoice, token, refresh }: {
  invoice: Invoice;
  token: string;
  refresh: () => Promise<void>;
}) {
  const balance = Number(invoice.balance_due || invoice.total);
  const [amount, setAmount] = useState(balance.toFixed(2));
  const [method, setMethod] = useState("etransfer");
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await request(`/api/v1/invoices/${invoice.id}/payments`, token, {
        method: "POST",
        body: JSON.stringify({ amount, method, reference: reference.trim() || null }),
      });
      setMessage("Payment recorded.");
      setReference("");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Payment could not be recorded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="invoice-payment-panel">
      <summary>
        <span>Payments</span>
        <strong>{formatMoney(invoice.paid_amount)} paid · {formatMoney(balance)} due</strong>
      </summary>
      <div className="invoice-payment-body">
        {invoice.payments?.length ? (
          <div className="payment-history">
            {invoice.payments.map((payment) => (
              <div key={payment.id}>
                <strong>{formatMoney(payment.amount)}</strong>
                <span>{payment.method}{payment.reference ? ` · ${payment.reference}` : ""}</span>
                <time>{new Date(payment.received_at).toLocaleDateString()}</time>
              </div>
            ))}
          </div>
        ) : <p className="settings-note">No payments recorded.</p>}
        {balance > 0 && invoice.status !== "void" && (
          <form onSubmit={submit} className="payment-form">
            <label>Amount<input type="number" min="0.01" max={balance} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required /></label>
            <label>Method<select value={method} onChange={(event) => setMethod(event.target.value)}><option value="etransfer">E-transfer</option><option value="card">Card</option><option value="cash">Cash</option><option value="cheque">Cheque</option><option value="bank">Bank transfer</option><option value="other">Other</option></select></label>
            <label>Reference<input value={reference} onChange={(event) => setReference(event.target.value)} maxLength={200} placeholder="Optional" /></label>
            <button type="submit" className="primary compact" disabled={busy}>{busy ? "Recording…" : "Record payment"}</button>
          </form>
        )}
        {message && <p className="settings-note" role="status">{message}</p>}
      </div>
    </details>
  );
}
