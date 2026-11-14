"use client";

import { FormEvent, useEffect, useState } from "react";
import { Calculator, ExternalLink, MapPin, PackageCheck, Tags } from "lucide-react";
import { materialLabels } from "@/features/price-list";
import { formatMoney } from "@/features/shared/format";
import { ApiError, GenerationMaterialEstimate, type PriceList, request } from "@/lib/api";

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
  const [priceList, setPriceList] = useState<PriceList>();
  const [savedEstimateLoaded, setSavedEstimateLoaded] = useState(false);

  // Fill a new estimate from the company's price list; a saved estimate keeps its own numbers.
  function applyPriceList(list: PriceList, value: Material) {
    const item = list.items.find((row) => row.material_type === value);
    if (item) {
      setUnitPrice(item.unit_price);
      setWaste(item.waste_percent);
      setDepth(item.depth || defaults[value].depth);
    }
    setLabourRate(list.labour_rate);
    setDelivery(list.delivery_cost);
    setTaxRate(list.tax_rate);
  }

  useEffect(() => {
    let active = true;
    request<PriceList>("/api/v1/price-list", token)
      .then((list) => { if (active) setPriceList(list); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (priceList && savedEstimateLoaded && !estimate) applyPriceList(priceList, material);
    // Only when the price list or the saved-estimate check first arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [priceList, savedEstimateLoaded]);

  useEffect(() => {
    let active = true;
    request<GenerationMaterialEstimate>(`/api/v1/generations/${jobId}/material-estimate`, token)
      .then((row) => {
        if (!active) return;
        setEstimate(row);
        setMaterial(row.material_type);
        setUnit(row.measurement_unit);
        setArea(toHundredths(row.measured_area));
        setPerimeter(toHundredths(row.measured_perimeter));
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
      })
      .finally(() => { if (active) setSavedEstimateLoaded(true); });
    return () => { active = false; };
  }, [jobId, onMessage, token]);

  function changeMaterial(value: Material) {
    setMaterial(value);
    setWaste(defaults[value].waste);
    setDepth(defaults[value].depth);
    setLabourHours("");
    if (priceList) applyPriceList(priceList, value);
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
  const priceItem = priceList?.items.find((row) => row.material_type === material);
  const priceListEmpty = priceList ? priceList.items.every((row) => Number(row.unit_price) === 0) : false;

  return <details className="material-estimator">
    <summary><Calculator /> Material, labour and suppliers</summary>
    <p className={priceListEmpty ? "estimator-source empty" : "estimator-source"}>
      <Tags aria-hidden="true" />
      {priceListEmpty
        ? "Set up your price list in Settings and estimates will fill in your own costs automatically."
        : `Prices from your price list${priceItem?.supplier ? ` · ${materialLabels[material].name} from ${priceItem.supplier}` : ""}. Adjust any number for this job.`}
    </p>
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
    {estimate && <EstimateBreakdown estimate={estimate} supplier={priceItem?.supplier} />}
  </details>;
}

function EstimateBreakdown({ estimate, supplier }: { estimate: GenerationMaterialEstimate; supplier?: string | null }) {
  const name = materialLabels[estimate.material_type].name;
  const unitLabel = estimate.material_unit;
  const qty = (value: string) => Number(value).toLocaleString("en-CA", { maximumFractionDigits: 2 });
  return (
    <div className="estimate-breakdown" aria-label="Estimate breakdown">
      <div className="estimate-measured">
        <div><span>Measured area</span><strong>{qty(estimate.measured_area)} sq {estimate.measurement_unit}</strong></div>
        <div><span>Edge length</span><strong>{qty(estimate.edging_quantity)} {estimate.measurement_unit}</strong></div>
        {estimate.depth && <div><span>Depth</span><strong>{qty(estimate.depth)} {estimate.measurement_unit === "m" ? "cm" : "in"}</strong></div>}
      </div>
      <table>
        <thead><tr><th scope="col">Item</th><th scope="col">Quantity</th><th scope="col" className="rate-col">Rate</th><th scope="col">Amount</th></tr></thead>
        <tbody>
          <tr>
            <th scope="row">{name}{supplier ? <small>{supplier}</small> : null}</th>
            <td>{qty(estimate.order_quantity)} {unitLabel}<small>incl. {qty(estimate.waste_percent)}% waste</small><small className="rate-inline">at {formatMoney(estimate.unit_price)} / {unitLabel}</small></td>
            <td className="rate-col">{formatMoney(estimate.unit_price)} / {unitLabel}</td>
            <td>{formatMoney(estimate.material_cost)}</td>
          </tr>
          <tr>
            <th scope="row">Labour</th>
            <td>{qty(estimate.labour_hours)} h<small className="rate-inline">at {formatMoney(estimate.labour_rate)} / h</small></td>
            <td className="rate-col">{formatMoney(estimate.labour_rate)} / h</td>
            <td>{formatMoney(estimate.labour_cost)}</td>
          </tr>
          {Number(estimate.delivery_cost) > 0 && <tr>
            <th scope="row">Delivery</th><td>1 trip</td><td className="rate-col">—</td><td>{formatMoney(estimate.delivery_cost)}</td>
          </tr>}
        </tbody>
        <tfoot>
          <tr><th scope="row" colSpan={2}>Subtotal</th><td className="rate-col" /><td>{formatMoney(estimate.subtotal)}</td></tr>
          <tr><th scope="row" colSpan={2}>Tax ({qty(estimate.tax_rate)}%)</th><td className="rate-col" /><td>{formatMoney(estimate.tax_amount)}</td></tr>
          <tr className="estimate-grand-total"><th scope="row" colSpan={2}>Estimated total</th><td className="rate-col" /><td>{formatMoney(estimate.total, estimate.currency)}</td></tr>
        </tfoot>
      </table>
      <ul>{estimate.assumptions.map((item) => <li key={item}><PackageCheck />{item}</li>)}</ul>
      <small>Planning estimate from a photo measurement. Confirm dimensions on site before quoting or ordering.</small>
    </div>
  );
}
