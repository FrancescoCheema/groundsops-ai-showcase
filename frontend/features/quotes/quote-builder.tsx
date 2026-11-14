"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CalendarCheck, Check, Download, FileText, Plus, Send, Trash2 } from "lucide-react";

import { GenerationMaterialEstimate, OrganizationUser, Quote, QuoteItem, WorkOrder, downloadAuthenticated, request } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/features/shared/format";

const blankItem = (): QuoteItem => ({
  description: "",
  category: "other",
  quantity: "1",
  unit: "unit",
  unit_price: "0",
});

export function QuoteBuilder({
  designId,
  jobId,
  token,
  onMessage,
}: {
  designId: string;
  jobId: string;
  token: string;
  onMessage: (message: string) => void;
}) {
  const [estimate, setEstimate] = useState<GenerationMaterialEstimate>();
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [users, setUsers] = useState<OrganizationUser[]>([]);
  const [title, setTitle] = useState("Landscape installation quote");
  const [items, setItems] = useState<QuoteItem[]>([blankItem()]);
  const [markup, setMarkup] = useState("10");
  const [discount, setDiscount] = useState("0");
  const [tax, setTax] = useState("5");
  const [assumptions, setAssumptions] = useState("Measurements are estimates and must be verified on site before ordering.");
  const [saving, setSaving] = useState(false);
  const [busyQuote, setBusyQuote] = useState("");
  const [scheduleQuote, setScheduleQuote] = useState("");
  const [scheduledStart, setScheduledStart] = useState("");
  const [scheduledEnd, setScheduledEnd] = useState("");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [priority, setPriority] = useState<WorkOrder["priority"]>("normal");
  const [customerInstructions, setCustomerInstructions] = useState("");

  useEffect(() => {
    void request<Quote[]>("/api/v1/quotes", token)
      .then((records) => setQuotes(records.filter((record) => record.generation_job_id === jobId)))
      .catch(() => undefined);
    void request<WorkOrder[]>("/api/v1/work-orders", token)
      .then(setWorkOrders)
      .catch(() => undefined);
    void request<OrganizationUser[]>("/api/v1/users", token)
      .then((records) => setUsers(records.filter((record) => record.active)))
      .catch(() => undefined);
    void request<GenerationMaterialEstimate>(`/api/v1/generations/${jobId}/material-estimate`, token)
      .then((record) => {
        setEstimate(record);
        setItems([
          { description: `${record.material_type.charAt(0).toUpperCase()}${record.material_type.slice(1)} materials`, category: "material", quantity: record.order_quantity, unit: record.material_unit, unit_price: record.unit_price },
          { description: "Installation labour", category: "labour", quantity: record.labour_hours, unit: "hour", unit_price: record.labour_rate },
          ...(Number(record.delivery_cost) > 0 ? [{ description: "Delivery", category: "delivery" as const, quantity: "1", unit: "delivery", unit_price: record.delivery_cost }] : []),
        ]);
        setTax(record.tax_rate);
      })
      .catch(() => undefined);
  }, [jobId, token]);

  const preview = useMemo(() => {
    const subtotal = items.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.unit_price || 0), 0);
    const markupAmount = subtotal * Number(markup || 0) / 100;
    const taxable = Math.max(0, subtotal + markupAmount - Number(discount || 0));
    return { subtotal, total: taxable * (1 + Number(tax || 0) / 100) };
  }, [discount, items, markup, tax]);

  function updateItem(index: number, field: keyof QuoteItem, value: string) {
    setItems((current) => current.map((item, position) => position === index ? { ...item, [field]: value } : item));
  }

  async function changeStatus(record: Quote, status: "sent" | "approved") {
    setBusyQuote(record.id);
    try {
      const updated = await request<Quote>(`/api/v1/quotes/${record.id}/status`, token, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setQuotes((current) => current.map((item) => item.id === updated.id ? updated : item));
      onMessage(status === "sent" ? `${record.number} marked as sent.` : `${record.number} approved and ready to schedule.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Quote status could not be updated.");
    } finally {
      setBusyQuote("");
    }
  }

  async function scheduleWork(record: Quote, event: FormEvent) {
    event.preventDefault();
    if (!scheduledStart || !scheduledEnd) {
      onMessage("Choose a start and end time.");
      return;
    }
    setBusyQuote(record.id);
    try {
      const created = await request<WorkOrder>(`/api/v1/quotes/${record.id}/work-order`, token, {
        method: "POST",
        body: JSON.stringify({
          assigned_user_id: assignedUserId || null,
          scheduled_start: new Date(scheduledStart).toISOString(),
          scheduled_end: new Date(scheduledEnd).toISOString(),
          priority,
          customer_instructions: customerInstructions || null,
        }),
      });
      setWorkOrders((current) => [created, ...current]);
      setScheduleQuote("");
      setCustomerInstructions("");
      onMessage(`${record.number} converted to a scheduled job.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "The job could not be scheduled.");
    } finally {
      setBusyQuote("");
    }
  }

  async function downloadPdf(record: Quote) {
    setBusyQuote(record.id);
    try {
      const blob = await downloadAuthenticated(`/api/v1/quotes/${record.id}/pdf`, token);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${record.number}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "The quote PDF could not be created.");
    } finally {
      setBusyQuote("");
    }
  }

  async function saveQuote() {
    return request<Quote>("/api/v1/quotes", token, {
      method: "POST",
      body: JSON.stringify({
        design_project_id: designId,
        generation_job_id: jobId,
        title,
        items,
        markup_rate: markup,
        discount_amount: discount,
        tax_rate: tax,
        currency: "CAD",
        assumptions,
      }),
    });
  }

  /** One click: save the quote exactly as prefilled from the estimate and download its PDF. */
  async function createPdfQuote() {
    setSaving(true);
    try {
      const created = await saveQuote();
      setQuotes((current) => [created, ...current]);
      await downloadPdf(created);
      onMessage(`${created.number} created. The PDF is downloading, ready to send to the customer.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Quote could not be created.");
    } finally {
      setSaving(false);
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await saveQuote();
      setQuotes((current) => [created, ...current]);
      onMessage(`${created.number} saved as a draft.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Quote could not be created.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="quote-builder-wrap">
  <div className="quote-one-click">
    <div><strong>Quote PDF for the customer</strong><span>{estimate ? `From the saved ${estimate.material_type} estimate, with your logo, the before and after photos, ${Number(markup)}% markup built into the prices and ${Number(tax)}% tax.` : "Save an estimate above first, or build the quote by hand below."}</span></div>
    <button type="button" className="primary compact" disabled={saving || !estimate} onClick={() => void createPdfQuote()}><Download />{saving ? "Creating…" : "Create quote PDF"}</button>
  </div>
  <details className="quote-builder">
    <summary><FileText />Edit lines before quoting</summary>
    <form onSubmit={create}>
      <label>Quote title<input value={title} minLength={2} maxLength={200} onChange={(event) => setTitle(event.target.value)} /></label>
      <div className="quote-lines">
        {items.map((item, index) => <div className="quote-line" key={index}>
          <input aria-label="Description" placeholder="Line item" value={item.description} required onChange={(event) => updateItem(index, "description", event.target.value)} />
          <select aria-label="Category" value={item.category} onChange={(event) => updateItem(index, "category", event.target.value)}><option value="material">Material</option><option value="labour">Labour</option><option value="equipment">Equipment</option><option value="delivery">Delivery</option><option value="other">Other</option></select>
          <input aria-label="Quantity" type="number" min="0.01" step="0.01" value={item.quantity} required onChange={(event) => updateItem(index, "quantity", event.target.value)} />
          <input aria-label="Unit" value={item.unit} required onChange={(event) => updateItem(index, "unit", event.target.value)} />
          <input aria-label="Unit price" type="number" min="0" step="0.01" value={item.unit_price} required onChange={(event) => updateItem(index, "unit_price", event.target.value)} />
          <button type="button" aria-label="Remove line" disabled={items.length === 1} onClick={() => setItems((current) => current.filter((_, position) => position !== index))}><Trash2 /></button>
        </div>)}
      </div>
      <button type="button" className="secondary" onClick={() => setItems((current) => [...current, blankItem()])}><Plus />Add line</button>
      <div className="quote-rates"><label>Markup %<input type="number" min="0" max="100" step="0.01" value={markup} onChange={(event) => setMarkup(event.target.value)} /></label><label>Discount $<input type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} /></label><label>Tax %<input type="number" min="0" max="100" step="0.01" value={tax} onChange={(event) => setTax(event.target.value)} /></label></div>
      <label>Assumptions<textarea value={assumptions} maxLength={5000} onChange={(event) => setAssumptions(event.target.value)} /></label>
      <div className="quote-preview"><span>Subtotal {formatMoney(preview.subtotal)}</span><strong>Estimated total {formatMoney(preview.total, "CAD")}</strong><small>The server recalculates and validates the final total.</small></div>
      <button className="primary compact" disabled={saving}>{saving ? "Saving…" : "Save draft quote"}</button>
      {estimate && <small>Prefilled from the saved {estimate.material_type} estimate.</small>}
    </form>
  </details>
    {quotes.length > 0 && <div className="quote-history"><strong>Quote history</strong>{quotes.map((record) => {
      const workOrder = workOrders.find((item) => item.quote_id === record.id);
      return <article className="quote-record" key={record.id}>
        <div className="quote-record-head"><span><strong>{record.number}</strong><small>{record.status}</small></span><b>{formatMoney(record.total, record.currency)}</b></div>
        <div className="quote-record-actions">
          <button type="button" className="secondary compact" disabled={busyQuote === record.id} onClick={() => void downloadPdf(record)}><Download />PDF</button>
          {record.status === "draft" && <button type="button" className="secondary compact" disabled={busyQuote === record.id} onClick={() => void changeStatus(record, "sent")}><Send />Mark sent</button>}
          {record.status === "sent" && <button type="button" className="secondary compact" disabled={busyQuote === record.id} onClick={() => void changeStatus(record, "approved")}><Check />Approve quote</button>}
          {record.status === "approved" && !workOrder && <button type="button" className="primary compact" onClick={() => setScheduleQuote((current) => current === record.id ? "" : record.id)}><CalendarCheck />Schedule job</button>}
          {workOrder && <span className="quote-job-linked"><CalendarCheck />Scheduled {workOrder.scheduled_start ? formatDateTime(workOrder.scheduled_start) : "job"}</span>}
        </div>
        {scheduleQuote === record.id && !workOrder && <form className="quote-schedule" onSubmit={(event) => void scheduleWork(record, event)}>
          <label>Start<input type="datetime-local" required value={scheduledStart} onChange={(event) => setScheduledStart(event.target.value)} /></label>
          <label>End<input type="datetime-local" required value={scheduledEnd} onChange={(event) => setScheduledEnd(event.target.value)} /></label>
          <label>Assign crew<select value={assignedUserId} onChange={(event) => setAssignedUserId(event.target.value)}><option value="">Unassigned</option>{users.map((user) => <option key={user.id} value={user.id}>{user.display_name} · {user.role}</option>)}</select></label>
          <label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value as WorkOrder["priority"])}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
          <label className="quote-schedule-notes">Customer and crew instructions<textarea maxLength={5000} value={customerInstructions} onChange={(event) => setCustomerInstructions(event.target.value)} placeholder="Access notes, protection requirements or customer preferences" /></label>
          <button className="primary compact" disabled={busyQuote === record.id}><CalendarCheck />{busyQuote === record.id ? "Scheduling..." : "Create scheduled job"}</button>
        </form>}
      </article>;
    })}</div>}
  </div>;
}
