from __future__ import annotations

import time
from typing import Any, Dict

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .adapter import build_responses_request, to_chat_completions, to_completions
from .config import settings
from .logging_setup import configure_logging, get_logger
from .streaming import stream_chat_completions, stream_completions

configure_logging(settings.log_level)
logger = get_logger()

app = FastAPI(title="OpenAI Responses Adapter", version="0.1.0")


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


def _build_upstream_headers(request: Request) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    headers.update(settings.auth_headers())

    if not settings.upstream_api_key and settings.pass_through_auth:
        incoming = request.headers.get(settings.upstream_api_key_header)
        if incoming:
            headers[settings.upstream_api_key_header] = incoming

    return headers


async def _proxy(payload: Dict[str, Any], stream: bool, transform: str, request: Request) -> Any:
    upstream_url = settings.upstream_responses_url()
    headers = _build_upstream_headers(request)

    timeout = httpx.Timeout(settings.request_timeout)

    if stream:
        client = httpx.AsyncClient(timeout=timeout)
        start = time.time()
        try:
            req = client.build_request("POST", upstream_url, json=payload, headers=headers)
            response = await client.send(req, stream=True)
        except httpx.RequestError as exc:
            await client.aclose()
            logger.error("upstream.request_error", error=str(exc))
            return JSONResponse(status_code=502, content={"error": "upstream_unreachable"})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "upstream.response",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code >= 400:
            data = await response.aread()
            await response.aclose()
            await client.aclose()
            return JSONResponse(status_code=response.status_code, content={"error": data.decode("utf-8", "ignore")})

        async def stream_lines() -> Any:
            try:
                async for line in response.aiter_lines():
                    yield line
            finally:
                await response.aclose()
                await client.aclose()

        if transform == "chat":
            return StreamingResponse(stream_chat_completions(stream_lines()), media_type="text/event-stream")
        return StreamingResponse(stream_completions(stream_lines()), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=timeout) as client:
        start = time.time()
        try:
            response = await client.post(upstream_url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            logger.error("upstream.request_error", error=str(exc))
            return JSONResponse(status_code=502, content={"error": "upstream_unreachable"})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "upstream.response",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code >= 400:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})

        body = response.json()
        if transform == "chat":
            return JSONResponse(content=to_chat_completions(body))
        return JSONResponse(content=to_completions(body))


async def _proxy_passthrough(payload: Dict[str, Any], stream: bool, request: Request) -> Any:
    upstream_url = settings.upstream_responses_url()
    headers = _build_upstream_headers(request)

    timeout = httpx.Timeout(settings.request_timeout)

    if stream:
        client = httpx.AsyncClient(timeout=timeout)
        start = time.time()
        try:
            req = client.build_request("POST", upstream_url, json=payload, headers=headers)
            response = await client.send(req, stream=True)
        except httpx.RequestError as exc:
            await client.aclose()
            logger.error("upstream.request_error", error=str(exc))
            return JSONResponse(status_code=502, content={"error": "upstream_unreachable"})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "upstream.response",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code >= 400:
            data = await response.aread()
            await response.aclose()
            await client.aclose()
            return JSONResponse(status_code=response.status_code, content={"error": data.decode("utf-8", "ignore")})

        async def stream_bytes() -> Any:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(stream_bytes(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=timeout) as client:
        start = time.time()
        try:
            response = await client.post(upstream_url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            logger.error("upstream.request_error", error=str(exc))
            return JSONResponse(status_code=502, content={"error": "upstream_unreachable"})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "upstream.response",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code >= 400:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})

        return JSONResponse(content=response.json())


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
    payload = await request.json()
    model_map = settings.resolved_model_map()
    responses_payload = build_responses_request(payload, model_map)
    return await _proxy(responses_payload, bool(payload.get("stream")), "chat", request)


@app.post("/v1/completions")
async def completions(request: Request) -> Any:
    payload = await request.json()
    model_map = settings.resolved_model_map()
    responses_payload = build_responses_request(payload, model_map)
    return await _proxy(responses_payload, bool(payload.get("stream")), "completions", request)


@app.post("/v1/responses")
async def responses(request: Request) -> Any:
    payload = await request.json()
    return await _proxy_passthrough(payload, bool(payload.get("stream")), request)


@app.get("/v1/models")
async def models(request: Request) -> Any:
    upstream_url = settings.upstream_models_url()
    headers = _build_upstream_headers(request)
    timeout = httpx.Timeout(settings.request_timeout)

    async with httpx.AsyncClient(timeout=timeout) as client:
        start = time.time()
        try:
            response = await client.get(upstream_url, headers=headers, params=request.query_params)
        except httpx.RequestError as exc:
            logger.error("upstream.request_error", error=str(exc))
            return JSONResponse(status_code=502, content={"error": "upstream_unreachable"})

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "upstream.response",
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        if response.status_code >= 400:
            return JSONResponse(status_code=response.status_code, content={"error": response.text})

        return JSONResponse(content=response.json())
