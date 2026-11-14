"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Eraser, Paintbrush, Ruler, RotateCcw, ScanLine } from "lucide-react";
import { captureBlob } from "@/lib/api";
import {
  REFERENCE_OBJECTS,
  convertLength,
  detectReferenceObject,
  groundHomography,
  hardscapeEdgeShare,
  longSidePixels,
  measureSelection,
  orderCorners,
  type Point,
} from "@/features/design-studio/ground-plane";

type MaskEditorProps = {
  captureId: string;
  token: string;
  onChange: (mask?: File) => void;
  onMeasurement?: (measurement?: MaskMeasurement) => void;
  onError: (message: string) => void;
};

export type MaskMeasurement = {
  method?: "mask_pixels" | "reference_line" | "camera_reference" | "reference_object";
  selectedPixelCount: number;
  totalPixelCount: number;
  selectedPercent: number;
  calibrationPixelLength?: number;
  calibrationRealLength?: number;
  calibrationUnit?: "ft" | "m";
  /** The known object used for scale, e.g. "Letter paper (8.5 × 11 in)". */
  calibrationReference?: string;
  estimatedArea?: number;
  estimatedPerimeter?: number;
  confidence: "uncalibrated" | "photo_estimate";
};

type Mode = "paint" | "erase" | "object" | "line";
type Unit = "ft" | "m";

/** Warn when at least this share of the selection's edge runs along a path, patio or wall. */
const HARD_EDGE_WARNING_SHARE = 0.12;

