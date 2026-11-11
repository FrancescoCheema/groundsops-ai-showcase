"use client";

import { useEffect } from "react";

export function ServiceWorkerRegistration() {
  useEffect(() => {
    if ("serviceWorker" in navigator && window.location.protocol === "https:") {
      void navigator.serviceWorker.register("/sw.js");
    }
  }, []);
  return null;
}
