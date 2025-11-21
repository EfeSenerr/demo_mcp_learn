# LOTR MCP Demo

A demonstration project showcasing **Model Context Protocol (MCP)** integration with the **Microsoft Agent Framework**. This project features multi-agent systems that bring Middle-earth to life through collaborative AI agents.

## Features

- **MCP Server**: Custom MCP server (`lotr_mcp_server.py`) that fetches authentic LOTR quotes from [The One API](https://the-one-api.dev)
- **Two Unique Scenarios**:

### 🎭 Poetry Collaboration (Default)
  - **Poet Agent**: Generates four-line poems inspired by LOTR quotes
  - **Critic Agent**: Reviews poems for accuracy, tone, and adherence to Middle-earth lore
  - **Iterative Refinement**: Agents collaborate in a ping-pong pattern to refine poetry until approved

### 🕵️ Mystery Solving (New!)
  - **Sauron (Mystery Weaver)**: The Dark Lord crafts cryptic mysteries with hidden clues
  - **Gandalf the Grey (Detective)**: Wise wizard who analyzes clues and builds theories
  - **Bilbo Baggins (Investigator)**: Applies hobbit-sense and notices overlooked details
  - **Collaborative Investigation**: Gandalf and Bilbo work together to solve Sauron's mysteries

## Prerequisites

- Python 3.8+
- GitHub Personal Access Token (for GitHub Models API)
- The One API Key (from [the-one-api.dev](https://the-one-api.dev))

## Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Create a `.env` file with your API keys:
   ```
   GITHUB_TOKEN=your_github_token
   ONE_API_KEY=your_one_api_key
   ```

3. Run the demo:
   
   **Poetry Scenario (default):**
   ```bash
   python main.py
   # OR explicitly
   SCENARIO=poetry python main.py
   ```
   
   **Mystery Scenario:**
   ```bash
   SCENARIO=mystery python main.py
   ```
   
   Or in PowerShell:
   ```powershell
   $env:SCENARIO="mystery"; python main.py
   ```

## Configuration

You can customize the behavior with environment variables:

- `SCENARIO`: Choose between `poetry` or `mystery` (default: `mystery`)
- `PING_PONG_LIMIT`: Max iterations for poetry refinement (default: `5`)
- `MYSTERY_MAX_TURNS`: Max turns for mystery investigation (default: `8`)
- `GITHUB_TOKEN`: Your GitHub Personal Access Token
- `ONE_API_KEY`: Your The One API key

## How It Works

### Poetry Scenario Flow
1. The Poet agent calls the MCP tool to fetch a random LOTR quote
2. It paraphrases the quote and composes a four-line poem
3. The Critic agent reviews the poem for lore accuracy and quality
4. If revisions are needed, the Poet refines the poem based on feedback
5. The cycle continues until the Critic approves or the iteration limit is reached

### Mystery Scenario Flow
1. **Sauron** uses the MCP tool to fetch a LOTR quote for inspiration
2. **Sauron** crafts a dark mystery with 3-5 hidden clues set in Middle-earth
3. **Gandalf** receives the mystery and begins analysis, forming theories
4. **Gandalf** and **Bilbo** take turns investigating:
   - Gandalf applies wizard wisdom and lore knowledge
   - Bilbo notices practical details and challenges assumptions
5. When Gandalf proposes a solution, Bilbo verifies it
6. If both agree, the mystery is solved! Otherwise, investigation continues

## Project Structure

- `lotr_mcp_server.py` - MCP server implementation for fetching LOTR quotes
- `main.py` - Multi-agent orchestration with both scenarios
- `pyproject.toml` - Project dependencies and metadata
- `.github/agents/` - Agent personality definitions:
  - `Sauron.md` - The Mystery Weaver
  - `Gandalf.md` - The Wise Detective
  - `BilboBot.md` - The Observant Investigator

## Agent Personalities

### Sauron the Mystery Weaver 🌋
- **Temperature**: 0.9 (highly creative)
- **Role**: Creates cryptic mysteries with hidden clues
- **Style**: Dark, ominous, master of deception

### Gandalf the Grey 🧙
- **Temperature**: 0.7 (balanced reasoning)
- **Role**: Lead detective and lore expert
- **Style**: Wise, methodical, shares reasoning process

### Bilbo Baggins 🍃
- **Temperature**: 0.6 (grounded and practical)
- **Role**: Observant investigator with hobbit-sense
- **Style**: Friendly, detail-oriented, draws on adventure experience

## Example Output

**Mystery Scenario:**
```
🌋 Sauron weaves a dark mystery...
"In the halls of Imladris, three artifacts have vanished..."

🧙 Gandalf analyzes the clues...
THEORY: The disappearance aligns with the lunar cycle...

🍃 Bilbo observes...
OBSERVATION: But wait, the smallest artifact wouldn't fit through...

✅ Mystery solved!
```