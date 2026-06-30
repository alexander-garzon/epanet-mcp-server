# mcp-server-epanet: An EPANET MCP server

## Overview

A Model Context Protocol server for EPANET water distribution network simulation and analysis. This server provides tools to load, simulate, visualise, and modify hydraulic network models via Large Language Models.

Please note that mcp-server-epanet is currently in early development. The functionality and available tools are subject to change and expansion as we continue to develop and improve the server.

### Tools

<!-- Tools will be documented here -->

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-epanet*.

### Using PIP

Alternatively you can install `mcp-server-epanet` via pip:

```
pip install mcp-server-epanet
```

After installation, you can run it as a script using:

```
python -m mcp_server_epanet
```

## Configuration

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "epanet": {
    "command": "uvx",
    "args": ["mcp-server-epanet"]
  }
}
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"mcpServers": {
  "epanet": {
    "command": "python",
    "args": ["-m", "mcp_server_epanet"]
  }
}
```
</details>

### Usage with VS Code

For manual installation, add the configuration to a file called `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "epanet": {
      "command": "uvx",
      "args": ["mcp-server-epanet"]
    }
  }
}
```

Or using a local uv installation:

```json
{
  "servers": {
    "epanet": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "mcp-server-epanet"]
    }
  }
}
```

> For more details about MCP configuration in VS Code, see the [official VS Code MCP documentation](https://code.visualstudio.com/docs/copilot/customization/mcp-servers).

## Debugging

You can use the MCP inspector to debug the server. For uvx installations:

```
npx @modelcontextprotocol/inspector uvx mcp-server-epanet
```

Or if you are developing locally:

```
cd path/to/epanet-mcp-server
npx @modelcontextprotocol/inspector uv run mcp-server-epanet
```

Running `tail -n 20 -f ~/Library/Logs/Claude/mcp*.log` will show the logs from the server and may
help you debug any issues.

## Development

If you are doing local development, there are two ways to test your changes:

1. Run the MCP inspector to test your changes. See [Debugging](#debugging) for run instructions.

2. Test using the Claude desktop app. Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "epanet": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/epanet-mcp-server",
        "run",
        "mcp-server-epanet"
      ]
    }
  }
}
```

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
