"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Check, Eraser, Paintbrush, Ruler, RotateCcw, X } from "lucide-react";
import type { MaskMeasurement } from "@/features/design-studio/mask-editor";

type Point = { x: number; y: number };
type DrawMode = "paint" | "erase" | "scale";

async function decodePhoto(file: File) {
  if ("createImageBitmap" in window) {
    const bitmap = await createImageBitmap(file);
    return { source: bitmap as CanvasImageSource, width: bitmap.width, height: bitmap.height, close: () => bitmap.close() };
  }
  const url = URL.createObjectURL(file);
  const image = new Image();
  image.src = url;
  await image.decode();
  return { source: image as CanvasImageSource, width: image.naturalWidth, height: image.naturalHeight, close: () => URL.revokeObjectURL(url) };
}

function distance(a: Point, b: Point) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

export function CameraMeasure({
  onMeasurement,
  onError,
  buttonClassName = "secondary camera-measure-open",
}: {
  onMeasurement: (measurement: MaskMeasurement) => void;
  onError: (message: string) => void;
  buttonClassName?: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const maskRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const frameRef = useRef<ImageData | null>(null);
  const drawingRef = useRef(false);
  const previousRef = useRef<Point | null>(null);
  const scaleDragRef = useRef<{ index: number; pointerId: number } | null>(null);
  const measurementFrameRef = useRef<number | undefined>(undefined);
  const onMeasurementRef = useRef(onMeasurement);
  const [open, setOpen] = useState(false);
  const [captured, setCaptured] = useState(false);
  const [mode, setMode] = useState<DrawMode>("paint");
  const [brushSize, setBrushSize] = useState(56);
  const [scalePoints, setScalePoints] = useState<Point[]>([]);
  const [knownLength, setKnownLength] = useState("4");
  const [unit, setUnit] = useState<"ft" | "m">("ft");
  const [measurement, setMeasurement] = useState<MaskMeasurement>();
  const [cameraStatus, setCameraStatus] = useState<"idle" | "requesting" | "ready" | "error">("idle");
  const [videoReady, setVideoReady] = useState(false);
  const [streamVersion, setStreamVersion] = useState(0);

  useEffect(() => { onMeasurementRef.current = onMeasurement; }, [onMeasurement]);

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  useEffect(() => () => {
    stopCamera();
    if (measurementFrameRef.current) cancelAnimationFrame(measurementFrameRef.current);
  }, []);

  useEffect(() => {
    if (!open || captured || cameraStatus !== "ready") return;
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return;
    video.srcObject = stream;
    const play = async () => {
      try {
        await video.play();
        setVideoReady(video.videoWidth > 0 && video.videoHeight > 0);
      } catch { setVideoReady(false); }
    };
    video.addEventListener("loadedmetadata", play);
    video.addEventListener("canplay", play);
    void play();
    return () => {
      video.removeEventListener("loadedmetadata", play);
      video.removeEventListener("canplay", play);
      if (video.srcObject === stream) video.srcObject = null;
    };
  }, [cameraStatus, captured, open, streamVersion]);

  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context || !frameRef.current) return;
    context.putImageData(frameRef.current, 0, 0);
    const mask = maskRef.current;
    if (mask) {
      const tint = document.createElement("canvas");
      tint.width = canvas.width;
      tint.height = canvas.height;
      const tintContext = tint.getContext("2d");
      if (tintContext) {
        tintContext.fillStyle = "rgba(44, 222, 125, .62)";
        tintContext.fillRect(0, 0, tint.width, tint.height);
        tintContext.globalCompositeOperation = "destination-in";
        tintContext.drawImage(mask, 0, 0);
        context.drawImage(tint, 0, 0);
      }
    }
    if (scalePoints.length) {
      context.save();
      context.strokeStyle = "#ffd166";
      context.fillStyle = "#ffd166";
      context.lineWidth = Math.max(4, canvas.width / 250);
      context.setLineDash([12, 8]);
      context.beginPath();
      context.moveTo(scalePoints[0].x, scalePoints[0].y);
      if (scalePoints[1]) context.lineTo(scalePoints[1].x, scalePoints[1].y);
      context.stroke();
      context.setLineDash([]);
      scalePoints.forEach((point) => {
        context.beginPath();
        context.arc(point.x, point.y, Math.max(11, canvas.width / 105), 0, Math.PI * 2);
        context.fill();
      });
      context.restore();
    }
  }, [scalePoints]);

  const calculate = useCallback(() => {
    const mask = maskRef.current;
    const context = mask?.getContext("2d", { willReadFrequently: true });
    if (!mask || !context) return;
    const pixels = context.getImageData(0, 0, mask.width, mask.height).data;
    const selected = new Uint8Array(mask.width * mask.height);
    let selectedPixelCount = 0;
    for (let index = 0; index < selected.length; index += 1) {
      selected[index] = pixels[index * 4 + 3] >= 64 ? 1 : 0;
      selectedPixelCount += selected[index];
    }
    if (!selectedPixelCount) { setMeasurement(undefined); return; }
    let perimeterPixels = 0;
    for (let y = 0; y < mask.height; y += 1) {
      for (let x = 0; x < mask.width; x += 1) {
        const index = y * mask.width + x;
        if (!selected[index]) continue;
        perimeterPixels += Number(x === 0 || !selected[index - 1]);
        perimeterPixels += Number(x === mask.width - 1 || !selected[index + 1]);
        perimeterPixels += Number(y === 0 || !selected[index - mask.width]);
        perimeterPixels += Number(y === mask.height - 1 || !selected[index + mask.width]);
      }
    }
    const realLength = Number(knownLength);
    const scalePixels = scalePoints.length === 2 ? distance(scalePoints[0], scalePoints[1]) : 0;
    const unitsPerPixel = scalePixels >= 2 && realLength > 0 ? realLength / scalePixels : undefined;
    const next: MaskMeasurement = {
      method: unitsPerPixel ? "camera_reference" : "mask_pixels",
      selectedPixelCount,
      totalPixelCount: selected.length,
      selectedPercent: selectedPixelCount / selected.length * 100,
      calibrationPixelLength: unitsPerPixel ? scalePixels : undefined,
      calibrationRealLength: unitsPerPixel ? realLength : undefined,
      calibrationUnit: unitsPerPixel ? unit : undefined,
      estimatedArea: unitsPerPixel ? selectedPixelCount * unitsPerPixel * unitsPerPixel : undefined,
      estimatedPerimeter: unitsPerPixel ? perimeterPixels * unitsPerPixel : undefined,
      confidence: unitsPerPixel ? "photo_estimate" : "uncalibrated",
    };
    setMeasurement(next);
    onMeasurementRef.current(next);
  }, [knownLength, scalePoints, unit]);

  const updateLive = useCallback(() => {
    renderCanvas();
    if (measurementFrameRef.current) cancelAnimationFrame(measurementFrameRef.current);
    measurementFrameRef.current = requestAnimationFrame(calculate);
  }, [calculate, renderCanvas]);

  useEffect(() => { if (captured) updateLive(); }, [captured, knownLength, scalePoints, unit, updateLive]);

  function initialize(width: number, height: number, source: CanvasImageSource) {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) throw new Error("Measurement canvas is unavailable.");
    canvas.width = width;
    canvas.height = height;
    context.drawImage(source, 0, 0, width, height);
    frameRef.current = context.getImageData(0, 0, width, height);
    const mask = document.createElement("canvas");
    mask.width = width;
    mask.height = height;
    maskRef.current = mask;
    setScalePoints([]);
    setMeasurement(undefined);
    setMode("paint");
  }

  async function startCamera() {
    setOpen(true); setCaptured(false); setVideoReady(false); setCameraStatus("requesting");
    setScalePoints([]); setMeasurement(undefined); stopCamera();
    if (!window.isSecureContext) {
      setCameraStatus("error");
      onError("Camera access requires HTTPS. You can still take or choose a photo below.");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraStatus("error");
      onError("Live camera is unavailable in this browser. Take or choose a photo below.");
      return;
    }
    try {
      streamRef.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
      setCameraStatus("ready");
      setStreamVersion((value) => value + 1);
    } catch (error) {
      setCameraStatus("error");
      const name = error instanceof DOMException ? error.name : "";
      onError(name === "NotAllowedError" ? "Camera permission is blocked. Allow access or choose a photo below." : name === "NotFoundError" ? "No camera was detected. Choose an existing photo below." : "The live camera could not start. Take or choose a photo below.");
    }
  }

  async function importPhoto(file?: File) {
    if (!file) return;
    try {
      setOpen(true); setCameraStatus("idle"); setVideoReady(false); stopCamera();
      await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
      const photo = await decodePhoto(file);
      initialize(photo.width, photo.height, photo.source);
      photo.close();
      setCaptured(true);
    } catch (error) {
      setCaptured(false); setCameraStatus("error");
      onError(error instanceof Error ? error.message : "The photo could not be opened.");
    }
  }

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;
    initialize(video.videoWidth, video.videoHeight, video);
    setCaptured(true); stopCamera();
  }

  function close() { stopCamera(); setOpen(false); setCameraStatus("idle"); setVideoReady(false); }

  function point(event: React.PointerEvent<HTMLCanvasElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    return { x: (event.clientX - bounds.left) * event.currentTarget.width / bounds.width, y: (event.clientY - bounds.top) * event.currentTarget.height / bounds.height };
  }

  function paint(from: Point, to: Point) {
    const mask = maskRef.current;
    const visible = canvasRef.current;
    const context = mask?.getContext("2d");
    if (!mask || !visible || !context) return;
    const displayedWidth = visible.getBoundingClientRect().width || visible.width;
    context.save();
    context.globalCompositeOperation = mode === "erase" ? "destination-out" : "source-over";
    context.strokeStyle = "#fff";
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = brushSize * visible.width / displayedWidth;
    context.beginPath(); context.moveTo(from.x, from.y); context.lineTo(to.x, to.y); context.stroke();
    context.restore();
    updateLive();
  }

  function pointerDown(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!captured) return;
    const next = point(event);
    event.currentTarget.setPointerCapture(event.pointerId);
    if (mode === "scale") {
      const radius = 32 * event.currentTarget.width / event.currentTarget.getBoundingClientRect().width;
      const index = scalePoints.findIndex((candidate) => distance(candidate, next) <= radius);
      if (index >= 0) scaleDragRef.current = { index, pointerId: event.pointerId };
      else setScalePoints((current) => current.length >= 2 ? [next] : [...current, next]);
      return;
    }
    drawingRef.current = true;
    previousRef.current = next;
    paint(next, { x: next.x + .01, y: next.y + .01 });
  }

  function pointerMove(event: React.PointerEvent<HTMLCanvasElement>) {
    const next = point(event);
    const drag = scaleDragRef.current;
    if (drag?.pointerId === event.pointerId) {
      setScalePoints((current) => current.map((value, index) => index === drag.index ? next : value));
      return;
    }
    if (!drawingRef.current || !previousRef.current) return;
    paint(previousRef.current, next);
    previousRef.current = next;
  }

  function pointerUp(event: React.PointerEvent<HTMLCanvasElement>) {
    drawingRef.current = false; previousRef.current = null; scaleDragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    updateLive();
  }

  function clearSelection() {
    const mask = maskRef.current;
    mask?.getContext("2d")?.clearRect(0, 0, mask.width, mask.height);
    setMeasurement(undefined); renderCanvas();
  }

  return <div className="camera-measure-shell">
    <button type="button" className={buttonClassName} onClick={() => void startCamera()}><Camera />Measure with camera</button>
    {open && <div className="camera-measure-dialog" role="dialog" aria-modal="true" aria-label="Camera measurement"><div className="camera-measure-panel">
      <header><div><strong>Camera Measure</strong><span>Capture the ground, paint the work area and calibrate one known length.</span></div><button type="button" onClick={close} aria-label="Close camera measurement"><X /></button></header>
      <div className="camera-measure-stage">
        {!captured && <video ref={videoRef} muted playsInline autoPlay onCanPlay={() => setVideoReady(Boolean(videoRef.current?.videoWidth))} />}
        <canvas ref={canvasRef} hidden={!captured} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp} />
        {!captured && !videoReady && <div className="camera-measure-status" role="status">{cameraStatus === "requesting" ? "Requesting camera access…" : cameraStatus === "error" ? "Live preview unavailable" : "Starting camera…"}</div>}
      </div>
      {!captured ? <div className="camera-measure-start-actions"><button type="button" className="primary compact" disabled={!videoReady} onClick={capture}><Camera />Capture measurement frame</button><label className="secondary compact camera-photo-fallback"><Camera />Take or choose photo<input type="file" accept="image/*" capture="environment" onChange={(event) => { void importPhoto(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label></div> : <>
        <div className="camera-measure-controls"><button type="button" className={mode === "paint" ? "active" : ""} onClick={() => setMode("paint")}><Paintbrush />Paint area</button><button type="button" className={mode === "erase" ? "active" : ""} onClick={() => setMode("erase")}><Eraser />Erase</button><button type="button" className={mode === "scale" ? "active" : ""} onClick={() => setMode("scale")}><Ruler />Set scale</button><button type="button" onClick={clearSelection}><RotateCcw />Clear area</button></div>
        {mode !== "scale" && <label className="camera-measure-brush">Brush size<input type="range" min="12" max="160" value={brushSize} onChange={(event) => setBrushSize(Number(event.target.value))} /></label>}
        <div className="camera-measure-scale"><label>Known length<input type="number" min="0.1" step="0.1" value={knownLength} onChange={(event) => setKnownLength(event.target.value)} /></label><label>Unit<select value={unit} onChange={(event) => setUnit(event.target.value as "ft" | "m")}><option value="ft">feet</option><option value="m">metres</option></select></label></div>
        <p>Paint or erase the exact work area. Results update while you draw.</p><p>Choose Set scale, place two yellow points over the known length, and drag either point to adjust it.</p>
        <div className="camera-measure-live" aria-live="polite"><div><span>Selected area</span><strong>{measurement ? `${measurement.selectedPercent.toFixed(1)}%` : "Paint an area"}</strong></div><div><span>Estimated area</span><strong>{measurement?.estimatedArea ? `${measurement.estimatedArea.toFixed(1)} sq ${unit}` : "Set scale"}</strong></div><div><span>Estimated perimeter</span><strong>{measurement?.estimatedPerimeter ? `${measurement.estimatedPerimeter.toFixed(1)} ${unit}` : "Set scale"}</strong></div></div>
        <button type="button" className="primary compact" disabled={!measurement?.estimatedArea} onClick={close}><Check />Use this measurement</button>
      </>}
    </div></div>}
  </div>;
}
