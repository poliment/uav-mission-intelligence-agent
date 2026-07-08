from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ZERO_USAGE = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}


@dataclass(frozen=True)
class ProviderPricing:
    provider_name: str
    model: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float
    currency: str = "USD"
    source_url: str = ""
    note: str = ""


def normalize_token_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(usage, dict):
        return dict(ZERO_USAGE)

    prompt_tokens = _int_or_zero(usage.get("prompt_tokens") or usage.get("input_tokens"))
    completion_tokens = _int_or_zero(usage.get("completion_tokens") or usage.get("output_tokens"))
    total_tokens = _int_or_zero(usage.get("total_tokens"))
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def estimate_cost(usage: dict[str, Any] | None, pricing: ProviderPricing) -> dict[str, Any]:
    normalized = normalize_token_usage(usage)
    input_cost = normalized["prompt_tokens"] / 1_000_000 * pricing.input_per_1m_tokens
    output_cost = normalized["completion_tokens"] / 1_000_000 * pricing.output_per_1m_tokens
    total_cost = input_cost + output_cost
    return {
        "currency": pricing.currency,
        "input_cost": round(input_cost, 8),
        "output_cost": round(output_cost, 8),
        "total_cost": round(total_cost, 8),
        "pricing_source": pricing.source_url or "configured",
        "pricing_note": pricing.note,
    }


def default_pricing_for(provider_name: str, model: str | None) -> ProviderPricing:
    normalized_provider = (provider_name or "offline").strip().lower()
    normalized_model = (model or "").strip() or ("rule-based" if normalized_provider == "offline" else "default")
    if normalized_provider in {"offline", "none", "rule-based"}:
        return ProviderPricing(
            provider_name="offline",
            model="rule-based",
            input_per_1m_tokens=0.0,
            output_per_1m_tokens=0.0,
            note="Offline rule-based execution does not use billable LLM tokens.",
        )
    if normalized_provider == "deepseek":
        return ProviderPricing(
            provider_name="deepseek",
            model=normalized_model,
            input_per_1m_tokens=0.0,
            output_per_1m_tokens=0.0,
            source_url="https://api-docs.deepseek.com/quick_start/pricing",
            note=(
                "Set explicit pricing before publishing live cost numbers; "
                "DeepSeek prices are provider-controlled and may change."
            ),
        )
    return ProviderPricing(
        provider_name=normalized_provider,
        model=normalized_model,
        input_per_1m_tokens=0.0,
        output_per_1m_tokens=0.0,
        note="No default pricing is configured for this provider/model.",
    )


def pricing_from_cli_spec(spec: str) -> ProviderPricing:
    parts = [part.strip() for part in spec.split(":")]
    if len(parts) != 4:
        raise ValueError("pricing spec must be PROVIDER/MODEL:INPUT_PER_1M:OUTPUT_PER_1M:CURRENCY")
    provider_model, input_price, output_price, currency = parts
    if "/" not in provider_model:
        raise ValueError("pricing spec provider/model must contain '/'")
    provider_name, model = [part.strip() for part in provider_model.split("/", 1)]
    return ProviderPricing(
        provider_name=provider_name,
        model=model,
        input_per_1m_tokens=float(input_price),
        output_per_1m_tokens=float(output_price),
        currency=currency or "USD",
        note="Configured from CLI pricing spec.",
    )


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
