# LOTR MCP Demo

A demonstration project showcasing **Model Context Protocol (MCP)** integration with the **Microsoft Agent Framework**. This project features a multi-agent system that generates Lord of the Rings-inspired poetry through collaborative AI agents.

## Features

- **MCP Server**: Custom MCP server (`lotr_mcp_server.py`) that fetches authentic LOTR quotes from [The One API](https://the-one-api.dev)
- **Multi-Agent System**: Two AI agents working together:
  - **Poet Agent**: Generates four-line poems inspired by LOTR quotes
  - **Critic Agent**: Reviews poems for accuracy, tone, and adherence to Middle-earth lore
- **Iterative Refinement**: Agents collaborate in a ping-pong pattern to refine poetry until approved

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
   ```bash
   python agent_framework_template.py
   ```

## How It Works

1. The Poet agent calls the MCP tool to fetch a random LOTR quote
2. It paraphrases the quote and composes a four-line poem
3. The Critic agent reviews the poem for lore accuracy and quality
4. If revisions are needed, the Poet refines the poem based on feedback
5. The cycle continues until the Critic approves or the iteration limit is reached

## Project Structure

- `lotr_mcp_server.py` - MCP server implementation
- `agent_framework_template.py` - Multi-agent orchestration
- `pyproject.toml` - Project dependencies and metadata