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

# Mystery-solving scenario
SAURON_AGENT_NAME = "Sauron the Mystery Weaver"
GANDALF_AGENT_NAME = "Gandalf the Grey"
BILBO_AGENT_NAME = "Bilbo Baggins"

MYSTERY_MAX_TURNS = int(os.getenv("MYSTERY_MAX_TURNS", "8"))


def load_agent_instructions(agent_file: str) -> str:
    """Load agent instructions from markdown file in .github/agents/"""
    agent_path = Path(__file__).parent / ".github" / "agents" / agent_file
    
    if not agent_path.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_path}")
    
    content = agent_path.read_text(encoding="utf-8")
    
    # Convert markdown to instructions format
    instructions = []
    
    # Extract role and personality
    if "## Role" in content:
        role_section = content.split("## Role")[1].split("##")[0].strip()
        instructions.append(f"You are {role_section}")
    
    # Extract personality traits
    if "## Personality" in content:
        personality = content.split("## Personality")[1].split("##")[0].strip()
        instructions.append("\nPersonality traits:")
        instructions.append(personality)
    
    # Extract investigation approach or abilities
    if "## Investigation Approach" in content:
        approach = content.split("## Investigation Approach")[1].split("##")[0].strip()
        instructions.append("\nInvestigation approach:")
        instructions.append(approach)
    elif "## Investigation Style" in content:
        style = content.split("## Investigation Style")[1].split("##")[0].strip()
        instructions.append("\nInvestigation style:")
        instructions.append(style)
    elif "## Abilities" in content:
        abilities = content.split("## Abilities")[1].split("##")[0].strip()
        instructions.append("\nAbilities:")
        instructions.append(abilities)
    
    # Extract key phrases
    if "## Key Phrases" in content:
        phrases = content.split("## Key Phrases")[1].split("##")[0].strip()
        instructions.append("\nKey phrases to use:")
        instructions.append(phrases)
    
    # Extract strengths
    if "## Strengths" in content:
        strengths = content.split("## Strengths")[1].split("##")[0].strip()
        instructions.append("\nYour strengths:")
        instructions.append(strengths)
    
    return "\n".join(instructions)


# Load instructions from markdown files
SAURON_INSTRUCTIONS = load_agent_instructions("Sauron.md")
GANDALF_INSTRUCTIONS = load_agent_instructions("Gandalf.md")
BILBO_INSTRUCTIONS = load_agent_instructions("BilboBot.md")

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
        chunk.raw_representation # type: ignore
        and chunk.raw_representation.raw_representation # type: ignore
        and hasattr(chunk.raw_representation.raw_representation, "choices") # type: ignore
        and chunk.raw_representation.raw_representation.choices is not None # type: ignore
        and len(chunk.raw_representation.raw_representation.choices) > 0 # type: ignore
        and hasattr(chunk.raw_representation.raw_representation.choices[0], "delta") # type: ignore
        and hasattr(chunk.raw_representation.raw_representation.choices[0].delta, "tool_calls") # type: ignore
        and chunk.raw_representation.raw_representation.choices[0].delta.tool_calls is not None # type: ignore
        and len(chunk.raw_representation.raw_representation.choices[0].delta.tool_calls) > 0 # type: ignore
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
                for call in chunk.raw_representation.raw_representation.choices[0].delta.tool_calls # type: ignore
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


