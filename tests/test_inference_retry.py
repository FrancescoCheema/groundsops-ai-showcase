from groundsops.inference import _retry_prompt


def test_grass_failure_adds_positive_emphasis():
    prompt = _retry_prompt("grass", ["requested_grass_not_detected"], 2)

    assert prompt.startswith("grass ")
    assert "Thick, uniformly green grass covers the entire area" in prompt
    assert "rejected" not in prompt.lower()


def test_retry_combines_relevant_emphasis_and_ignores_others():
    prompt = _retry_prompt(
        "charcoal pavers",
        ["requested_pavers_not_detected", "excessive_protected_change"],
        3,
    )

    assert "Interlocking concrete pavers cover the entire area" in prompt
    assert "mask" not in prompt.lower()


def test_retry_without_known_reasons_keeps_original_prompt():
    assert _retry_prompt("  gravel  ", ["dimension_mismatch"], 2) == "gravel"
