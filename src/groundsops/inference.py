from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.evaluation import evaluate_generation
from groundsops.images import composite_edit
from groundsops.inference_providers import (
    ImageGenerationRequest,
    ImageGenerationResult,
    get_image_generation_provider,
)
from groundsops.models import GenerationEvaluation, GenerationJob, GenerationStatus, SiteCapture
from groundsops.storage import get_object_storage, tenant_storage_key


def _run_provider(
    job: GenerationJob,
    *,
    image_override: bytes | None = None,
    image_media_type_override: str | None = None,
    prompt_override: str | None = None,
) -> ImageGenerationResult:
    storage = get_object_storage()
    with SessionLocal() as db:
        capture = db.get(SiteCapture, job.capture_id)
        if capture is None:
            raise RuntimeError("Source capture no longer exists")
        image = image_override or storage.get(capture.storage_key)
        image_media_type = image_media_type_override or capture.media_type
    provider = get_image_generation_provider()
    if provider.name != job.provider:
        raise RuntimeError(f"Generation provider mismatch: expected {job.provider}")
    return provider.generate(
        ImageGenerationRequest(
            image=image,
            image_media_type=image_media_type,
            mask=storage.get(job.mask_storage_key),
            prompt=prompt_override or job.prompt,
        )
    )


def _retry_prompt(prompt: str, failure_reasons: list[str], attempt: int) -> str:
    """Strengthen the request after a rejected attempt.

    Retries always start again from the original photo, so the wording only adds
    positive emphasis on what the finished surface should look like.
    """
    emphasis = {
        "requested_grass_not_detected": (
            "Thick, uniformly green grass covers the entire area from edge to edge."
        ),
        "requested_pavers_not_detected": (
            "Interlocking concrete pavers cover the entire area from edge to edge."
        ),
        "requested_mulch_not_detected": (
            "Brown wood-chip mulch covers the entire area from edge to edge."
        ),
        "requested_gravel_not_detected": (
            "Landscaping gravel covers the entire area from edge to edge."
        ),
        "blank_or_flat_mask_output": (
            "Richly detailed, photorealistic natural texture throughout."
        ),
        "insufficient_masked_change": (
            "The new surface is complete and fully finished across the whole area."
        ),
    }
    additions = [emphasis[reason] for reason in failure_reasons if reason in emphasis]
    return " ".join([prompt.strip(), *additions]) if additions else prompt.strip()


def process_generation_job(job_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(GenerationJob, job_id)
        if job is None or job.status != GenerationStatus.QUEUED.value:
            return
        job.status = GenerationStatus.RUNNING.value
        job.started_at = datetime.now(UTC)
        db.commit()
        try:
            storage = get_object_storage()
            capture = db.get(SiteCapture, job.capture_id)
            if capture is None:
                raise RuntimeError("Source capture no longer exists")
            source_image = storage.get(capture.storage_key)
            retry_image = source_image
            retry_media_type = capture.media_type
            retry_prompt = job.prompt
            total_latency_ms = 0
            total_cost = Decimal("0")
            evaluation = None
            provider_result = None

            mask_image = storage.get(job.mask_storage_key)
            for attempt in range(1, settings.inference_max_attempts + 1):
                provider_result = _run_provider(
                    job,
                    image_override=retry_image,
                    image_media_type_override=retry_media_type,
                    prompt_override=retry_prompt,
                )
                total_latency_ms += provider_result.latency_ms
                total_cost += provider_result.estimated_cost_usd
                # Keep every pixel outside the selection identical to the original photo.
                provider_result = replace(
                    provider_result,
                    image=composite_edit(source_image, provider_result.image, mask_image),
                    media_type="image/png",
                )
                evaluation = evaluate_generation(
                    source_image,
                    provider_result.image,
                    mask_image,
                    prompt=job.prompt,
                    masked_change_min=settings.evaluation_masked_change_min,
                    protected_change_max=settings.evaluation_protected_change_max,
                    pixel_change_threshold=settings.evaluation_pixel_change_threshold,
                )
                if evaluation.passed or attempt == settings.inference_max_attempts:
                    break
                retry_prompt = _retry_prompt(job.prompt, evaluation.failure_reasons, attempt + 1)

            if provider_result is None or evaluation is None:
                raise RuntimeError("Inference provider returned no generation attempt")
            extension = "jpg" if "jpeg" in provider_result.media_type else "png"
            key = tenant_storage_key(
                job.organization_id, "generations", job.id, f"output.{extension}"
            )
            storage.put(key, provider_result.image, provider_result.media_type)
            job.output_storage_key = key
            job.output_media_type = provider_result.media_type
            job.provider_prediction_id = provider_result.prediction_id
            job.latency_ms = total_latency_ms
            job.estimated_cost_usd = total_cost.quantize(Decimal("0.0001"))
            db.add(
                GenerationEvaluation(
                    organization_id=job.organization_id,
                    generation_job_id=job.id,
                    evaluator_version=evaluation.evaluator_version,
                    dimensions_match=evaluation.dimensions_match,
                    masked_change_ratio=Decimal(str(evaluation.masked_change_ratio)),
                    protected_change_ratio=Decimal(str(evaluation.protected_change_ratio)),
                    masked_change_threshold=Decimal(str(evaluation.masked_change_threshold)),
                    protected_change_threshold=Decimal(str(evaluation.protected_change_threshold)),
                    pixel_change_threshold=Decimal(str(evaluation.pixel_change_threshold)),
                    passed=evaluation.passed,
                    failure_reasons=evaluation.failure_reasons,
                    evaluation_latency_ms=evaluation.evaluation_latency_ms,
                )
            )
            if evaluation.passed:
                job.status = GenerationStatus.SUCCEEDED.value
            else:
                job.status = GenerationStatus.FAILED.value
                reasons = ", ".join(evaluation.failure_reasons)
                job.error_message = (
                    "Generated concept failed quality checks after "
                    f"{settings.inference_max_attempts} attempts: {reasons}"
                )
        except Exception as exc:
            job.status = GenerationStatus.FAILED.value
            job.error_message = str(exc)[:2000]
        job.completed_at = datetime.now(UTC)
        db.commit()
