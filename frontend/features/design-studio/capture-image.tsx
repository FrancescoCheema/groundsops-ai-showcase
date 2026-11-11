"use client";

import { useEffect, useState } from "react";
import { ImageIcon } from "lucide-react";
import { captureBlob } from "@/lib/api";

export function CaptureImage({ captureId, token, alt }: { captureId: string; token: string; alt: string }) {
  const [url, setUrl] = useState<string>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setUrl(undefined);
    setFailed(false);
    captureBlob(captureId, token)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [captureId, token]);

  if (failed) return <div className="capture-loading capture-missing"><ImageIcon aria-hidden="true" /> Photo unavailable</div>;
  if (!url) return <div className="capture-loading"><ImageIcon aria-hidden="true" /> Loading preview</div>;
  // Blob URLs are authenticated runtime content and cannot use Next's optimizer.
  // eslint-disable-next-line @next/next/no-img-element
  return <img className="capture-image" src={url} alt={alt} />;
}
