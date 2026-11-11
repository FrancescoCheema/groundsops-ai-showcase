"use client";

import { useState } from "react";
import { Check, Plus, Trash2, X } from "lucide-react";
import { WorkOrder, request } from "@/lib/api";
import { formatMoney } from "@/features/shared/format";

type MaterialRow = { description: string; quantity: string; unit: string; unit_price: string };

export function JobCompletion({
  job,
  token,
  close,
  completed,
}: {
  job: WorkOrder;
  token: string;
  close: () => void;
  completed: () => Promise<void>;
}) {
  const [hours, setHours] = useState("");
  const [rate, setRate] = useState("");
  const [notes, setNotes] = useState("");
  const [createInvoice, setCreateInvoice] = useState(true);
  const [materials, setMaterials] = useState<MaterialRow[]>([
    { description: "", quantity: "", unit: "unit", unit_price: "" },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const actualTotal =
    (Number(hours) || 0) * (Number(rate) || 0) +
    materials.reduce(
      (sum, row) => sum + (Number(row.quantity) || 0) * (Number(row.unit_price) || 0),
      0,
    );

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await request(`/api/v1/work-orders/${job.id}/complete`, token, {
        method: "POST",
        body: JSON.stringify({
          labour_hours: hours || "0",
          labour_rate: rate || "0",
          materials: materials.filter((row) => row.description.trim()).map((row) => ({
            ...row,
            quantity: row.quantity || "0",
            unit_price: row.unit_price || "0",
          })),
          notes: notes || null,
        }),
      });
      if (createInvoice) {
        await request(`/api/v1/work-orders/${job.id}/invoice`, token, { method: "POST" });
      }
      await completed();
      close();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The job could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="modal-backdrop" onClick={close}>
    <section className="composer job-completion" onClick={(event) => event.stopPropagation()}>
      <header><div><p className="eyebrow dark">Complete job</p><h2>{job.title}</h2></div><button className="icon-button" onClick={close}><X /></button></header>
      <div className="completion-grid"><label>Actual labour hours<input type="number" min="0" step="0.25" value={hours} onChange={(event) => setHours(event.target.value)} /></label><label>Hourly rate<input type="number" min="0" step="0.01" value={rate} onChange={(event) => setRate(event.target.value)} /></label></div>
      <div className="completion-materials"><div className="section-heading"><div><strong>Actual materials</strong><small>Record what was used, not what was originally estimated.</small></div><button className="secondary compact" onClick={() => setMaterials((rows) => [...rows, { description: "", quantity: "", unit: "unit", unit_price: "" }])}><Plus />Add material</button></div>{materials.map((row, index) => <div className="completion-material-row" key={index}><input placeholder="Material" value={row.description} onChange={(event) => setMaterials((rows) => rows.map((item, position) => position === index ? { ...item, description: event.target.value } : item))} /><input type="number" min="0" placeholder="Qty" value={row.quantity} onChange={(event) => setMaterials((rows) => rows.map((item, position) => position === index ? { ...item, quantity: event.target.value } : item))} /><input placeholder="Unit" value={row.unit} onChange={(event) => setMaterials((rows) => rows.map((item, position) => position === index ? { ...item, unit: event.target.value } : item))} /><input type="number" min="0" placeholder="Unit price" value={row.unit_price} onChange={(event) => setMaterials((rows) => rows.map((item, position) => position === index ? { ...item, unit_price: event.target.value } : item))} /><button className="mini-icon-button" onClick={() => setMaterials((rows) => rows.filter((_, position) => position !== index))}><Trash2 /></button></div>)}</div>
      <label>Completion notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <label className="toggle-row"><input type="checkbox" checked={createInvoice} onChange={(event) => setCreateInvoice(event.target.checked)} /><span>Create a draft invoice from actual costs</span></label>
      <div className="completion-total"><span>Actual job cost</span><strong>{formatMoney(actualTotal)}</strong>{job.quoted_total && <small>Quoted {formatMoney(job.quoted_total)} · variance {formatMoney(actualTotal - Number(job.quoted_total))}</small>}</div>
      {error && <p className="form-error">{error}</p>}
      <button className="primary" disabled={busy || actualTotal <= 0} onClick={() => void submit()}><Check />{busy ? "Completing…" : "Complete job"}</button>
    </section>
  </div>;
}
