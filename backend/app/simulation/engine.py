from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request

from app.simulation.errors import AFTER_KINDS, BEFORE_KINDS, ErrorKind


@dataclass
class SimParams:
    transitive_errors: bool = False
    error_prob: float = 0.0
    explicit_error: ErrorKind | None = None
    latency_prob: float = 0.0
    latency_ms: int = 1000
    malformed_prob: float = 0.0
    malformed_seed: int = -1

    @classmethod
    def from_request(cls, request: Request) -> SimParams:
        q = request.query_params

        def f(name: str, default: float) -> float:
            raw = q.get(name)
            if raw is None:
                return default
            try:
                return min(max(float(raw), 0.0), 1.0)
            except ValueError:
                return default

        def i(name: str, default: int) -> int:
            raw = q.get(name)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError:
                return default

        explicit_raw = q.get("explicityError")
        explicit = None
        if explicit_raw is not None:
            try:
                explicit = ErrorKind(explicit_raw)
            except ValueError:
                explicit = None

        return cls(
            transitive_errors=q.get("transitiveErrors", "false").lower() == "true",
            error_prob=f("errorProb", 0.0),
            explicit_error=explicit,
            latency_prob=f("latencyProb", 0.0),
            latency_ms=max(i("latencyMs", 1000), 0),
            malformed_prob=f("malformedProb", 0.0),
            malformed_seed=i("malformedSeed", -1),
        )


def simulation_params(
    transitiveErrors: bool = False,
    errorProb: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    explicityError: ErrorKind | None = None,
    latencyProb: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    latencyMs: Annotated[int, Query(ge=0)] = 1000,
    malformedProb: Annotated[float, Query(ge=0.0, le=1.0)] = 0.0,
    malformedSeed: int = -1,
) -> SimParams:
    """OpenAPI-documented dependency computing SimParams from query params."""
    return SimParams(
        transitive_errors=transitiveErrors,
        error_prob=errorProb,
        explicit_error=explicityError,
        latency_prob=latencyProb,
        latency_ms=latencyMs,
        malformed_prob=malformedProb,
        malformed_seed=malformedSeed,
    )


async def simulation_params_dependency(
    request: Request,
    params: Annotated[SimParams, Depends(simulation_params)],
) -> SimParams:
    """Router-level dependency: documents the params in OpenAPI and
    stores the computed SimParams on request.state for SimulationRoute."""
    request.state.sim_params = params
    return params


def roll_error_kind(params: SimParams) -> ErrorKind | None:
    """Single probability roll per request. No state, nothing sticky.

    errorProb is the chance THIS request errors, always applied. When it
    hits, explicityError (if set) pins the kind; otherwise a random kind
    is drawn. transitiveErrors only enables that kind of error; it never
    forces anything and holds no state.
    """
    if params.error_prob <= 0 or random.random() >= params.error_prob:
        return None
    if params.explicit_error is not None:
        return params.explicit_error
    return random.choice([*BEFORE_KINDS, *AFTER_KINDS])


def should_fire_before(kind: ErrorKind | None) -> bool:
    """True when the drawn kind belongs to the BEFORE group."""
    return kind is not None and kind in BEFORE_KINDS


async def apply_latency(params: SimParams) -> None:
    if params.latency_prob > 0 and random.random() < params.latency_prob:
        await asyncio.sleep(params.latency_ms / 1000)


def should_malform(params: SimParams) -> random.Random | None:
    """Return an rng when this response should be malformed, else None."""
    if params.malformed_prob <= 0:
        return None
    if random.random() >= params.malformed_prob:
        return None
    if params.malformed_seed != -1:
        return random.Random(params.malformed_seed)
    return random.Random()


def malform_json(payload: dict, rng: random.Random) -> dict:
    """Mutate a JSON payload: drop a field, change a type, or corrupt a value."""
    if not payload:
        return payload
    key = rng.choice(list(payload.keys()))
    mutation = rng.choice(["drop", "type", "corrupt"])
    result = dict(payload)
    if mutation == "drop":
        result.pop(key)
    elif mutation == "type":
        original = result[key]
        if isinstance(original, str):
            result[key] = rng.choice(
                [123, 1.5, True, None, [original], {"x": original}]
            )
        else:
            result[key] = "corrupted-string"
    else:
        result[key] = "�corrupted�"
    return result


def malform_page(payload: dict, rng: random.Random) -> dict:
    """Mutation variant for paginated responses: corrupts nested items."""
    items = payload.get("items")
    if isinstance(items, list) and items:
        result = dict(payload)
        mutated = [malform_json(item, rng) if isinstance(item, dict) else item for item in items]
        result["items"] = mutated
        return result
    return malform_json(payload, rng)