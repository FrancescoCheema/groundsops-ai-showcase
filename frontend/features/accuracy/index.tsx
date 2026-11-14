"use client";

import { CheckCircle2, Ruler, Target } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { type GenerationJob, type MeasurementAccuracyReport, type SiteMeasurement, request } from "@/lib/api";

export function errorText(percent: number) {
  const size = Math.abs(percent).toFixed(1);
  if (Math.abs(percent) < 0.05) return "matched the tape";
  return `${size}% ${percent > 0 ? "high" : "low"}`;
}

function errorClass(percent: number) {
  const size = Math.abs(percent);
  return size <= 5 ? "good" : size <= 10 ? "fair" : "poor";
}

/** Record the tape-measured area for a concept and show how far the app was off. */
export function TapeCheck({ job, token, onMessage }: { job: GenerationJob; token: string; onMessage?: (message: string) => void }) {
  const unit = job.calibration_unit || "ft";
  const initial: SiteMeasurement | null = job.site_measured_area && job.estimated_area ? {
    job_id: job.id,
    unit,
    estimated_area: job.estimated_area,
    site_area: job.site_measured_area,
    area_error_percent: ((Number(job.estimated_area) - Number(job.site_measured_area)) / Number(job.site_measured_area)) * 100,
    measured_at: job.site_measured_at || "",
    notes: job.site_measurement_notes,
  } : null;
  const [result, setResult] = useState<SiteMeasurement | null>(initial);
  const [editing, setEditing] = useState(false);
  const [area, setArea] = useState("");
  const [perimeter, setPerimeter] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const saved = await request<SiteMeasurement>(`/api/v1/generations/${job.id}/site-measurement`, token, {
        method: "PUT",
        body: JSON.stringify({ area, perimeter: perimeter || null, notes: notes || null }),
      });
      setResult(saved);
      setEditing(false);
      onMessage?.(`Tape check saved: the app was ${errorText(saved.area_error_percent)}.`);
    } catch (error) {
      onMessage?.(error instanceof Error ? error.message : "The tape measurement could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  if (result && !editing) {
    return <div className={`tape-check result ${errorClass(result.area_error_percent)}`}>
      <CheckCircle2 />
      <div>
        <strong>Tape on site: {Number(result.site_area).toLocaleString()} sq {unit}</strong>
        <span>The app measured {Number(result.estimated_area).toLocaleString(undefined, { maximumFractionDigits: 1 })} sq {unit}, {errorText(result.area_error_percent)}.{result.notes ? ` ${result.notes}` : ""}</span>
      </div>
      <button type="button" className="secondary compact" onClick={() => { setArea(String(Number(result.site_area))); setEditing(true); }}>Edit</button>
    </div>;
  }

  return <form className="tape-check" onSubmit={(event) => void save(event)}>
    <div className="tape-check-intro"><Ruler /><div><strong>Tape check</strong><span>Measured this area with a tape on site? Enter it to see how accurate the photo measurement was.</span></div></div>
    <label>Tape area (sq {unit})<input type="number" min="0.01" step="0.01" required value={area} onChange={(event) => setArea(event.target.value)} /></label>
    <label>Tape edge ({unit}, optional)<input type="number" min="0.01" step="0.01" value={perimeter} onChange={(event) => setPerimeter(event.target.value)} /></label>
    <label className="tape-notes">Notes (optional)<input maxLength={500} value={notes} placeholder="e.g. split into 2 rectangles + 1 triangle" onChange={(event) => setNotes(event.target.value)} /></label>
    <div className="tape-actions">
      {editing && <button type="button" className="secondary compact" onClick={() => setEditing(false)}>Cancel</button>}
      <button className="primary compact" disabled={busy}>{busy ? "Saving…" : "Save tape check"}</button>
    </div>
  </form>;
}

/** Company-wide accuracy of photo measurements against tape measurements. */
export function MeasurementAccuracy({ token, onOpenDesign }: { token: string; onOpenDesign: (id: string) => void }) {
  const [report, setReport] = useState<MeasurementAccuracyReport>();
  useEffect(() => {
    request<MeasurementAccuracyReport>("/api/v1/measurement-accuracy", token).then(setReport).catch(() => undefined);
  }, [token]);
  if (!report) return null;
  const { summary, checks } = report;
  return <section className="accuracy-card">
    <div className="section-heading"><div><p className="eyebrow dark">Field accuracy</p><h3>Photo measurement vs. tape measure</h3></div><Target /></div>
    {summary.count === 0 ? <p className="accuracy-empty">No tape checks yet. On your next job: lay a sheet of letter paper flat on the ground, take the photo and measure with Known object, then tape-measure the same area and enter it under Tape check on the concept. Five to ten checks give you a reliable accuracy figure.</p> : <>
      <div className="accuracy-stats">
        <div><span>Tape checks</span><strong>{summary.count}</strong></div>
        <div><span>Typical error</span><strong>{summary.median_abs_error_percent?.toFixed(1)}%</strong><small>median, either direction</small></div>
        <div><span>Within 5%</span><strong>{summary.within_5_percent} of {summary.count}</strong></div>
        <div><span>Within 10%</span><strong>{summary.within_10_percent} of {summary.count}</strong></div>
      </div>
      {summary.by_method.length > 1 && <div className="accuracy-methods">{summary.by_method.map((item) => <span key={item.method}><b>{item.method}</b> typical error {item.median_abs_error_percent.toFixed(1)}% · {item.within_5_percent} of {item.count} within 5%</span>)}</div>}
      <table className="accuracy-table">
        <thead><tr><th scope="col">Design</th><th scope="col">Method</th><th scope="col">App</th><th scope="col">Tape</th><th scope="col">Difference</th></tr></thead>
        <tbody>{checks.map((check) => <tr key={check.job_id}>
          <th scope="row"><button type="button" onClick={() => onOpenDesign(check.design_project_id)}>{check.design_name}</button><small>{new Date(check.measured_at).toLocaleDateString()}</small></th>
          <td>{check.method}{check.reference ? <small>{check.reference}</small> : null}</td>
          <td>{Number(check.estimated_area).toLocaleString(undefined, { maximumFractionDigits: 0 })} sq {check.unit}</td>
          <td>{Number(check.site_area).toLocaleString(undefined, { maximumFractionDigits: 0 })} sq {check.unit}</td>
          <td><span className={`accuracy-pill ${errorClass(check.area_error_percent)}`}>{check.area_error_percent > 0 ? "+" : ""}{check.area_error_percent.toFixed(1)}%</span></td>
        </tr>)}</tbody>
      </table>
    </>}
  </section>;
}
