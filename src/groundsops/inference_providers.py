import base64
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from typing import Protocol

import httpx
from PIL import Image

from groundsops.config import Settings, get_settings
from groundsops.material_intent import resolve_material_intent


@dataclass(frozen=True)
class ImageGenerationRequest:
    image: bytes
    image_media_type: str
    mask: bytes
    prompt: str


@dataclass(frozen=True)
class ImageGenerationResult:
    image: bytes
    media_type: str
    prediction_id: str
    latency_ms: int
    estimated_cost_usd: Decimal


class ImageGenerationProvider(Protocol):
    name: str
    model_version: str

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...


SCENE_MATCHING = (
    "Photorealistic landscaping photograph, matching the existing scene's daylight, "
    "shadows, colour grading, camera angle, scale and perspective."
)


def landscaping_edit_prompt(user_prompt: str) -> str:
    """Describe the finished surface for FLUX Fill.

    FLUX Fill only regenerates the masked pixels, so the prompt should describe what
    belongs there, not give instructions about masks or list unwanted content.
    """
    request = " ".join(user_prompt.split()).strip().rstrip(".")
    material_intent = resolve_material_intent(request)
    parts = [material_intent.instruction] if material_intent else []
    if request:
        parts.append(f"{request}.")
    parts.append(SCENE_MATCHING)
    return " ".join(parts)


def _data_uri(data: bytes, media_type: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


RATE_LIMIT_MAX_ATTEMPTS = 4
RATE_LIMIT_MAX_WAIT_SECONDS = 30.0


def _retry_after_seconds(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("Retry-After", "10"))
    except ValueError:
        seconds = 10.0
    return min(max(seconds, 1.0), RATE_LIMIT_MAX_WAIT_SECONDS)


class ReplicateImageGenerationProvider:
    name = "replicate"

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not settings.replicate_api_token or not settings.replicate_model_version:
            raise RuntimeError("Replicate credentials or model version are not configured")
        self.settings = settings
        self.model_version = settings.replicate_model_version
        self._client = client
        self._sleep = sleep

    def _prediction_request(self, request: ImageGenerationRequest) -> tuple[str, dict]:
        model_input = {
            "image": _data_uri(request.image, request.image_media_type),
            "mask": _data_uri(request.mask, "image/png"),
            "prompt": landscaping_edit_prompt(request.prompt),
            "steps": 50,
            "guidance": self.settings.replicate_guidance,
            "prompt_upsampling": False,
            "safety_tolerance": 2,
            "output_format": "png",
        }
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.model_version):
            owner, model = self.model_version.split("/", maxsplit=1)
            endpoint = (
                f"https://api.replicate.com/v1/models/{owner}/{model}/predictions"
            )
            return endpoint, {"input": model_input}
        model_input["num_outputs"] = 1
        return (
            "https://api.replicate.com/v1/predictions",
            {"version": self.model_version, "input": model_input},
        )

    def _create_prediction(
        self, client: httpx.Client, endpoint: str, headers: dict, payload: dict
    ) -> httpx.Response:
        """Submit a prediction, waiting out Replicate rate limits.

        A 429 means the prediction was not created (and not billed), so it is
        safe to wait for ``Retry-After`` and submit again.
        """
        for attempt in range(1, RATE_LIMIT_MAX_ATTEMPTS + 1):
            response = client.post(endpoint, headers=headers, json=payload)
            if response.status_code != 429 or attempt == RATE_LIMIT_MAX_ATTEMPTS:
                response.raise_for_status()
                return response
            self._sleep(_retry_after_seconds(response))
        raise RuntimeError("unreachable")

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        headers = {
            "Authorization": f"Bearer {self.settings.replicate_api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }
        endpoint, payload = self._prediction_request(request)
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(self.settings.inference_timeout_seconds)
        )
        owns_client = self._client is None
        started = time.perf_counter()
        try:
            response = self._create_prediction(client, endpoint, headers, payload)
            prediction = response.json()
            while prediction.get("status") not in {
                "succeeded",
                "failed",
                "canceled",
                "aborted",
            }:
                self._sleep(2)
                status_url = prediction.get("urls", {}).get("get")
                if not status_url:
                    raise RuntimeError("Inference provider returned no status URL")
                response = client.get(status_url, headers=headers)
                response.raise_for_status()
                prediction = response.json()
            if prediction.get("status") != "succeeded":
                raise RuntimeError(prediction.get("error") or "Inference provider failed")
            output = prediction.get("output")
            output_url = output[0] if isinstance(output, list) else output
            if not output_url:
                raise RuntimeError("Inference provider returned no image")
            output_response = client.get(output_url)
            output_response.raise_for_status()
        finally:
            if owns_client:
                client.close()

        latency_ms = round((time.perf_counter() - started) * 1000)
        if "/models/" in endpoint:
            cost = Decimal(str(self.settings.replicate_cost_per_output_usd)).quantize(
                Decimal("0.0001")
            )
        else:
            cost = Decimal(
                str(latency_ms / 1000 * self.settings.replicate_cost_per_second_usd)
            ).quantize(Decimal("0.0001"))
        return ImageGenerationResult(
            image=output_response.content,
            media_type=output_response.headers.get("content-type", "image/png"),
            prediction_id=prediction["id"],
            latency_ms=latency_ms,
            estimated_cost_usd=cost,
        )


class MockImageGenerationProvider:
    """Deterministic, offline image editor for automated tests and demos."""

    name = "mock"
    model_version = "mock-landscape-v1"

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        started = time.perf_counter()
        with Image.open(BytesIO(request.image)) as source_image:
            source = source_image.convert("RGB")
        with Image.open(BytesIO(request.mask)) as mask_image:
            mask = mask_image.convert("L").resize(source.size)
        texture = Image.new("RGB", source.size)
        texture_pixels = texture.load()
        for y in range(source.height):
            for x in range(source.width):
                variation = ((x * 17 + y * 31) % 29) - 14
                texture_pixels[x, y] = (
                    max(0, min(255, 42 + variation // 3)),
                    max(0, min(255, 145 + variation)),
                    max(0, min(255, 74 + variation // 2)),
                )
        output = Image.composite(texture, source, mask)
        buffer = BytesIO()
        output.save(buffer, format="PNG")
        return ImageGenerationResult(
            image=buffer.getvalue(),
            media_type="image/png",
            prediction_id=f"mock-{time.time_ns()}",
            latency_ms=round((time.perf_counter() - started) * 1000),
            estimated_cost_usd=Decimal("0.0000"),
        )


def get_image_generation_provider(
    settings: Settings | None = None,
) -> ImageGenerationProvider:
    configured = settings or get_settings()
    if configured.inference_provider == "mock":
        return MockImageGenerationProvider()
    if configured.inference_provider == "replicate":
        return ReplicateImageGenerationProvider(configured)
    raise RuntimeError(
        f"Unsupported image generation provider: {configured.inference_provider}"
    )
