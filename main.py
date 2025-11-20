"""Multi-agent LOTR poetry demo built with Microsoft Agent Framework.

Setup:
1. Install dependencies (recommended: `uv sync` or `pip install -e .`).
2. Export `GITHUB_TOKEN` for the GitHub Models endpoint and `ONE_API_KEY` for The One API.
3. Run `python agent_framework.py` to watch the poet/critic ping-pong with the MCP server.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Literal

from agent_framework import ChatAgent, MCPStdioTool, ToolProtocol
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# To authenticate with the model you will need to generate a personal access token (PAT) in your GitHub settings.
# Create your PAT token by following instructions here: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
openaiClient = AsyncOpenAI(
    base_url = "https://models.github.ai/inference",
    api_key = os.environ["GITHUB_TOKEN"],
    default_query = {
        "api-version": "2024-08-01-preview",
    },
)


POET_AGENT_NAME = "LOTR Poet"
CRITIC_AGENT_NAME = "LOTR Poem Expert"

PING_PONG_LIMIT = int(os.getenv("PING_PONG_LIMIT", "5"))

INITIAL_TASK = (
    "Fetch a Lord of the Rings quote using your MCP tool, summarize it in one sentence, "
    "and craft a concise four-line poem that reflects the quote's mood."
)

POET_INSTRUCTIONS = """
You are a lyrical poet from Middle-earth.
- Always call the MCP tool `lotr_content` (get_lotr_quote) before drafting a poem.
- Paraphrase the quote in one sentence before the poem so collaborators know the context.
- Compose exactly four poetic lines referencing characters, places, or emotions from the quote.
- Close with `STATUS: READY` when you believe the poem satisfies the review criteria or `STATUS: REVISION` when asking for more feedback.
""".strip()

CRITIC_INSTRUCTIONS = """
You are a meticulous Loremaster ensuring LOTR poems honor the lore.
- Inspect the provided paraphrase and poem for accuracy, line count (exactly four), and tone.
- Respond with `APPROVED: <short explanation>` if everything looks great.
- Otherwise respond with `REVISE: <actionable feedback>` describing what must change (line count, lore, rhyme, etc.).
""".strip()

def create_mcp_tools() -> list[ToolProtocol]:
    server_path = Path(__file__).with_name("lotr_mcp_server.py")
    return [
        MCPStdioTool(
            name="lotr_content",
            description="Fetches canonical Lord of the Rings quotes via The One API",
            command=sys.executable,
            args=[
                str(server_path),
            ],
        ),
    ]


def _chunk_contains_tool_calls(chunk: object) -> bool:
    return (
        chunk.raw_representation
        and chunk.raw_representation.raw_representation
        and hasattr(chunk.raw_representation.raw_representation, "choices")
        and chunk.raw_representation.raw_representation.choices is not None
        and len(chunk.raw_representation.raw_representation.choices) > 0
        and hasattr(chunk.raw_representation.raw_representation.choices[0], "delta")
        and hasattr(chunk.raw_representation.raw_representation.choices[0].delta, "tool_calls")
        and chunk.raw_representation.raw_representation.choices[0].delta.tool_calls is not None
        and len(chunk.raw_representation.raw_representation.choices[0].delta.tool_calls) > 0
    )


async def stream_agent_response(
    agent: ChatAgent,
    thread,
    message: str,
    speaker: str,
    log_tool_calls: bool,
) -> str:
    print(f"\n[{speaker}] <- {message}")
    collected: list[str] = []
    async for chunk in agent.run_stream([message], thread=thread):
        if chunk.text:
            print(chunk.text, end="", flush=True)
            collected.append(chunk.text)
        elif log_tool_calls and _chunk_contains_tool_calls(chunk):
            tool_calls = [
                call.function.name
                for call in chunk.raw_representation.raw_representation.choices[0].delta.tool_calls
                if call.function.name is not None
            ]
            if tool_calls:
                print("\nTool calls:", tool_calls)
    print("\n")
    return "".join(collected).strip()


async def run_ping_pong(
    poet: ChatAgent,
    critic: ChatAgent,
    initial_task: str,
    limit: int,
) -> None:
    poet_thread = poet.get_new_thread()
    critic_thread = critic.get_new_thread()

    next_task = initial_task

    for turn in range(1, limit + 1):
        poem_output = await stream_agent_response(
            poet,
            poet_thread,
            next_task,
            speaker=POET_AGENT_NAME,
            log_tool_calls=True,
        )

        review_prompt = (
            "Please evaluate the paraphrase and poem below. Confirm APPROVED or provide REVISE "
            "feedback.\n\n" + poem_output
        )
        critic_output = await stream_agent_response(
            critic,
            critic_thread,
            review_prompt,
            speaker=CRITIC_AGENT_NAME,
            log_tool_calls=False,
        )

        verdict: Literal["approved", "revise"]
        normalized = critic_output.strip().lower()
        if normalized.startswith("approved"):
            verdict = "approved"
        elif normalized.startswith("revise"):
            verdict = "revise"
        else:
            print("Unrecognized verdict, defaulting to REVISE queue.")
            verdict = "revise"

        if verdict == "approved":
            print(f"\n✅ Poem approved after {turn} ping-pong cycle(s).")
            return

        next_task = (
            "Incorporate the critic feedback below. Keep the poem to four lines, reuse the "
            "retrieved quote context, and respond with STATUS: REVISION or STATUS: READY.\n\n"
            f"Feedback: {critic_output}\n\nPrevious poem draft:\n{poem_output}"
        )

    print("\n⚠️ Ping-pong limit reached without approval. Please review the latest draft manually.")

async def main() -> None:
    chat_client = OpenAIChatClient(
        async_client=openaiClient,
        model_id="openai/gpt-4.1",
    )

    async with (
        ChatAgent(
            chat_client=chat_client,
            instructions=POET_INSTRUCTIONS,
            temperature=0.8,
            top_p=0.95,
            name=POET_AGENT_NAME,
            tools=create_mcp_tools(),
        ) as poet,
        ChatAgent(
            chat_client=chat_client,
            instructions=CRITIC_INSTRUCTIONS,
            temperature=0.2,
            top_p=0.8,
            name=CRITIC_AGENT_NAME,
        ) as critic,
    ):
        await run_ping_pong(
            poet=poet,
            critic=critic,
            initial_task=INITIAL_TASK,
            limit=PING_PONG_LIMIT,
        )

        print("\n--- Collaboration complete ---")

    # Give additional time for all async cleanup to complete
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Program finished.")
