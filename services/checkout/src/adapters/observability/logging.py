"""Logging estruturado em JSON com saga_id obrigatorio (Principio V da constituicao)."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any, cast

import structlog

_saga_id_ctx: ContextVar[str | None] = ContextVar("saga_id", default=None)


def bind_saga_id(saga_id: str) -> None:
    _saga_id_ctx.set(saga_id)
    structlog.contextvars.bind_contextvars(saga_id=saga_id)


def clear_saga_id() -> None:
    _saga_id_ctx.set(None)
    structlog.contextvars.unbind_contextvars("saga_id")


def _inject_saga_id(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    saga_id = _saga_id_ctx.get()
    if saga_id is not None and "saga_id" not in event_dict:
        event_dict["saga_id"] = saga_id
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    """Configura structlog para emitir JSON em stdout, sempre com saga_id quando disponivel."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_saga_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    return cast(structlog.typing.FilteringBoundLogger, structlog.get_logger(name))
