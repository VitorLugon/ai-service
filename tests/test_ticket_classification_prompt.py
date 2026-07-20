from app.prompts.ticket_classification import (
    PromptStrategy,
    build_ticket_classification_instructions,
)


def test_zero_shot_prompt_does_not_include_examples() -> None:
    instructions = build_ticket_classification_instructions(
        PromptStrategy.ZERO_SHOT,
    )

    assert "# Identidade" in instructions
    assert "# Regras" in instructions
    assert "# Exemplos" not in instructions
    assert "<expected_output" not in instructions


def test_one_shot_prompt_includes_one_example() -> None:
    instructions = build_ticket_classification_instructions(
        PromptStrategy.ONE_SHOT,
    )

    assert "# Exemplos" in instructions
    assert instructions.count("<ticket id=") == 1
    assert instructions.count("<expected_output id=") == 1


def test_few_shot_prompt_includes_multiple_examples() -> None:
    instructions = build_ticket_classification_instructions(
        PromptStrategy.FEW_SHOT,
    )

    assert "# Exemplos" in instructions
    assert instructions.count("<ticket id=") == 3
    assert instructions.count("<expected_output id=") == 3


def test_all_prompts_define_allowed_labels() -> None:
    for strategy in PromptStrategy:
        instructions = build_ticket_classification_instructions(strategy)

        assert "acesso_e_autenticacao" in instructions
        assert "erro_tecnico" in instructions
        assert "cobranca" in instructions
        assert "duvida_de_uso" in instructions
        assert "solicitacao" in instructions
        assert "outro" in instructions

        assert "baixa" in instructions
        assert "media" in instructions
        assert "alta" in instructions
        assert "critica" in instructions
