from groundsops.inference_providers import landscaping_edit_prompt
from groundsops.material_intent import resolve_material_intent


def test_short_grass_prompts_expand_to_same_material_description():
    prompts = ["grass", "install sod", "make this a lawn", "replace it with turf"]

    for prompt in prompts:
        intent = resolve_material_intent(prompt)
        assert intent is not None
        assert intent.key == "grass"
        expanded = landscaping_edit_prompt(prompt)
        assert "lush, healthy natural green sod" in expanded
        assert prompt in expanded


def test_paver_prompt_has_distinct_description():
    expanded = landscaping_edit_prompt("charcoal pavers")

    assert "interlocking concrete pavers" in expanded
    assert "realistic joints" in expanded
    assert "charcoal pavers" in expanded


def test_last_mentioned_material_wins():
    assert resolve_material_intent("Replace the lawn with cedar mulch").key == "mulch"
    assert resolve_material_intent("Swap the gravel for pavers").key == "pavers"
    assert resolve_material_intent("Remove the mulch and lay sod").key == "grass"


def test_descriptions_never_name_other_materials():
    for prompt, others in {
        "grass": ("gravel", "paver", "mulch", "soil"),
        "pavers": ("grass", "gravel", "mulch", "soil"),
        "mulch": ("grass", "gravel", "paver"),
        "gravel": ("grass", "paver", "mulch"),
    }.items():
        description = resolve_material_intent(prompt).instruction.lower()
        for other in others:
            assert other not in description
