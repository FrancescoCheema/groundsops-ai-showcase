"use client";

import { Tags } from "lucide-react";
import { useEffect, useState } from "react";
import { request, type PriceList, type PriceListItem } from "@/lib/api";

export const materialLabels: Record<PriceListItem["material_type"], { name: string; unit: string; volume: boolean }> = {
  sod: { name: "Sod", unit: "sq ft", volume: false },
  pavers: { name: "Pavers", unit: "sq ft", volume: false },
  mulch: { name: "Mulch", unit: "cu yd", volume: true },
  gravel: { name: "Gravel", unit: "cu yd", volume: true },
  topsoil: { name: "Topsoil", unit: "cu yd", volume: true },
};

/** Company price list in Settings: one row per material plus labour, delivery and tax defaults. */
/** Show stored decimals without padding ("10.00" -> "10", "0.850" -> "0.85"). */
function tidy(list: PriceList): PriceList {
  const n = (value?: string | null) => (value === null || value === undefined || value === "" ? value ?? null : String(Number(value)));
  return {
    ...list,
    labour_rate: n(list.labour_rate) ?? "0",
    delivery_cost: n(list.delivery_cost) ?? "0",
    tax_rate: n(list.tax_rate) ?? "0",
    items: list.items.map((item) => ({ ...item, unit_price: n(item.unit_price) ?? "0", waste_percent: n(item.waste_percent) ?? "0", depth: n(item.depth) })),
  };
}

export function PriceListSettings({ token, canEdit }: { token: string; canEdit: boolean }) {
  const [list, setList] = useState<PriceList>();
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    request<PriceList>("/api/v1/price-list", token).then((data) => setList(tidy(data))).catch(() => setStatus("Price list could not be loaded."));
  }, [token]);

  if (!list) return null;
  const setItem = (index: number, patch: Partial<PriceListItem>) =>
    setList({ ...list, items: list.items.map((item, i) => (i === index ? { ...item, ...patch } : item)) });

  async function save() {
    if (!list) return;
    setSaving(true);
    setStatus("");
    try {
      setList(tidy(await request<PriceList>("/api/v1/price-list", token, { method: "PUT", body: JSON.stringify(list) })));
      setStatus("Price list saved. New estimates will use these prices.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Price list could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="settings-section price-list-settings">
      <h3><Tags aria-hidden="true" /> Price list</h3>
      <p className="settings-note">Your own costs. Estimates fill these in automatically, and you can still change them per job.</p>
      <div className="price-list-table" role="table" aria-label="Material prices">
        <div className="price-list-row head" role="row">
          <span role="columnheader">Material</span>
          <span role="columnheader">Your cost</span>
          <span role="columnheader">Waste %</span>
          <span role="columnheader">Depth (in)</span>
          <span role="columnheader">Supplier</span>
        </div>
        {list.items.map((item, index) => {
          const meta = materialLabels[item.material_type];
          return (
            <div className="price-list-row" role="row" key={item.material_type}>
              <strong role="cell">{meta.name}</strong>
              <label role="cell" className="with-unit">
                <span className="sr-only">{meta.name} cost per {meta.unit}</span>
                <span aria-hidden="true">$</span>
                <input type="number" min="0" step="0.01" disabled={!canEdit} value={item.unit_price} onChange={(event) => setItem(index, { unit_price: event.target.value })} />
                <small>/{meta.unit}</small>
              </label>
              <label role="cell">
                <span className="sr-only">{meta.name} waste percent</span>
                <input type="number" min="0" max="50" step="0.5" disabled={!canEdit} value={item.waste_percent} onChange={(event) => setItem(index, { waste_percent: event.target.value })} />
              </label>
              <label role="cell">
                <span className="sr-only">{meta.name} depth in inches</span>
                {meta.volume ? (
                  <input type="number" min="0.1" max="36" step="0.5" disabled={!canEdit} value={item.depth || ""} onChange={(event) => setItem(index, { depth: event.target.value || null })} />
                ) : <span className="muted">—</span>}
              </label>
              <label role="cell">
                <span className="sr-only">{meta.name} supplier</span>
                <input maxLength={200} disabled={!canEdit} value={item.supplier || ""} placeholder="Optional" onChange={(event) => setItem(index, { supplier: event.target.value })} />
              </label>
            </div>
          );
        })}
      </div>
      <div className="price-list-defaults">
        <label>Labour rate ($/hour)<input type="number" min="0" step="0.5" disabled={!canEdit} value={list.labour_rate} onChange={(event) => setList({ ...list, labour_rate: event.target.value })} /></label>
        <label>Delivery ($/job)<input type="number" min="0" step="1" disabled={!canEdit} value={list.delivery_cost} onChange={(event) => setList({ ...list, delivery_cost: event.target.value })} /></label>
        <label>Tax (%)<input type="number" min="0" max="100" step="0.5" disabled={!canEdit} value={list.tax_rate} onChange={(event) => setList({ ...list, tax_rate: event.target.value })} /></label>
      </div>
      {canEdit && <button type="button" className="primary compact" disabled={saving} onClick={() => void save()}>{saving ? "Saving…" : "Save price list"}</button>}
      {status && <p className="settings-status" role="status">{status}</p>}
    </div>
  );
}