export function MaskEditor({ captureId, token, onChange, onMeasurement, onError }: MaskEditorProps) {
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const calibrationRef = useRef<HTMLCanvasElement>(null);
  const maskRef = useRef<HTMLCanvasElement>(null);
  const photoPixelsRef = useRef<ImageData | null>(null);
  const drawingRef = useRef(false);
  const lineStartRef = useRef<Point | null>(null);
  const draggingCornerRef = useRef<number | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [brushSize, setBrushSize] = useState(48);
  const [hasSelection, setHasSelection] = useState(false);
  const [mode, setMode] = useState<Mode>("paint");
  const [line, setLine] = useState<{ start: Point; end: Point } | null>(null);
  const [knownLength, setKnownLength] = useState("");
  const [corners, setCorners] = useState<Point[]>([]);
  const [objectId, setObjectId] = useState(REFERENCE_OBJECTS[0].id);
  const [customWidth, setCustomWidth] = useState("");
  const [customLength, setCustomLength] = useState("");
  const [unit, setUnit] = useState<Unit>("ft");
  const [objectHint, setObjectHint] = useState("");
  const [measurement, setMeasurement] = useState<MaskMeasurement>();
  const [beyondGround, setBeyondGround] = useState(false);
  const [hardEdgeShare, setHardEdgeShare] = useState(0);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setImageUrl("");
    setHasSelection(false);
    setLine(null);
    setCorners([]);
    setMeasurement(undefined);
    setHardEdgeShare(0);
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

  function initialize(image: HTMLImageElement) {
    const width = image.naturalWidth;
    const height = image.naturalHeight;
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
    const scratch = document.createElement("canvas");
    scratch.width = width;
    scratch.height = height;
    const scratchContext = scratch.getContext("2d", { willReadFrequently: true });
    if (scratchContext) {
      scratchContext.drawImage(image, 0, 0);
      try {
        photoPixelsRef.current = scratchContext.getImageData(0, 0, width, height);
      } catch {
        photoPixelsRef.current = null;
      }
    }
  }

  function selectedObject() {
    if (objectId !== "custom") return REFERENCE_OBJECTS.find((item) => item.id === objectId) ?? REFERENCE_OBJECTS[0];
    const width = Number(customWidth);
    const length = Number(customLength);
    if (!(width > 0 && length > 0)) return null;
    return { id: "custom", label: `Custom object (${width} × ${length} ${unit})`, width: Math.min(width, length), length: Math.max(width, length), unit };
  }

  function point(event: React.PointerEvent<HTMLCanvasElement>): Point {
    const canvas = event.currentTarget;
    const bounds = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - bounds.left) * (canvas.width / bounds.width),
      y: (event.clientY - bounds.top) * (canvas.height / bounds.height),
    };
  }

  function handleRadius(canvas: HTMLCanvasElement) {
    return Math.max(10, 22 * (canvas.width / Math.max(1, canvas.clientWidth)));
  }

  function stroke(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current) return;
    const next = point(event);
    if (mode === "line") {
      if (lineStartRef.current) setLine({ start: lineStartRef.current, end: next });
      return;
    }
    if (mode === "object") {
      const index = draggingCornerRef.current;
      if (index !== null) setCorners((current) => current.map((corner, i) => (i === index ? next : corner)));
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

  function placeObject(at: Point) {
    const canvas = calibrationRef.current;
    if (!canvas) return;
    const near = corners.findIndex((corner) => Math.hypot(corner.x - at.x, corner.y - at.y) <= handleRadius(canvas));
    if (near >= 0) {
      draggingCornerRef.current = near;
      return;
    }
    if (corners.length === 0 || corners.length === 4) {
      const pixels = photoPixelsRef.current;
      const found = pixels ? detectReferenceObject(pixels.data, pixels.width, pixels.height, at) : null;
      if (found) {
        setCorners(found);
        setObjectHint("Found it. Drag any corner if it is not exactly on the object.");
        return;
      }
      setCorners([at]);
      setObjectHint("Couldn't find its edges automatically. Tap the other 3 corners of the object.");
      return;
    }
    const next = [...corners, at];
    setCorners(next.length === 4 ? orderCorners(next) : next);
    setObjectHint(next.length === 4 ? "Drag any corner to fine-tune." : `Tap ${4 - next.length} more corner${next.length === 3 ? "" : "s"}.`);
  }

  function begin(event: React.PointerEvent<HTMLCanvasElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    const start = point(event);
    if (mode === "line") {
      lineStartRef.current = start;
      setLine({ start, end: start });
      return;
    }
    if (mode === "object") {
      placeObject(start);
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
    draggingCornerRef.current = null;
    if (mode === "line" || mode === "object") return;
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
    setHardEdgeShare(0);
    setBeyondGround(false);
    onChange(undefined);
    onMeasurement?.(undefined);
  }

  // Draw the reference line or the object outline.
  useEffect(() => {
    const canvas = calibrationRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    const size = Math.max(3, canvas.width / 350);
    context.strokeStyle = "#f6c453";
    context.fillStyle = "#f6c453";
    context.lineWidth = size;
    if (mode !== "object" && line) {
      context.setLineDash([10, 7]);
      context.beginPath();
      context.moveTo(line.start.x, line.start.y);
      context.lineTo(line.end.x, line.end.y);
      context.stroke();
      context.setLineDash([]);
      for (const p of [line.start, line.end]) {
        context.beginPath();
        context.arc(p.x, p.y, Math.max(5, canvas.width / 180), 0, Math.PI * 2);
        context.fill();
      }
    }
    if (corners.length) {
      context.beginPath();
      corners.forEach((p, i) => (i ? context.lineTo(p.x, p.y) : context.moveTo(p.x, p.y)));
      if (corners.length === 4) context.closePath();
      context.fillStyle = "rgba(246, 196, 83, 0.25)";
      if (corners.length === 4) context.fill();
      context.stroke();
      const radius = Math.max(6, canvas.width / 160);
      for (const p of corners) {
        context.beginPath();
        context.arc(p.x, p.y, radius, 0, Math.PI * 2);
        context.fillStyle = "#f6c453";
        context.fill();
        context.lineWidth = Math.max(2, size / 2);
        context.strokeStyle = "#13261a";
        context.stroke();
        context.strokeStyle = "#f6c453";
        context.lineWidth = size;
      }
    }
  }, [corners, line, mode]);

  function calculateMeasurement() {
    const canvas = maskRef.current;
    const context = canvas?.getContext("2d", { willReadFrequently: true });
    if (!canvas || !context) return;
    const { width, height } = canvas;
    const pixels = context.getImageData(0, 0, width, height).data;
    const selected = new Uint8Array(width * height);
    for (let index = 0; index < selected.length; index += 1) selected[index] = pixels[index * 4] >= 128 ? 1 : 0;

    const photo = photoPixelsRef.current;
    setHardEdgeShare(photo ? hardscapeEdgeShare(photo.data, selected, width, height).share : 0);

    const object = selectedObject();
    const useObject = corners.length === 4 && object;
    const homography = useObject ? groundHomography(corners, object, { width, height }) : null;
    const linePixels = line ? Math.hypot(line.end.x - line.start.x, line.end.y - line.start.y) : 0;
    const realLength = Number(knownLength);
    const lineScale = !homography && linePixels > 4 && realLength > 0 ? realLength / linePixels : undefined;

    const base = measureSelection(selected, width, height);
    const shared = {
      selectedPixelCount: base.selectedPixelCount,
      totalPixelCount: selected.length,
      selectedPercent: selected.length ? (base.selectedPixelCount / selected.length) * 100 : 0,
    };
    let next: MaskMeasurement = { ...shared, confidence: "uncalibrated", method: "mask_pixels" };
    setBeyondGround(false);
    if (homography && object) {
      const ground = measureSelection(selected, width, height, { homography });
      // The homography works in the object's own unit; report in the chosen unit.
      const factor = convertLength(1, object.unit, unit);
      if (ground.beyondGround) {
        setBeyondGround(true);
      } else if (ground.area && ground.perimeter) {
        next = {
          ...shared,
          method: "reference_object",
          confidence: "photo_estimate",
          calibrationReference: object.label,
          calibrationPixelLength: longSidePixels(corners),
          calibrationRealLength: convertLength(object.length, object.unit, unit),
          calibrationUnit: unit,
          estimatedArea: ground.area * factor * factor,
          estimatedPerimeter: ground.perimeter * factor,
        };
      }
    } else if (lineScale) {
      const flat = measureSelection(selected, width, height, { unitsPerPixel: lineScale });
      next = {
        ...shared,
        method: "reference_line",
        confidence: "photo_estimate",
        calibrationPixelLength: linePixels,
        calibrationRealLength: realLength,
        calibrationUnit: unit,
        estimatedArea: flat.area,
        estimatedPerimeter: flat.perimeter,
      };
    }
    setMeasurement(next);
    onMeasurement?.(next);
  }

  useEffect(() => {
    if (hasSelection) calculateMeasurement();
    // Recalculate when calibration values change; the mask canvas is intentionally read imperatively.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corners, line, knownLength, unit, objectId, customWidth, customLength]);

  const scaleMode = mode === "object" || mode === "line";
  const hardEdgeWarning = hasSelection && hardEdgeShare >= HARD_EDGE_WARNING_SHARE;

  return (
    <div className="mask-editor">
      <div className="mask-editor-heading">
        <div><strong>Edit area</strong><span>Paint the part of the photo that AI may change.</span></div>
        <div className="mask-editor-tools">
          <button type="button" className={mode === "paint" ? "active" : ""} onClick={() => setMode("paint")}><Paintbrush /> Paint</button>
          <button type="button" className={mode === "erase" ? "active" : ""} onClick={() => setMode("erase")}><Eraser /> Erase</button>
          <button type="button" className={mode === "object" ? "active" : ""} onClick={() => { setMode("object"); setObjectHint(corners.length === 4 ? "Drag any corner to fine-tune, or tap another object." : "Tap the object lying on the ground."); }}><ScanLine /> Known object</button>
          <button type="button" className={mode === "line" ? "active" : ""} onClick={() => setMode("line")}><Ruler /> Line</button>
          <button type="button" onClick={clear}><RotateCcw /> Clear</button>
        </div>
      </div>
      {!scaleMode && <label className="mask-brush-size">Brush size
        <input type="range" min="12" max="140" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} />
      </label>}
      {mode === "line" ? <div className="mask-calibration">
        <div><strong>Measure with a line</strong><span>Draw a line over something on the ground with a known length. Less accurate than a known object when the photo is taken at an angle.</span></div>
        <label>Known length<input type="number" min="0.1" step="0.1" value={knownLength} onChange={(event) => setKnownLength(event.target.value)} placeholder="4" /></label>
        <label>Unit<select value={unit} onChange={(event) => setUnit(event.target.value as Unit)}><option value="ft">feet</option><option value="m">metres</option></select></label>
      </div> : <div className="mask-calibration object">
        <div><strong>Measure with a known object</strong><span>{mode === "object" ? (objectHint || "Tap the object lying on the ground.") : "Lay a sheet of paper or a patio slab flat on the ground before taking the photo, then choose Known object and tap it. Corrects for perspective."}</span></div>
        <label>Object<select value={objectId} onChange={(event) => setObjectId(event.target.value)}>
          {REFERENCE_OBJECTS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          <option value="custom">Custom size…</option>
        </select></label>
        <label>Results in<select value={unit} onChange={(event) => setUnit(event.target.value as Unit)}><option value="ft">feet</option><option value="m">metres</option></select></label>
        {objectId === "custom" && <div className="mask-custom-object">
          <label>Width ({unit})<input type="number" min="0.05" step="0.05" value={customWidth} onChange={(event) => setCustomWidth(event.target.value)} /></label>
          <label>Length ({unit})<input type="number" min="0.05" step="0.05" value={customLength} onChange={(event) => setCustomLength(event.target.value)} /></label>
        </div>}
      </div>}
      <div className="mask-editor-stage">
        {imageUrl ? <div className="mask-editor-image">
          {/* Authenticated blob URLs cannot use the Next image optimizer. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt="Source property" onLoad={(event) => initialize(event.currentTarget)} />
          <canvas ref={overlayRef} onPointerDown={begin} onPointerMove={stroke} onPointerUp={finish} onPointerCancel={finish} />
          <canvas className="calibration-canvas" ref={calibrationRef} onPointerDown={begin} onPointerMove={stroke} onPointerUp={finish} onPointerCancel={finish} style={{ pointerEvents: scaleMode ? "auto" : "none" }} />
          <canvas ref={maskRef} hidden />
        </div> : <span>Loading source photo…</span>}
      </div>
      <p className={hasSelection ? "mask-ready" : "mask-required"}>{hasSelection ? "Editable area selected." : "Paint at least one area before generating."}</p>
      {hardEdgeWarning && <div className="mask-warning" role="status">
        <AlertTriangle />
        <div><strong>The selection runs along a path, patio or wall</strong><span>About {Math.round(hardEdgeShare * 100)}% of its edge touches a hard grey surface. The AI may continue that surface into the new area. Stop the brush a little short of hard edges for the cleanest result.</span></div>
      </div>}
      {beyondGround && <div className="mask-warning" role="status">
        <AlertTriangle />
        <div><strong>Part of the selection is not on the ground</strong><span>Area can only be measured on flat ground. Erase any sky, fence or wall from the selection, or check the object corners.</span></div>
      </div>}
      {measurement && <div className="mask-measurement" aria-live="polite">
        <div><span>Selected photo area</span><strong>{measurement.selectedPercent.toFixed(1)}%</strong></div>
        <div><span>Estimated area</span><strong>{measurement.estimatedArea ? `${measurement.estimatedArea.toFixed(1)} sq ${measurement.calibrationUnit}` : "Scale required"}</strong></div>
        <div><span>Estimated perimeter</span><strong>{measurement.estimatedPerimeter ? `${measurement.estimatedPerimeter.toFixed(1)} ${measurement.calibrationUnit}` : "Scale required"}</strong></div>
        <small>{measurement.method === "reference_object" ? `Perspective-corrected from ${measurement.calibrationReference?.toLowerCase()} · verify on site before ordering` : measurement.confidence === "photo_estimate" ? "Photo estimate · verify on site before ordering" : "Tap a known object on the ground, or draw a line of known length, to measure real dimensions"}</small>
      </div>}
    </div>
  );
}
