# MCP-Swarm Framework

**Distributed AI Agent Orchestration via Model Context Protocol**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🚀 The Innovation

While MCP has gained traction with early adopters, most implementations focus on single-agent scenarios. **MCP-Swarm** is the first framework to enable MCP-based multi-agent orchestration, where agents communicate through MCP servers rather than traditional message passing.

## ✨ Key Features

- **Protocol-First Design**: All communication through standardized MCP
- **Agent Autonomy**: Each agent operates as an independent MCP server
- **Dynamic Discovery**: Agents discover each other via MCP Registry
- **State Synchronization**: Distributed state management across agents
- **Production-Ready**: Built with observability, resilience, and scalability in mind

## 📋 Requirements

- Python 3.11+
- [UV](https://github.com/astral-sh/uv) package manager

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/rinaldofesta/mcp-swarm.git
cd mcp-swarm

# Install dependencies
uv sync

# Activate virtual environment (UV handles this automatically)
uv run python --version
```

## 🎯 Quick Start

```python
from mcp_swarm.core.agent import MCPAgent

# Create an agent
agent = MCPAgent(name="my-agent", role="processor")

# Initialize and start
await agent.initialize()
await agent.start()
```

## 📚 Documentation

- [Architecture Guide](docs/architecture/)
- [API Reference](docs/api/)
- [Tutorials](docs/tutorials/)
- [Examples](examples/)

## 🏗️ Project Structure

```
mcp-swarm/
├── src/mcp_swarm/      # Core framework code
├── tests/              # Test suite
├── examples/           # Example implementations
├── docs/               # Documentation
└── scripts/            # Utility scripts
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with [FastMCP](https://fastmcp.dev) and following the [Model Context Protocol](https://spec.mcp.dev) specification.

---

**Status**: 🚧 Early Development - We're building the future of AI agent orchestration!
