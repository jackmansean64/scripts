from enum import StrEnum

MARKUP = 1
USD_TO_CAD_CONVERSION_RATE = 1.34

class ModelName(StrEnum):
    SONNET_3_5 = "SONNET_3_5"
    HAIKU_3_5 = "HAIKU_3_5"

SONNET_3_5_PROMPT_COST_PER_THOUSAND_TOKENS = 0.003
SONNET_3_5_COMPLETION_COST_PER_THOUSAND_TOKENS = 0.015

HAIKU_3_5_PROMPT_COST_PER_THOUSAND_TOKENS = 0.0008
HAIKU_3_5_COMPLETION_COST_PER_THOUSAND_TOKENS = 0.004

PROMPT_COST_PER_THOUSAND_TOKENS = HAIKU_3_5_PROMPT_COST_PER_THOUSAND_TOKENS
COMPLETION_COST_PER_THOUSAND_TOKENS = HAIKU_3_5_COMPLETION_COST_PER_THOUSAND_TOKENS


def calculate_total_prompt_cost(prompt_tokens: int, completion_tokens: int, model: ModelName) -> float:
    return calculate_prompt_cost(prompt_tokens, model) + calculate_completion_cost(completion_tokens, model)


def calculate_prompt_cost(prompt_tokens: int, model: ModelName) -> float:
    """
    Calculates the cost of the prompt tokens in Canadian dollars.
    Pricing obtained from https://aws.amazon.com/bedrock/pricing/
    """
    match model:
        case ModelName.SONNET_3_5:
            prompt_cost_per_thousand_tokens = SONNET_3_5_PROMPT_COST_PER_THOUSAND_TOKENS
        case ModelName.HAIKU_3_5:
            prompt_cost_per_thousand_tokens = HAIKU_3_5_PROMPT_COST_PER_THOUSAND_TOKENS
        case _:
            prompt_cost_per_thousand_tokens = 0


    prompt_cost_usd = prompt_tokens * prompt_cost_per_thousand_tokens / 1000
    prompt_cost_cad = prompt_cost_usd * USD_TO_CAD_CONVERSION_RATE * MARKUP
    return prompt_cost_cad


def calculate_completion_cost(completion_tokens: int, model: ModelName) -> float:
    """
    Calculates the cost of the completion tokens in Canadian dollars.
    Pricing obtained from https://aws.amazon.com/bedrock/pricing/
    """
    match model:
        case ModelName.SONNET_3_5:
            completion_cost_per_thousand_tokens = SONNET_3_5_COMPLETION_COST_PER_THOUSAND_TOKENS
        case ModelName.HAIKU_3_5:
            completion_cost_per_thousand_tokens = HAIKU_3_5_COMPLETION_COST_PER_THOUSAND_TOKENS
        case _:
            completion_cost_per_thousand_tokens = 0

    completion_cost_usd = (
        completion_tokens * completion_cost_per_thousand_tokens / 1000
    )
    completion_cost_cad = (
            completion_cost_usd * USD_TO_CAD_CONVERSION_RATE * MARKUP
    )
    return completion_cost_cad
