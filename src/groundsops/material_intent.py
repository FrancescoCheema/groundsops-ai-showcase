import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialIntent:
    key: str
    instruction: str


# Descriptions are deliberately positive. Diffusion models such as FLUX have no
# negative prompt, so naming unwanted materials ("no gravel, no pavers") pushes the
# output towards them.
_INTENTS = (
    (
        re.compile(r"\b(grass|sod|lawn|turf)\b", re.IGNORECASE),
        MaterialIntent(
            "grass",
            "A freshly laid lawn of lush, well-watered, vibrant green sod: a continuous "
            "carpet of short, dense, evenly mown grass with subtle natural colour "
            "variation, covering the whole area.",
        ),
    ),
    (
        re.compile(r"\b(pavers?|interlock(?:ing)?|patio stones?)\b", re.IGNORECASE),
        MaterialIntent(
            "pavers",
            "Professionally installed interlocking concrete pavers with tight, realistic "
            "joints, consistent real-world scale and perspective-correct rows, laid flush "
            "with the surrounding ground.",
        ),
    ),
    (
        re.compile(r"\b(mulch|wood chips?|bark)\b", re.IGNORECASE),
        MaterialIntent(
            "mulch",
            "A fresh, evenly spread bed of natural brown wood-chip landscaping mulch with "
            "realistic bark texture, depth and colour variation.",
        ),
    ),
    (
        re.compile(r"\b(gravel|river rock|pea gravel|crushed rock)\b", re.IGNORECASE),
        MaterialIntent(
            "gravel",
            "A neatly raked bed of grey crushed landscaping gravel: small angular stones "
            "about 2 cm across, shown at true scale for the camera distance, with natural "
            "colour variation and depth.",
        ),
    ),
)


def resolve_material_intent(prompt: str) -> MaterialIntent | None:
    """Return the material the user asked for.

    When several materials are mentioned the last one wins, so "replace the lawn
    with cedar mulch" resolves to mulch rather than grass.
    """
    normalized = " ".join(prompt.split())
    best: tuple[int, MaterialIntent] | None = None
    for pattern, intent in _INTENTS:
        for match in pattern.finditer(normalized):
            if best is None or match.start() > best[0]:
                best = (match.start(), intent)
    return best[1] if best else None


def canonical_material_prompt(prompt: str) -> tuple[str, MaterialIntent | None]:
    request = " ".join(prompt.split()).strip()
    intent = resolve_material_intent(request)
    if intent is None:
        return request, None
    return f"{intent.instruction} {request}", intent
