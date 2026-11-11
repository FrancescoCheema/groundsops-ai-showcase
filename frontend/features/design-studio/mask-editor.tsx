"use client";

import { useEffect, useRef, useState } from "react";
import { Eraser, Paintbrush, Ruler, RotateCcw } from "lucide-react";
import { captureBlob } from "@/lib/api";

type MaskEditorProps = {
  captureId: string;
  token: string;
  onChange: (mask?: File) => void;
  onMeasurement?: (measurement?: MaskMeasurement) => void;
  onError: (message: string) => void;
};

export type MaskMeasurement = {
  method?: "mask_pixels" | "reference_line" | "camera_reference";
  selectedPixelCount: number;
  totalPixelCount: number;
  selectedPercent: number;
  calibrationPixelLength?: number;
  calibrationRealLength?: number;
  calibrationUnit?: "ft" | "m";
  estimatedArea?: number;
  estimatedPerimeter?: number;
  confidence: "uncalibrated" | "photo_estimate";
};

export function MaskEditor({ captureId, token, onChange, onMeasurement, onError }: MaskEditorProps) {
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const calibrationRef = useRef<HTMLCanvasElement>(null);
  const maskRef = useRef<HTMLCanvasElement>(null);
  const drawingRef = useRef(false);
  const calibrationStartRef = useRef<{ x: number; y: number } | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [brushSize, setBrushSize] = useState(48);
  const [hasSelection, setHasSelection] = useState(false);
  const [mode, setMode] = useState<"paint" | "erase" | "calibrate">("paint");
  const [calibrationPixels, setCalibrationPixels] = useState(0);
  const [knownLength, setKnownLength] = useState("");
  const [unit, setUnit] = useState<"ft" | "m">("ft");
  const [measurement, setMeasurement] = useState<MaskMeasurement>();

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setImageUrl("");
    setHasSelection(false);
    setCalibrationPixels(0);
    setMeasurement(undefined);
    onChange(undefined);
    onMeasurement?.(undefined);
    captureBlob(captureId, token)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setImageUrl(objectUrl);
      })
      .catch((error) => onError(error instanceof Error ? error.message : "Source photo could not be loaded."));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [captureId, onChange, onError, onMeasurement, token]);

  function initialize(width: number, height: number) {
    for (const canvas of [overlayRef.current, calibrationRef.current, maskRef.current]) {
      if (!canvas) continue;
      canvas.width = width;
      canvas.height = height;
    }
    const context = maskRef.current?.getContext("2d");
    if (context) {
      context.fillStyle = "black";
      context.fillRect(0, 0, width, height);
    }
  }

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const canvas = event.currentTarget;
    const bounds = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - bounds.left) * (canvas.width / bounds.width),
      y: (event.clientY - bounds.top) * (canvas.height / bounds.height),
    };
  }

  function stroke(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current) return;
    const next = point(event);
    if (mode === "calibrate") {
      drawCalibration(next);
      return;
    }
    const overlay = overlayRef.current?.getContext("2d");
    const mask = maskRef.current?.getContext("2d");
    if (!overlay || !mask) return;
    const width = brushSize * (event.currentTarget.width / event.currentTarget.clientWidth);
    for (const context of [overlay, mask]) {
      context.lineCap = "round";
      context.lineJoin = "round";
      context.lineWidth = width;
      context.lineTo(next.x, next.y);
      context.stroke();
    }
  }

  function begin(event: React.PointerEvent<HTMLCanvasElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    const start = point(event);
    if (mode === "calibrate") {
      calibrationStartRef.current = start;
      drawCalibration(start);
      return;
    }
    const overlay = overlayRef.current?.getContext("2d");
    const mask = maskRef.current?.getContext("2d");
    if (!overlay || !mask) return;
    overlay.globalCompositeOperation = mode === "erase" ? "destination-out" : "source-over";
    overlay.strokeStyle = "rgba(74, 222, 128, .72)";
    mask.globalCompositeOperation = "source-over";
    mask.strokeStyle = mode === "erase" ? "black" : "white";
    for (const context of [overlay, mask]) {
      context.beginPath();
      context.moveTo(start.x, start.y);
      context.lineTo(start.x + 0.01, start.y + 0.01);
    }
    stroke(event);
    setHasSelection(true);
  }

  function finish() {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (mode === "calibrate") {
      calculateMeasurement();
      return;
    }
    const canvas = maskRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) {
        onChange(new File([blob], "groundsops-edit-mask.png", { type: "image/png" }));
        calculateMeasurement();
      }
    }, "image/png");
  }

  function clear() {
    const overlay = overlayRef.current;
    const mask = maskRef.current;
    overlay?.getContext("2d")?.clearRect(0, 0, overlay.width, overlay.height);
    const context = mask?.getContext("2d");
    if (context && mask) {
      context.globalCompositeOperation = "source-over";
      context.fillStyle = "black";
      context.fillRect(0, 0, mask.width, mask.height);
    }
    setHasSelection(false);
    setMeasurement(undefined);
    onChange(undefined);
    onMeasurement?.(undefined);
  }

  function drawCalibration(end: { x: number; y: number }) {
    const canvas = calibrationRef.current;
    const start = calibrationStartRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !start || !context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#f6c453";
    context.fillStyle = "#f6c453";
    context.lineWidth = Math.max(3, canvas.width / 350);
    context.setLineDash([10, 7]);
    context.beginPath();
    context.moveTo(start.x, start.y);
    context.lineTo(end.x, end.y);
    context.stroke();
    context.setLineDash([]);
    for (const point of [start, end]) {
      context.beginPath();
      context.arc(point.x, point.y, Math.max(5, canvas.width / 180), 0, Math.PI * 2);
      context.fill();
    }
    setCalibrationPixels(Math.hypot(end.x - start.x, end.y - start.y));
  }

  function calculateMeasurement() {
    const canvas = maskRef.current;
    const context = canvas?.getContext("2d", { willReadFrequently: true });
    if (!canvas || !context) return;
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const selected = new Uint8Array(canvas.width * canvas.height);
    let selectedPixelCount = 0;
    for (let index = 0; index < selected.length; index += 1) {
      selected[index] = pixels[index * 4] >= 128 ? 1 : 0;
      selectedPixelCount += selected[index];
    }
    let perimeterPixels = 0;
    for (let y = 0; y < canvas.height; y += 1) {
      for (let x = 0; x < canvas.width; x += 1) {
        const index = y * canvas.width + x;
        if (!selected[index]) continue;
        perimeterPixels += Number(x === 0 || !selected[index - 1]);
        perimeterPixels += Number(x === canvas.width - 1 || !selected[index + 1]);
        perimeterPixels += Number(y === 0 || !selected[index - canvas.width]);
        perimeterPixels += Number(y === canvas.height - 1 || !selected[index + canvas.width]);
      }
    }
    const realLength = Number(knownLength);
    const scale = calibrationPixels > 0 && realLength > 0 ? realLength / calibrationPixels : undefined;
    const next: MaskMeasurement = {
      selectedPixelCount,
      totalPixelCount: selected.length,
      selectedPercent: selected.length ? (selectedPixelCount / selected.length) * 100 : 0,
      calibrationPixelLength: scale ? calibrationPixels : undefined,
      calibrationRealLength: scale ? realLength : undefined,
      calibrationUnit: scale ? unit : undefined,
      estimatedArea: scale ? selectedPixelCount * scale * scale : undefined,
      estimatedPerimeter: scale ? perimeterPixels * scale : undefined,
      confidence: scale ? "photo_estimate" : "uncalibrated",
      method: scale ? "reference_line" : "mask_pixels",
    };
    setMeasurement(next);
    onMeasurement?.(next);
  }

  useEffect(() => {
    if (hasSelection) calculateMeasurement();
    // Recalculate when calibration values change; the mask canvas is intentionally read imperatively.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [calibrationPixels, knownLength, unit]);

  return (
    <div className="mask-editor">
      <div className="mask-editor-heading">
        <div><strong>Edit area</strong><span>Paint the part of the photo that AI may change.</span></div>
        <div className="mask-editor-tools">
          <button type="button" className={mode === "paint" ? "active" : ""} onClick={() => setMode("paint")}><Paintbrush /> Paint</button>
          <button type="button" className={mode === "erase" ? "active" : ""} onClick={() => setMode("erase")}><Eraser /> Erase</button>
          <button type="button" className={mode === "calibrate" ? "active" : ""} onClick={() => setMode("calibrate")}><Ruler /> Calibrate</button>
          <button type="button" onClick={clear}><RotateCcw /> Clear</button>
        </div>
      </div>
      {mode !== "calibrate" && <label className="mask-brush-size">Brush size
        <input type="range" min="12" max="140" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} />
      </label>}
      <div className="mask-calibration">
        <div><strong>Photo scale</strong><span>Select Calibrate, then draw a line over something with a known length.</span></div>
        <label>Known length<input type="number" min="0.1" step="0.1" value={knownLength} onChange={(event) => setKnownLength(event.target.value)} placeholder="4" /></label>
        <label>Unit<select value={unit} onChange={(event) => setUnit(event.target.value as "ft" | "m")}><option value="ft">feet</option><option value="m">metres</option></select></label>
      </div>
      <div className="mask-editor-stage">
        {imageUrl ? <div className="mask-editor-image">
          {/* Authenticated blob URLs cannot use the Next image optimizer. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt="Source property" onLoad={(event) => initialize(event.currentTarget.naturalWidth, event.currentTarget.naturalHeight)} />
          <canvas ref={overlayRef} onPointerDown={begin} onPointerMove={stroke} onPointerUp={finish} onPointerCancel={finish} />
          <canvas className="calibration-canvas" ref={calibrationRef} onPointerDown={begin} onPointerMove={stroke} onPointerUp={finish} onPointerCancel={finish} style={{ pointerEvents: mode === "calibrate" ? "auto" : "none" }} />
          <canvas ref={maskRef} hidden />
        </div> : <span>Loading source photo…</span>}
      </div>
      <p className={hasSelection ? "mask-ready" : "mask-required"}>{hasSelection ? "Editable area selected." : "Paint at least one area before generating."}</p>
      {measurement && <div className="mask-measurement" aria-live="polite">
        <div><span>Selected photo area</span><strong>{measurement.selectedPercent.toFixed(1)}%</strong></div>
        <div><span>Estimated area</span><strong>{measurement.estimatedArea ? `${measurement.estimatedArea.toFixed(1)} sq ${measurement.calibrationUnit}` : "Calibration required"}</strong></div>
        <div><span>Estimated perimeter</span><strong>{measurement.estimatedPerimeter ? `${measurement.estimatedPerimeter.toFixed(1)} ${measurement.calibrationUnit}` : "Calibration required"}</strong></div>
        <small>{measurement.confidence === "photo_estimate" ? "Photo estimate · verify on site before ordering" : "Draw and label a calibration line to estimate real dimensions"}</small>
      </div>}
    </div>
  );
}
