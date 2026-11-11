import json
from decimal import Decimal

import httpx

from groundsops.config import Settings
from groundsops.inference_providers import (
    ImageGenerationRequest,
    ReplicateImageGenerationProvider,
    get_image_generation_provider,
    landscaping_edit_prompt,
)


def test_landscaping_prompt_describes_the_finished_surface_positively():
    prompt = landscaping_edit_prompt("Replace the lawn with cedar mulch.")

    assert prompt.startswith("A fresh, evenly spread bed of natural brown wood-chip")
    assert "Replace the lawn with cedar mulch." in prompt
    assert "matching the existing scene's daylight" in prompt
    lowered = prompt.lower()
    for banned in ("mask", "white", " no ", "never", "do not"):
        assert banned not in lowered


def test_replicate_provider_submits_and_downloads_an_edit():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "POST":
            payload = json.loads(request.content)
            assert payload["version"] == "pinned-version"
            assert payload["input"]["image"].startswith("data:image/png;base64,")
            assert payload["input"]["mask"].startswith("data:image/png;base64,")
            assert "matching the existing scene" in payload["input"]["prompt"]
            return httpx.Response(
                201,
                json={
                    "id": "prediction-1",
                    "status": "processing",
                    "urls": {"get": "https://api.replicate.com/v1/predictions/1"},
                },
            )
        if request.url.host == "api.replicate.com":
            return httpx.Response(
                200,
                json={
                    "id": "prediction-1",
                    "status": "succeeded",
                    "output": ["https://delivery.example/result.png"],
                },
            )
        return httpx.Response(
            200,
            content=b"generated-image",
            headers={"content-type": "image/png"},
        )

    settings = Settings(
        inference_provider="replicate",
        replicate_api_token="test-token",
        replicate_model_version="pinned-version",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = ReplicateImageGenerationProvider(
            settings,
            client=client,
            sleep=lambda _seconds: None,
        )
        result = provider.generate(
            ImageGenerationRequest(
                image=b"source-image",
                image_media_type="image/png",
                mask=b"mask-image",
                prompt="Install charcoal pavers.",
            )
        )

    assert result.image == b"generated-image"
    assert result.media_type == "image/png"
    assert result.prediction_id == "prediction-1"
    assert len(calls) == 3


def test_replicate_official_model_uses_model_endpoint_and_fixed_cost():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "POST":
            assert request.url.path == (
                "/v1/models/black-forest-labs/flux-fill-pro/predictions"
            )
            payload = json.loads(request.content)
            assert "version" not in payload
            assert "num_outputs" not in payload["input"]
            assert payload["input"]["steps"] == 50
            assert payload["input"]["guidance"] == 60
            assert payload["input"]["output_format"] == "png"
            assert payload["input"]["prompt_upsampling"] is False
            return httpx.Response(
                201,
                json={
                    "id": "official-prediction",
                    "status": "succeeded",
                    "output": "https://delivery.example/official.jpg",
                },
            )
        return httpx.Response(
            200,
            content=b"official-image",
            headers={"content-type": "image/jpeg"},
        )

    settings = Settings(
        inference_provider="replicate",
        replicate_api_token="test-token",
        replicate_model_version="black-forest-labs/flux-fill-pro",
        replicate_cost_per_output_usd=0.05,
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = ReplicateImageGenerationProvider(settings, client=client).generate(
            ImageGenerationRequest(
                image=b"source-image",
                image_media_type="image/png",
                mask=b"mask-image",
                prompt="Replace the lawn with drought-tolerant landscaping.",
            )
        )

    assert result.image == b"official-image"
    assert result.media_type == "image/jpeg"
    assert result.estimated_cost_usd == Decimal("0.0500")
    assert len(calls) == 2


def test_provider_factory_rejects_disabled_generation():
    settings = Settings(inference_provider="disabled")

    try:
        get_image_generation_provider(settings)
    except RuntimeError as exc:
        assert str(exc) == "Unsupported image generation provider: disabled"
    else:
        raise AssertionError("Disabled generation must not create a provider")


def _rate_limited_handler(failures: int, calls: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        posts = sum(1 for call in calls if call.method == "POST")
        if request.method == "POST" and posts <= failures:
            return httpx.Response(429, headers={"Retry-After": "7"}, json={"detail": "throttled"})
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "id": "prediction-2",
                    "status": "succeeded",
                    "output": "https://delivery.example/result.png",
                },
            )
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})

    return handler


def _rate_limit_provider(client: httpx.Client, sleeps: list[float]):
    settings = Settings(
        inference_provider="replicate",
        replicate_api_token="test-token",
        replicate_model_version="black-forest-labs/flux-fill-pro",
    )
    return ReplicateImageGenerationProvider(settings, client=client, sleep=sleeps.append)


def _edit_request() -> ImageGenerationRequest:
    return ImageGenerationRequest(
        image=b"source", image_media_type="image/png", mask=b"mask", prompt="Install sod."
    )


def test_replicate_provider_waits_out_rate_limits():
    calls: list[httpx.Request] = []
    sleeps: list[float] = []
    with httpx.Client(transport=httpx.MockTransport(_rate_limited_handler(2, calls))) as client:
        result = _rate_limit_provider(client, sleeps).generate(_edit_request())

    assert result.prediction_id == "prediction-2"
    assert sleeps == [7.0, 7.0]
    assert sum(1 for call in calls if call.method == "POST") == 3


def test_replicate_provider_gives_up_after_bounded_rate_limit_retries():
    calls: list[httpx.Request] = []
    sleeps: list[float] = []
    with httpx.Client(transport=httpx.MockTransport(_rate_limited_handler(10, calls))) as client:
        provider = _rate_limit_provider(client, sleeps)
        try:
            provider.generate(_edit_request())
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 429
        else:
            raise AssertionError("expected the rate limit to surface")

    assert len(sleeps) == 3
    assert sum(1 for call in calls if call.method == "POST") == 4
