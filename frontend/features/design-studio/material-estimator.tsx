"use client";

import { FormEvent, useEffect, useState } from "react";
import { Calculator, ExternalLink, MapPin, PackageCheck } from "lucide-react";
import { ApiError, GenerationMaterialEstimate, request } from "@/lib/api";

type Material = GenerationMaterialEstimate["material_type"];
type MeasurementUnit = GenerationMaterialEstimate["measurement_unit"];

const defaults: Record<Material, { waste: string; depth: string }> = {
  sod: { waste: "8", depth: "" },
  pavers: { waste: "10", depth: "" },
  mulch: { waste: "10", depth: "3" },
  gravel: { waste: "10", depth: "3" },
  topsoil: { waste: "10", depth: "4" },
};

function materialFromPrompt(prompt: string): Material {
  const value = prompt.toLowerCase();
  if (/paver|patio|brick|flagstone|hardscape/.test(value)) return "pavers";
  if (/mulch|bark|wood chip/.test(value)) return "mulch";
  if (/gravel|river rock|pea gravel|crushed rock/.test(value)) return "gravel";
  if (/topsoil|soil|garden bed/.test(value)) return "topsoil";
  return "sod";
}

function mapsSearch(query: string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function toHundredths(value?: string | null) {
  const number = Number(value);
  return value && Number.isFinite(number) ? number.toFixed(2) : "";
}

export function MaterialEstimator({
  jobId,
  token,
  prompt,
  propertyLocation,
  estimatedArea,
  estimatedPerimeter,
  measurementUnit,
  onMessage,
}: {
  jobId: string;
  token: string;
  prompt: string;
  propertyLocation: string;
  estimatedArea?: string | null;
  estimatedPerimeter?: string | null;
  measurementUnit?: "ft" | "m" | null;
  onMessage: (message: string) => void;
}) {
  const suggestedMaterial = materialFromPrompt(prompt);
  const [material, setMaterial] = useState<Material>(suggestedMaterial);
  const [waste, setWaste] = useState(defaults[suggestedMaterial].waste);
  const [depth, setDepth] = useState(defaults[suggestedMaterial].depth);
  const [unit, setUnit] = useState<MeasurementUnit>(measurementUnit || "ft");
  // Calibrated measurements arrive with 4 decimals; the inputs use step 0.01, so an
  // unrounded value would fail browser validation and silently block submission.
  const [area, setArea] = useState(toHundredths(estimatedArea));
  const [perimeter, setPerimeter] = useState(toHundredths(estimatedPerimeter));
  const [unitPrice, setUnitPrice] = useState("0");
  const [labourRate, setLabourRate] = useState("0");
  const [labourHours, setLabourHours] = useState("");
  const [delivery, setDelivery] = useState("0");
  const [taxRate, setTaxRate] = useState("12");
  const [estimate, setEstimate] = useState<GenerationMaterialEstimate>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    request<GenerationMaterialEstimate>(`/api/v1/generations/${jobId}/material-estimate`, token)
      .then((row) => {
        if (!active) return;
        setEstimate(row);
        setMaterial(row.material_type);
        setUnit(row.measurement_unit);
        setArea(row.measured_area);
        setPerimeter(row.measured_perimeter);
        setWaste(row.waste_percent);
        setDepth(row.depth || "");
        setUnitPrice(row.unit_price);
        setLabourRate(row.labour_rate);
        setLabourHours(row.labour_hours);
        setDelivery(row.delivery_cost);
        setTaxRate(row.tax_rate);
      })
      .catch((error) => {
        if (active && error instanceof Error && !(error instanceof ApiError && error.status === 404))
          onMessage(error.message);
      });
    return () => { active = false; };
  }, [jobId, onMessage, token]);

  function changeMaterial(value: Material) {
    setMaterial(value);
    setWaste(defaults[value].waste);
    setDepth(defaults[value].depth);
    setLabourHours("");
  }

  async function calculate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const row = await request<GenerationMaterialEstimate>(
        `/api/v1/generations/${jobId}/material-estimate`,
        token,
        {
          method: "PUT",
          body: JSON.stringify({
            material_type: material,
            measurement_unit: unit,
            measured_area: Number(area),
            measured_perimeter: Number(perimeter),
            waste_percent: Number(waste),
            depth: depth ? Number(depth) : null,
            unit_price: Number(unitPrice),
            labour_rate: Number(labourRate),
            labour_hours: labourHours ? Number(labourHours) : null,
            delivery_cost: Number(delivery),
            tax_rate: Number(taxRate),
          }),
        },
      );
      setEstimate(row);
      setLabourHours(row.labour_hours);
      onMessage("Material and labour estimate saved.");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Estimate could not be calculated.");
    } finally {
      setSaving(false);
    }
  }

  const volumeMaterial = material === "mulch" || material === "gravel" || material === "topsoil";
  const location = propertyLocation.trim() || "near me";
  const materialLabel = material === "topsoil" ? "topsoil" : material;

  return <details className="material-estimator">
    <summary><Calculator /> Material, labour and suppliers</summary>
    <form onSubmit={calculate}>
      <label>Material<select value={material} onChange={(event) => changeMaterial(event.target.value as Material)}>
        <option value="sod">Sod</option><option value="pavers">Pavers</option><option value="mulch">Mulch</option><option value="gravel">Gravel</option><option value="topsoil">Topsoil</option>
      </select></label>
      <label>Measurement unit<select value={unit} onChange={(event) => setUnit(event.target.value as MeasurementUnit)}><option value="ft">feet</option><option value="m">metres</option></select></label>
      <label>Area (sq {unit})<input type="number" min="0.01" step="0.01" value={area} onChange={(event) => setArea(event.target.value)} required /></label>
      <label>Perimeter ({unit})<input type="number" min="0.01" step="0.01" value={perimeter} onChange={(event) => setPerimeter(event.target.value)} required /></label>
      <label>Waste %<input type="number" min="0" max="50" step="0.5" value={waste} onChange={(event) => setWaste(event.target.value)} required /></label>
      {volumeMaterial && <label>Depth ({unit === "m" ? "cm" : "inches"})<input type="number" min="0.1" max="36" step="0.1" value={depth} onChange={(event) => setDepth(event.target.value)} required /></label>}
      <label>Material price / order unit<input type="number" min="0" step="0.01" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} /></label>
      <label>Labour rate / hour<input type="number" min="0" step="0.01" value={labourRate} onChange={(event) => setLabourRate(event.target.value)} /></label>
      <label>Labour hours<input type="number" min="0.01" step="0.01" value={labourHours} onChange={(event) => setLabourHours(event.target.value)} placeholder="Automatically calculated" /></label>
      <label>Delivery<input type="number" min="0" step="0.01" value={delivery} onChange={(event) => setDelivery(event.target.value)} /></label>
      <label>Tax %<input type="number" min="0" max="100" step="0.001" value={taxRate} onChange={(event) => setTaxRate(event.target.value)} /></label>
      <button className="primary compact" disabled={saving}><Calculator />{saving ? "Calculating..." : "Calculate and save"}</button>
    </form>
    <div className="supplier-links">
      <div><MapPin /><span><strong>Nearby suppliers</strong><small>{propertyLocation || "Uses your current map location"}</small></span></div>
      <a href={mapsSearch(`${materialLabel} supplier ${location}`)} target="_blank" rel="noreferrer">Find {materialLabel} suppliers <ExternalLink /></a>
      <a href={mapsSearch(`landscape supply ${location}`)} target="_blank" rel="noreferrer">Find landscape supply stores <ExternalLink /></a>
    </div>
    {estimate && <div className="estimate-result">
      <div><span>Measured area</span><strong>{Number(estimate.measured_area).toFixed(1)} sq {estimate.measurement_unit}</strong></div>
      <div><span>Order</span><strong>{estimate.order_quantity} {estimate.material_unit}</strong></div>
      <div><span>Edging</span><strong>{estimate.edging_quantity} {estimate.measurement_unit}</strong></div>
      <div><span>Labour</span><strong>{estimate.labour_hours} hours</strong></div>
      <div><span>Material</span><strong>${estimate.material_cost}</strong></div>
      <div><span>Labour</span><strong>${estimate.labour_cost}</strong></div>
      <div className="estimate-total"><span>Estimated total</span><strong>${estimate.total} {estimate.currency}</strong></div>
      <ul>{estimate.assumptions.map((item) => <li key={item}><PackageCheck />{item}</li>)}</ul>
      <small>Planning estimate only. Verify dimensions, supplier coverage, site conditions, availability and taxes before quoting or ordering.</small>
    </div>}
  </details>;
}
