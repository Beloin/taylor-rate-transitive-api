from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.simulation import engine
from app.simulation.errors import (
    ERROR_HEADER,
    KIND_MESSAGES,
    ErrorKind,
)

logger = logging.getLogger(__name__)


class SimulationRoute(APIRoute):
    """APIRoute with error/latency/malformed simulation hooks.

    Everything is PER REQUEST, no state between requests:
      - explicityError: deterministic, bypasses rolls
      - errorProb: chance this request errors; kind drawn uniform,
        its group (BEFORE/AFTER) decides when it fires
      - latencyProb/latencyMs: delay before the controller
      - malformedProb/malformedSeed: mutate 2xx JSON responses
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            params = getattr(request.state, "sim_params", None)
            if params is None:
                params = engine.SimParams.from_request(request)

            await engine.apply_latency(params)

            kind = engine.roll_error_kind(params)
            if engine.should_fire_before(kind):
                return self._error_response(request, kind, KIND_MESSAGES[kind])

            response = await original(request)

            if kind is not None and not engine.should_fire_before(kind):
                return self._error_response(request, kind, KIND_MESSAGES[kind])

            if response.status_code < 300 and params.malformed_prob > 0:
                rng = engine.should_malform(params)
                if rng is not None:
                    response = self._malform_response(response, rng)

            return response

        return custom_handler

    def _error_response(
        self, request: Request, kind: ErrorKind, message: str
    ) -> JSONResponse:
        from app.simulation.errors import KIND_STATUS, build_error_body

        body = build_error_body(kind.value, message, request)
        headers = {ERROR_HEADER: kind.value}
        if kind is ErrorKind.RATE_LIMIT:
            headers["Retry-After"] = "5"
        return JSONResponse(
            content=body.model_dump(),
            status_code=KIND_STATUS[kind],
            headers=headers,
        )

    def _malform_response(self, response: Response, rng: Any) -> Response:
        try:
            payload = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response
        if isinstance(payload, dict):
            if "items" in payload:
                payload = engine.malform_page(payload, rng)
            else:
                payload = engine.malform_json(payload, rng)
        elif isinstance(payload, list):
            payload = [
                engine.malform_json(item, rng) if isinstance(item, dict) else item
                for item in payload
            ]
        return JSONResponse(
            content=payload,
            status_code=response.status_code,
            headers={ERROR_HEADER: ErrorKind.MALFORMED_RESPONSE.value},
        )