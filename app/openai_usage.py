from __future__ import annotations

import logging
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# USD por 1M tokens. Si OpenAI cambia precios o aparece un modelo no listado,
# guardamos tokens y dejamos costo en 0 para no romper pedidos.
MODEL_PRICES_USD_PER_MILLION: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}


def openai_real_orders_enabled() -> bool:
    return _truthy(os.getenv("OPENAI_ENABLE_REAL_ORDERS", "false"))


def max_openai_calls_per_order() -> int:
    try:
        return max(0, int(os.getenv("MAX_OPENAI_CALLS_PER_ORDER", "3")))
    except (TypeError, ValueError):
        return 3


def calculate_openai_cost(model: str, input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
    model_key = (model or "").strip()
    if not model_key:
        return None

    prices = MODEL_PRICES_USD_PER_MILLION.get(model_key)
    if not prices:
        # Fallback razonable para aliases como gpt-4o-mini-YYYY-MM-DD.
        for known, known_prices in MODEL_PRICES_USD_PER_MILLION.items():
            if model_key.startswith(known):
                prices = known_prices
                break

    if not prices:
        return None

    try:
        in_tokens = int(input_tokens or 0)
        out_tokens = int(output_tokens or 0)
    except (TypeError, ValueError):
        return None

    cost = (in_tokens / 1_000_000) * prices["input"] + (out_tokens / 1_000_000) * prices["output"]
    return round(cost, 8)


def extract_usage_tokens(response: Any) -> tuple[int, int, int]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")

    def get_value(*names: str) -> int:
        for name in names:
            value = None
            if isinstance(usage, dict):
                value = usage.get(name)
            elif usage is not None:
                value = getattr(usage, name, None)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0
        return 0

    input_tokens = get_value("input_tokens", "prompt_tokens")
    output_tokens = get_value("output_tokens", "completion_tokens")
    total_tokens = get_value("total_tokens")
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


def _order_call_count(order_id: Optional[int]) -> int:
    if not order_id:
        return 0
    try:
        from app import db as database

        return int(database.get_openai_call_count(int(order_id)))
    except Exception:
        logger.debug("No se pudo leer contador OpenAI pedido #%s", order_id, exc_info=True)
        return 0


def assert_openai_call_allowed(order_id: Optional[int], call_type: str) -> None:
    if not openai_real_orders_enabled():
        logger.info(
            "OPENAI_CALL_SKIPPED_REAL_ORDERS_DISABLED order_id=%s call_type=%s",
            order_id,
            call_type,
        )
        raise RuntimeError(
            "OPENAI_ENABLE_REAL_ORDERS=false: llamadas reales a OpenAI bloqueadas. "
            "Usa JSON existente o JSON demo para pruebas sin costo."
        )

    if not order_id:
        return

    used = _order_call_count(order_id)
    limit = max_openai_calls_per_order()
    if limit and used >= limit:
        try:
            from app import db as database

            database.update_pedido_campos(
                int(order_id),
                generation_status="needs_admin_review",
                last_error_stage="openai_cost_guard",
                last_error_message=f"Pedido alcanzó MAX_OPENAI_CALLS_PER_ORDER={limit}.",
            )
        except Exception:
            logger.debug("No se pudo marcar bloqueo OpenAI pedido #%s", order_id, exc_info=True)
        logger.warning(
            "OPENAI_CALL_BLOCKED_MAX_CALLS order_id=%s call_type=%s used=%s limit=%s",
            order_id,
            call_type,
            used,
            limit,
        )
        raise RuntimeError(
            f"Pedido #{order_id} alcanzó el límite de {limit} llamadas OpenAI. "
            "Queda en revisión admin para evitar costos automáticos."
        )


def record_openai_usage(
    *,
    order_id: Optional[int],
    model: str,
    call_type: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    duration_seconds: Optional[float] = None,
    retry_count: int = 0,
    sections: Optional[list[str] | str] = None,
) -> Optional[float]:
    estimated_cost = calculate_openai_cost(model, input_tokens, output_tokens)
    if not order_id:
        return estimated_cost

    try:
        from app import db as database

        if isinstance(sections, list):
            sections_value = json.dumps(sections, ensure_ascii=False)
        else:
            sections_value = sections

        database.insert_openai_usage_log(
            order_id=int(order_id),
            model=model,
            call_type=call_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            duration_seconds=duration_seconds,
            retry_count=retry_count,
            sections=sections_value,
        )
    except Exception:
        logger.exception("No se pudo registrar uso OpenAI pedido #%s", order_id)
    return estimated_cost


def save_raw_openai_response(order_id: Optional[int], call_type: str, text: str) -> Optional[str]:
    if not order_id or not text:
        return None

    try:
        root = Path(__file__).resolve().parent.parent
        folder = root / "output" / "raw_openai"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        safe_call_type = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in call_type)
        path = folder / f"openai_raw_{int(order_id)}_{safe_call_type}_{stamp}.txt"
        path.write_text(text, encoding="utf-8")

        try:
            from app import db as database

            database.update_pedido_campos(int(order_id), raw_openai_path=str(path))
        except Exception:
            logger.debug("No se pudo guardar raw_openai_path en pedido #%s", order_id, exc_info=True)

        return str(path)
    except Exception:
        logger.exception("No se pudo guardar raw OpenAI pedido #%s", order_id)
        return None
