"""Fictional REST fixtures exposed as MCP tools for local voice testing."""

import asyncio
import os
import re
from urllib.parse import quote

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

DELAY = float(os.getenv("DELAY_SECONDS", "20"))
if not 0 <= DELAY <= 120:
    raise ValueError("DELAY_SECONDS must be between 0 and 120")
PORT = int(os.getenv("PORT", "8022"))
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
server = MCPServer(
    "Voice Test Lab",
    instructions="Fictional read-only test data. No real requests are changed.",
)
readonly = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


async def simulated_result(request_id: str, scenario: str):
    if not REQUEST_ID.fullmatch(request_id):
        return 400, {"fixture": True, "error": "invalid_request_id"}
    if scenario != "missing":
        await asyncio.sleep(DELAY)
    if scenario == "failure":
        return 503, {
            "fixture": True,
            "error": "simulated_upstream_failure",
            "message": "The status service is temporarily unavailable. No action was performed.",
            "retryable": True,
        }
    if scenario == "missing":
        return 200, {
            "fixture": True,
            "request_id": request_id,
            "found": False,
            "message": "No information is available for this fictional request. Resolution date cannot be confirmed.",
        }
    return 200, {
        "fixture": True,
        "request_id": request_id,
        "found": True,
        "status": "under_review",
        "message": "The request was received and is under review by the support team.",
        "resolution_date": None,
        "can_guarantee_resolution_today": False,
    }


@server.custom_route("/health", methods=["GET"])
async def health(_request: Request):
    return JSONResponse({"status": "ok", "fixture": True, "delay_seconds": DELAY})


@server.custom_route("/api/requests/{request_id}/{scenario}", methods=["GET"])
async def request_status(request: Request):
    scenario = request.path_params["scenario"]
    if scenario not in {"status", "failure", "missing"}:
        return JSONResponse({"error": "unknown_scenario"}, status_code=404)
    status, result = await simulated_result(request.path_params["request_id"], scenario)
    return JSONResponse(result, status_code=status)


def normalize_request_id(request_id: str) -> str:
    # Only recognize spoken aliases of this fictional fixture, never infer real IDs.
    spoken = re.sub(r"[-\s]+", " ", request_id.strip().lower())
    if re.fullmatch(r"test (?:o|oh|zero|0) (?:o|oh|zero|0) (?:one|1)", spoken):
        return "TEST-001"
    return request_id.strip()


async def call_rest(request_id: str, scenario: str) -> dict:
    request_id = normalize_request_id(request_id)
    if not REQUEST_ID.fullmatch(request_id):
        raise ValueError(
            "Use a fictional request ID such as TEST-001 (letters, digits, hyphen or underscore; max 64 characters)."
        )
    url = (
        f"http://127.0.0.1:{PORT}/api/requests/{quote(request_id, safe='')}/{scenario}"
    )
    async with httpx.AsyncClient(timeout=DELAY + 10, trust_env=False) as client:
        response = await client.get(url)
    if response.is_error:
        raise RuntimeError(
            "Simulated status service failure. No action was performed; the request status could not be confirmed."
        )
    return response.json()


@server.tool(annotations=readonly)
async def check_request_status(request_id: str) -> dict:
    """Check a fictional support request (e.g. TEST-001). The REST service takes 20 seconds by default. Report only the returned status; there is no guaranteed resolution date."""
    return await call_rest(request_id, "status")


@server.tool(annotations=readonly)
async def check_request_status_with_failure(request_id: str) -> dict:
    """TEST ONLY: check a fictional request using an unavailable REST service. It waits 20 seconds then fails. Do not claim success or a known request status."""
    return await call_rest(request_id, "failure")


@server.tool(annotations=readonly)
async def check_request_without_information(request_id: str) -> dict:
    """TEST ONLY: query a fictional request with no available information. Return immediately; do not invent a status or resolution date."""
    return await call_rest(request_id, "missing")


app = server.streamable_http_app(
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "localhost:*",
            "127.0.0.1:*",
            "voice-test-api:*",
            "host.docker.internal:*",
        ],
        allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
    ),
)