async def run_mystery_solving(
    sauron: ChatAgent,
    gandalf: ChatAgent,
    bilbo: ChatAgent,
    max_turns: int,
) -> None:
    """Mystery-solving scenario where Sauron creates a mystery and Gandalf+Bilbo solve it."""
    
    sauron_thread = sauron.get_new_thread()
    gandalf_thread = gandalf.get_new_thread()
    bilbo_thread = bilbo.get_new_thread()

    # Step 1: Sauron creates the mystery
    print("\n" + "="*80)
    print("🌋 THE MYSTERY OF MIDDLE-EARTH 🌋")
    print("="*80)
    
    mystery_prompt = (
        "Weave a dark mystery set in Middle-earth. Use your MCP tool to fetch a LOTR quote "
        "for inspiration, then craft your mysterious riddle."
    )
    
    mystery = await stream_agent_response(
        sauron,
        sauron_thread,
        mystery_prompt,
        speaker=SAURON_AGENT_NAME,
        log_tool_calls=True,
    )

    print("\n" + "="*80)
    print("🧙 INVESTIGATION BEGINS 🧙")
    print("="*80)

    # Step 2: Gandalf and Bilbo collaborate to solve it
    investigation_context = f"A dark mystery has been presented:\n\n{mystery}\n\nWhat are your initial thoughts?"
    
    current_investigator: Literal["gandalf", "bilbo"] = "gandalf"
    solved = False
    
    for turn in range(1, max_turns + 1):
        if current_investigator == "gandalf":
            response = await stream_agent_response(
                gandalf,
                gandalf_thread,
                investigation_context,
                speaker=GANDALF_AGENT_NAME,
                log_tool_calls=False,
            )
            
            # Check if Gandalf has declared a solution
            if "SOLUTION:" in response.upper():
                print("\n🎯 Gandalf has proposed a solution!")
                
                # Ask Bilbo to verify
                verification_prompt = (
                    f"Gandalf proposes the following solution:\n\n{response}\n\n"
                    "Do you concur with this solution, or do you see any flaws?"
                )
                
                bilbo_response = await stream_agent_response(
                    bilbo,
                    bilbo_thread,
                    verification_prompt,
                    speaker=BILBO_AGENT_NAME,
                    log_tool_calls=False,
                )
                
                if "CONCUR" in bilbo_response.upper():
                    print("\n✅ Mystery solved! Both investigators agree!")
                    solved = True
                    break
                else:
                    investigation_context = (
                        f"Bilbo's response to your solution:\n\n{bilbo_response}\n\n"
                        "Consider his feedback and continue investigating."
                    )
                    current_investigator = "gandalf"
            else:
                # Pass Gandalf's analysis to Bilbo
                investigation_context = (
                    f"Gandalf's analysis:\n\n{response}\n\n"
                    "What are your thoughts? Do you notice anything else?"
                )
                current_investigator = "bilbo"
        
        else:  # bilbo's turn
            response = await stream_agent_response(
                bilbo,
                bilbo_thread,
                investigation_context,
                speaker=BILBO_AGENT_NAME,
                log_tool_calls=False,
            )
            
            # Pass Bilbo's insights back to Gandalf
            investigation_context = (
                f"Bilbo's observation:\n\n{response}\n\n"
                "Incorporate his insights and continue your deduction."
            )
            current_investigator = "gandalf"
    
    if not solved:
        print("\n⚠️ Investigation ongoing - the mystery remains unsolved after maximum turns.")
        print("The darkness of Mordor keeps its secrets still...")


async def main() -> None:
    chat_client = OpenAIChatClient(
        async_client=openaiClient,
        model_id="openai/gpt-4.1",
    )

    # Get scenario choice from environment, otherwise prompt user
    scenario = os.getenv("SCENARIO", "").lower()
    
    if not scenario:
        print("\n" + "="*80)
        print("🌟 Welcome to the LOTR Multi-Agent Demo 🌟")
        print("="*80)
        print("\nChoose your adventure:\n")
        print("  1. 🎭 Poetry Collaboration")
        print("     - Poet creates LOTR-inspired poems")
        print("     - Critic reviews and refines them\n")
        print("  2. 🕵️  Mystery Solving")
        print("     - Sauron weaves a dark mystery")
        print("     - Gandalf & Bilbo investigate and solve it\n")
        print("="*80)
        
        while True:
            choice = input("\nEnter your choice (1 or 2): ").strip()
            if choice == "1":
                scenario = "poetry"
                break
            elif choice == "2":
                scenario = "mystery"
                break
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
        
        print(f"\n✨ Starting {scenario.upper()} scenario...\n")
    
    if scenario == "poetry":
        print("\n🎭 Starting Poetry Collaboration Scenario 🎭\n")
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
    
    elif scenario == "mystery":
        print("\n🕵️ Starting Mystery Solving Scenario 🕵️\n")
        async with (
            ChatAgent(
                chat_client=chat_client,
                instructions=SAURON_INSTRUCTIONS,
                temperature=0.9,
                top_p=0.95,
                name=SAURON_AGENT_NAME,
                tools=create_mcp_tools(),
            ) as sauron,
            ChatAgent(
                chat_client=chat_client,
                instructions=GANDALF_INSTRUCTIONS,
                temperature=0.7,
                top_p=0.9,
                name=GANDALF_AGENT_NAME,
            ) as gandalf,
            ChatAgent(
                chat_client=chat_client,
                instructions=BILBO_INSTRUCTIONS,
                temperature=0.6,
                top_p=0.85,
                name=BILBO_AGENT_NAME,
            ) as bilbo,
        ):
            await run_mystery_solving(
                sauron=sauron,
                gandalf=gandalf,
                bilbo=bilbo,
                max_turns=MYSTERY_MAX_TURNS,
            )
    
    else:
        print(f"❌ Unknown scenario: {scenario}")
        print("Available scenarios: 'poetry' or 'mystery'")
        return

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
