# ADR 0002: Separate photo rendering, estimation, and live AR

## Status

Accepted.

## Context

The product should let a customer point a phone at an outdoor space, preview grass, pavers, or other materials, and see nearby material options. This description contains three technically different problems:

1. editing a captured image while preserving scene structure
2. estimating physical quantities and matching products
3. tracking a surface and rendering it continuously in a moving camera view

Treating them as one AI call would produce unstable visuals and misleading estimates.

## Decision

Deliver the capability incrementally:

- First, build still-image capture, segmentation, mask correction, and controlled image generation.
- Estimate quantities only from explicit measurements or supported depth/multi-view information, with visible confidence and assumptions.
- Match materials through an authorized, freshness-aware product catalog.
- Prototype live AR only after the captured-photo workflow demonstrates real customer value.

The backend will keep vendor-neutral interfaces for segmentation, generation, measurement, geocoding, distance, and provider catalog services. Original images, masks, outputs, prompts, models, and feedback remain independently versioned.

## Consequences

- The first visual feature can be built and evaluated without committing to a native mobile application.
- Generated images cannot be presented as exact construction outcomes.
- A single photo cannot silently produce a construction-grade material quantity.
- Live AR requires a later mobile/AR workstream rather than only an LLM or diffusion API.
- User data improves the system only through consented, de-identified, versioned datasets and controlled evaluation.

