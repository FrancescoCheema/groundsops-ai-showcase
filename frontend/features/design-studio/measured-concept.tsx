"use client";

import { Ruler, ScanLine, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { downloadAuthenticated, type GenerationJob } from "@/lib/api";

const OUTLINE = "#ffd23f";

function loadImage(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Image could not be loaded"));
    };
    image.src = url;
  });
}

/** Draw the selection the measurement came from: tinted fill, bold outline and the area label. */
function drawMeasuredArea(canvas: HTMLCanvasElement, concept: HTMLImageElement, mask: HTMLImageElement | null, label: string) {
  const width = concept.naturalWidth;
  const height = concept.naturalHeight;
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return;
  context.drawImage(concept, 0, 0, width, height);
  if (!mask) return;

  const scratch = document.createElement("canvas");
  scratch.width = width;
  scratch.height = height;
  const scratchContext = scratch.getContext("2d", { willReadFrequently: true });
  if (!scratchContext) return;
  scratchContext.drawImage(mask, 0, 0, width, height);
  const pixels = scratchContext.getImageData(0, 0, width, height).data;
  const inside = (x: number, y: number) => x >= 0 && y >= 0 && x < width && y < height && pixels[(y * width + x) * 4] >= 128;

  const overlay = context.getImageData(0, 0, width, height);
  const out = overlay.data;
  const stroke = Math.max(2, Math.round(Math.min(width, height) / 220));
  let sumX = 0;
  let sumY = 0;
  let count = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (!inside(x, y)) continue;
      sumX += x;
      sumY += y;
      count += 1;
      const index = (y * width + x) * 4;
      let edge = false;
      for (let d = 1; d <= stroke && !edge; d += 1) {
        edge = !inside(x - d, y) || !inside(x + d, y) || !inside(x, y - d) || !inside(x, y + d);
      }
      if (edge) {
        out[index] = 255; out[index + 1] = 210; out[index + 2] = 63;
      } else {
        // A light warm tint keeps the new surface visible while showing what was measured.
        out[index] = Math.round(out[index] * 0.82 + 255 * 0.18);
        out[index + 1] = Math.round(out[index + 1] * 0.82 + 210 * 0.18);
        out[index + 2] = Math.round(out[index + 2] * 0.82 + 63 * 0.18);
      }
    }
  }
  context.putImageData(overlay, 0, 0);
  if (!count || !label) return;

  const fontSize = Math.max(14, Math.round(Math.min(width, height) / 18));
  context.font = `800 ${fontSize}px system-ui, -apple-system, Segoe UI, sans-serif`;
  const padding = Math.round(fontSize * 0.45);
  const textWidth = context.measureText(label).width;
  const boxWidth = textWidth + padding * 2;
  const boxHeight = fontSize + padding * 1.4;
  const x = Math.min(Math.max(sumX / count - boxWidth / 2, 4), width - boxWidth - 4);
  const y = Math.min(Math.max(sumY / count - boxHeight / 2, 4), height - boxHeight - 4);
  context.fillStyle = "rgba(17, 30, 22, 0.86)";
  context.beginPath();
  context.roundRect(x, y, boxWidth, boxHeight, boxHeight / 3);
  context.fill();
  context.strokeStyle = OUTLINE;
  context.lineWidth = Math.max(2, fontSize / 10);
  context.stroke();
  context.fillStyle = "#ffffff";
  context.textBaseline = "middle";
  context.fillText(label, x + padding, y + boxHeight / 2 + 1);
}

function formatNumber(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: value < 100 ? 1 : 0 });
}

export function MeasuredConcept({ job, token }: { job: GenerationJob; token: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [images, setImages] = useState<{ concept: HTMLImageElement; mask: HTMLImageElement | null } | null>(null);
  const [failed, setFailed] = useState(false);
  const [showArea, setShowArea] = useState(true);

  const unit = job.calibration_unit;
  const area = job.estimated_area ? Number(job.estimated_area) : null;
  const perimeter = job.estimated_perimeter ? Number(job.estimated_perimeter) : null;
  const measured = area !== null && Boolean(unit);
  const areaLabel = measured ? `${formatNumber(area)} sq ${unit}` : "";

  useEffect(() => {
    let active = true;
    const loaded: HTMLImageElement[] = [];
    (async () => {
      try {
        const concept = await loadImage(await downloadAuthenticated(`/api/v1/generations/${job.id}/output`, token));
        loaded.push(concept);
        let mask: HTMLImageElement | null = null;
        try {
          mask = await loadImage(await downloadAuthenticated(`/api/v1/generations/${job.id}/mask`, token));
          loaded.push(mask);
        } catch {
          mask = null;
        }
        if (active) setImages({ concept, mask });
      } catch {
        if (active) setFailed(true);
      }
    })();
    return () => {
      active = false;
      loaded.forEach((image) => URL.revokeObjectURL(image.src));
    };
  }, [job.id, token]);

  useEffect(() => {
    if (!images || !canvasRef.current) return;
    drawMeasuredArea(canvasRef.current, images.concept, showArea ? images.mask : null, areaLabel);
  }, [images, showArea, areaLabel]);

  if (failed) return <div className="capture-loading">The generated concept could not be loaded.</div>;
  if (!images) return <div className="capture-loading">Loading generated concept…</div>;

  const method = job.measurement_method === "reference_object"
    ? `Perspective-corrected from ${job.calibration_reference ? job.calibration_reference.replace(/^./, (c) => c.toLowerCase()) : "a known object"} on the ground`
    : job.measurement_method === "reference_line" || job.measurement_method === "camera_reference"
      ? `Calibrated from a reference line${job.calibration_real_length ? ` (${Number(job.calibration_real_length)} ${unit})` : ""}`
      : "Scaled from the photo";

  return <div className="measured-concept">
    <div className="measured-concept-frame">
      <canvas
        ref={canvasRef}
        className="generation-output"
        role="img"
        aria-label={measured && showArea ? `Generated landscape concept with the measured area of ${areaLabel} outlined` : "Generated landscape concept"}
      />
      {images.mask && <button type="button" className="measured-concept-toggle" aria-pressed={showArea} onClick={() => setShowArea((value) => !value)}>
        <ScanLine />{showArea ? "Hide measured area" : "Show measured area"}
      </button>}
    </div>
    {measured ? <div className="measurement-tiles">
      <div><span><Square />Measured area</span><strong>{areaLabel}</strong></div>
      {perimeter !== null && <div><span><Ruler />Edge length</span><strong>{formatNumber(perimeter)} {unit}</strong></div>}
      <div className="measurement-method"><span>How it was measured</span><strong>{method}</strong><small>Photo estimate, so confirm on site before ordering materials.</small></div>
    </div> : <p className="measurement-missing">No measurement for this concept. Draw a reference line of known length on the photo before generating to get the area and edge length.</p>}
  </div>;
}
