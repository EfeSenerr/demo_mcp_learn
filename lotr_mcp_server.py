"""MCP server that fetches Lord of the Rings quotes from The One API."""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field, ConfigDict

from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = "https://the-one-api.dev/v2"
API_KEY_ENV_VAR = "ONE_API_KEY"


class LotrQuote(BaseModel):
    """Structured representation of a LOTR quote."""

    model_config = ConfigDict(populate_by_name=True)

    quote_id: str = Field(alias="_id", description="Unique identifier of the quote")
    dialog: str = Field(description="Dialogue line from the quote")
    movie_id: str | None = Field(default=None, alias="movie", description="Movie identifier")
    character_id: str | None = Field(default=None, alias="character", description="Character identifier")


@dataclass
class AppContext:
    """Holds shared resources for the MCP server lifespan."""

    http_client: httpx.AsyncClient
    total_quotes: int | None = None


@asynccontextmanager
async def lifespan(_: FastMCP):
    """Creates shared HTTP client with The One API authorization."""

    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise RuntimeError(
            f"Environment variable '{API_KEY_ENV_VAR}' must be set with The One API access token."
        )

    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers, timeout=20.0) as client:
        yield AppContext(http_client=client)


mcp = FastMCP("LOTR Content Server", lifespan=lifespan)


async def _ensure_total_quotes(app_ctx: AppContext, ctx: Context[ServerSession, AppContext]) -> int:
    """Fetch and cache the total number of quotes exposed by the API."""

    if app_ctx.total_quotes is None:
        response = await app_ctx.http_client.get("/quote", params={"limit": 1})
        response.raise_for_status()
        data = response.json()
        app_ctx.total_quotes = int(data.get("total", 0))
        await ctx.debug(f"Cached LOTR quote total: {app_ctx.total_quotes}")

    if app_ctx.total_quotes <= 0:
        raise RuntimeError("Unable to determine total quote count from The One API.")

    return app_ctx.total_quotes


async def _fetch_random_quote(app_ctx: AppContext, ctx: Context[ServerSession, AppContext]) -> LotrQuote:
    """Retrieve a random quote by selecting a random offset."""

    total = await _ensure_total_quotes(app_ctx, ctx)
    random_offset = secrets.randbelow(total)
    params = {"limit": 1, "offset": random_offset}
    response = await app_ctx.http_client.get("/quote", params=params)
    response.raise_for_status()
    payload = response.json()
    docs = payload.get("docs", [])
    if not docs:
        raise RuntimeError("No quote returned from The One API.")

    return LotrQuote.model_validate(docs[0])


@mcp.tool()
async def get_lotr_quote(
    quote_id: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> LotrQuote:
    """Return a Lord of the Rings quote by id or randomly when no id is provided."""

    if ctx is None or ctx.request_context.lifespan_context is None:
        raise RuntimeError("Server context is not available.")

    app_ctx = ctx.request_context.lifespan_context

    if quote_id:
        response = await app_ctx.http_client.get(f"/quote/{quote_id}")
        response.raise_for_status()
        payload = response.json()
        docs = payload.get("docs", [])
        if not docs:
            raise RuntimeError(f"Quote with id '{quote_id}' was not found.")
        await ctx.info(f"Fetched LOTR quote with id {quote_id}.")
        return LotrQuote.model_validate(docs[0])

    quote = await _fetch_random_quote(app_ctx, ctx)
    await ctx.info(f"Fetched random LOTR quote (id={quote.quote_id}).")
    return quote


@mcp.tool()
async def describe_lotr_quote(
    quote: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Provide guidance on how a retrieved quote can inspire creative writing."""

    if not quote.strip():
        raise ValueError("Quote text must not be empty.")

    # This tool does not require API access but helps agents reason about usage.
    return (
        "Consider the tone, speaker, and context of the quote. Highlight emotional beats "
        "or conflicts and build poetic imagery that mirrors Middle-earth's lore."
    )


if __name__ == "__main__":
    mcp.run()
