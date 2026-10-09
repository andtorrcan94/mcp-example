"""Exercise REST and actual MCP transport without contacting an LLM provider."""

import asyncio
import os
from time import monotonic

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    base = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8022")
    async with httpx2.AsyncClient(timeout=60) as client:
        health = await client.get(base + "/health")
        health.raise_for_status()
        delay = health.json()["delay_seconds"]
        async with (
            streamable_http_client(base + "/mcp", http_client=client) as (
                read,
                write,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {
                "check_request_status",
                "check_request_status_with_failure",
                "check_request_without_information",
            }, names
            print("MCP handshake and discovery: 3 tools", flush=True)
            for tool, expected_error in [
                ("check_request_status", False),
                ("check_request_status_with_failure", True),
                ("check_request_without_information", False),
            ]:
                start = monotonic()
                result = await session.call_tool(tool, {"request_id": "TEST-001"})
                elapsed = monotonic() - start
                assert bool(result.is_error) == expected_error, result
                if tool != "check_request_without_information":
                    assert elapsed >= delay - 0.1, elapsed
                else:
                    assert elapsed < 5, elapsed
                print(
                    f"{tool}: {elapsed:.2f}s; isError={bool(result.is_error)}",
                    flush=True,
                )
            status = await client.get(base + "/api/requests/TEST-001/missing")
            status.raise_for_status()
            assert status.json()["found"] is False
            print("REST missing fixture: OK", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
