# MCP-to-MCP Bridge Protocol Specification

## Overview

The MCP-to-MCP Bridge Protocol enables standardized communication between MCP agents in a distributed swarm. This protocol defines message formats, handshake mechanisms, and communication patterns for agent coordination.

**Version:** 0.1.0
**Status:** Draft

## Design Goals

1. **Type Safety**: All messages validated with Pydantic schemas
2. **Traceability**: UUID-based message IDs and correlation IDs for request/response tracking
3. **Flexibility**: Support for synchronous request/response and asynchronous notifications
4. **Extensibility**: Easily add new message types and capabilities
5. **Error Handling**: Structured error messages with error codes and details

## Message Types

The protocol defines six core message types:

| Type | Purpose | Correlation Required |
|------|---------|---------------------|
| `handshake_request` | Initial connection and capability exchange | No |
| `handshake_response` | Acknowledge handshake and share capabilities | Yes |
| `request` | Invoke a tool on remote agent | No |
| `response` | Return result of tool invocation | Yes |
| `notification` | Broadcast or targeted event notification | No |
| `error` | Report an error condition | Optional |

## Message Priority

Messages can be prioritized for processing:

- `LOW`: Background tasks, non-critical operations
- `NORMAL`: Standard operations (default)
- `HIGH`: Important operations requiring prompt attention
- `URGENT`: Critical operations requiring immediate processing

## Base Message Structure

All messages share this common structure:

```json
{
  "message_id": "uuid-v4",
  "message_type": "request|response|notification|error|handshake_request|handshake_response",
  "sender_id": "agent-id",
  "receiver_id": "agent-id|null",
  "timestamp": "ISO-8601-timestamp",
  "correlation_id": "uuid-v4|null",
  "priority": "low|normal|high|urgent",
  "payload": {}
}
```

### Fields

- **message_id**: Auto-generated UUID v4, unique per message
- **message_type**: One of the six message types
- **sender_id**: Identifier of the sending agent
- **receiver_id**: Identifier of target agent (null for broadcasts)
- **timestamp**: ISO 8601 UTC timestamp (auto-generated)
- **correlation_id**: Links responses to requests
- **priority**: Processing priority level
- **payload**: Message-specific data (type depends on message_type)

## Communication Patterns

### 1. Handshake Flow

Agents must exchange handshakes before other communication:

```
Agent A                           Agent B
   |                                 |
   |  handshake_request              |
   |  (capabilities)                 |
   |-------------------------------->|
   |                                 |
   |         handshake_response      |
   |         (capabilities, accepted)|
   |<--------------------------------|
   |                                 |
```

**HandshakeRequest payload (AgentCapabilities):**
```json
{
  "agent_id": "agent-1",
  "agent_name": "Data Processor",
  "agent_role": "processor",
  "tools": ["process_data", "validate_input"],
  "version": "0.1.0",
  "metadata": {
    "region": "us-east",
    "capacity": "high"
  }
}
```

**HandshakeResponse payload (AgentCapabilities + accepted flag):**
```json
{
  "agent_id": "agent-2",
  "agent_name": "Coordinator",
  "agent_role": "coordinator",
  "tools": ["coordinate_task", "assign_work"],
  "version": "0.1.0",
  "metadata": {},
  "accepted": true
}
```

### 2. Request/Response Flow

Tool invocation follows request/response pattern:

```
Agent A                           Agent B
   |                                 |
   |  request                        |
   |  (tool_name, arguments)         |
   |-------------------------------->|
   |                                 |
   |  [Agent B executes tool]        |
   |                                 |
   |         response                |
   |         (result)                |
   |<--------------------------------|
   |                                 |
```

**RequestMessage payload (ToolRequest):**
```json
{
  "tool_name": "process_data",
  "arguments": {
    "data": "input data",
    "format": "json"
  },
  "timeout": 30
}
```

**ResponseMessage payload (ToolResponse):**
```json
{
  "success": true,
  "result": {
    "processed": true,
    "output": "result data"
  },
  "execution_time": 0.5,
  "error": null
}
```

### 3. Notification Flow

Agents can send notifications (one-way, no response expected):

```
Agent A                     Agent B, C, D
   |                             |
   |  notification               |
   |  (event_type, data)         |
   |---------------------------->|
   |                             |
```

**NotificationMessage payload:**
```json
{
  "event_type": "agent_status_changed",
  "data": {
    "status": "busy",
    "reason": "processing_large_batch"
  }
}
```

- **Broadcast**: `receiver_id` is `null`, sent to all agents
- **Targeted**: `receiver_id` specifies single recipient

### 4. Error Handling

Errors can be reported at any stage:

**ErrorMessage payload (ErrorDetails):**
```json
{
  "error_code": "TOOL_NOT_FOUND",
  "error_message": "The requested tool does not exist",
  "error_type": "not_found",
  "details": {
    "tool_name": "invalid_tool",
    "available_tools": ["ping", "echo"]
  }
}
```

**Standard Error Codes:**
- `TOOL_NOT_FOUND`: Requested tool doesn't exist
- `INVALID_ARGUMENTS`: Tool arguments are invalid
- `EXECUTION_FAILED`: Tool execution failed
- `TIMEOUT`: Operation timed out
- `UNAUTHORIZED`: Agent not authorized for operation
- `INTERNAL_ERROR`: Internal agent error

## Protocol Factory

The `MCPBridgeProtocol` class provides factory methods for creating messages:

```python
from mcp_swarm.core.protocol import MCPBridgeProtocol, AgentCapabilities, ToolRequest

# Create handshake request
caps = AgentCapabilities(
    agent_id="agent-1",
    agent_name="Processor",
    agent_role="processor"
)
handshake = MCPBridgeProtocol.create_handshake_request(
    sender_id="agent-1",
    capabilities=caps,
    receiver_id="agent-2"
)

# Create tool request
tool_req = ToolRequest(
    tool_name="process_data",
    arguments={"data": "test"}
)
request = MCPBridgeProtocol.create_request(
    sender_id="agent-1",
    receiver_id="agent-2",
    tool_request=tool_req,
    priority=MessagePriority.HIGH
)
```

## Message Validation

All messages are validated using Pydantic:

- **Type checking**: Field types are enforced
- **Required fields**: Missing required fields raise ValidationError
- **Enum values**: Message types and priorities must be valid enum values
- **JSON serialization**: All messages can be serialized to/from JSON

Example validation:
```python
from pydantic import ValidationError
from mcp_swarm.core.protocol import BaseMessage, MessageType

try:
    message = BaseMessage(
        sender_id="agent-1",
        message_type="invalid_type"  # Error!
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Transport Layer

This protocol defines the message format only. Transport mechanism (HTTP, WebSocket, etc.) is implementation-specific. Requirements:

- **Bidirectional**: Support both request/response and notifications
- **Reliable**: Guarantee message delivery
- **Ordered**: Maintain message order per sender
- **Secure**: Support authentication and encryption

## Future Extensions

Planned enhancements for future versions:

1. **Message Acknowledgment**: Explicit ACK/NACK for all messages
2. **Streaming**: Support for long-running operations with progress updates
3. **Compression**: Optional message compression for large payloads
4. **Encryption**: End-to-end message encryption
5. **Multi-hop Routing**: Forward messages through intermediate agents
6. **Message Batching**: Combine multiple messages for efficiency

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- Pydantic V2 Documentation: https://docs.pydantic.dev/

## Changelog

### Version 0.1.0 (2024-01-11)
- Initial protocol specification
- Six core message types defined
- Request/response and notification patterns
- Pydantic-based validation
- Factory methods for message creation
