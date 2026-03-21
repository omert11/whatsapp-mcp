# WhatsApp MCP Server (Fork)

This is a fork of [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) with additional features.

A Model Context Protocol (MCP) server for WhatsApp. Search, read, and send messages (including media) from your personal WhatsApp account via AI assistants like Claude.

Connects to your **personal WhatsApp account** via the WhatsApp web multidevice API ([whatsmeow](https://github.com/tulir/whatsmeow)). All messages are stored locally in SQLite and only sent to an LLM when accessed through tools.

> **Caution:** As with many MCP servers, this is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). Prompt injection could lead to private data exfiltration.

## Fork Changes

This fork adds the following features on top of the original:

### Quote Reply
Reply to specific messages with `quoted_message_id` and `quoted_chat_jid` parameters. Works with text, image, video, audio, and document messages.

### Mentions (@)
Tag people in group messages using the `mentions` parameter. Pass phone numbers (e.g., `["905551234567"]`) and they are automatically resolved to LID JIDs via `get_contact_lid`.

### Media Improvements
- **Document FileName**: Documents now display with proper file names in WhatsApp
- **Extended MIME types**: pdf, docx, xlsx, txt, md, csv, json, xml, zip and more
- **Caption support**: `send_file` now accepts a `message` parameter for captions

### Message Editing
Edited messages are detected and updated in the database instead of creating duplicates.

### Sent Message Storage
Messages you send are now saved to the database, enabling reply to your own messages.

### Image/Video/Document Captions
Media message captions (text attached to images/videos/documents) are now properly extracted and stored.

### Chat Management
- `refresh_chats` - Refresh all group names and contacts from WhatsApp
- `reset_messages` - Clear message database for a fresh start
- `get_chat_info` - Get group details including participant names, topic, and admin status

### REST API Endpoints
- `/api/messages` - List recent messages from a chat
- `/api/message` - Get a single message by ID
- `/api/chat-info` - Get chat/group info with participant names

### Port Change
API port changed from `8080` to `56271` to avoid conflicts.

### whatsmeow Update
Updated to latest whatsmeow version, fixing "client outdated (405)" connection errors.

## Installation

### Prerequisites

- Go
- Python 3.6+
- Claude Code, Claude Desktop, or Cursor
- UV (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- FFmpeg (_optional_) - Only needed for audio voice messages

### Steps

1. **Clone this repository**

   ```bash
   git clone https://github.com/omert11/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Build and run the WhatsApp bridge**

   ```bash
   cd whatsapp-bridge
   go build -o whatsapp-bridge main.go
   ./whatsapp-bridge
   ```

   Scan the QR code with your WhatsApp mobile app (Settings > Linked Devices > Link a Device).

3. **Configure your AI client**

   Add to your config (`~/.claude.json` for Claude Code, `claude_desktop_config.json` for Claude Desktop, `~/.cursor/mcp.json` for Cursor):

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "/path/to/uv",
         "args": [
           "--directory",
           "/path/to/whatsapp-mcp/whatsapp-mcp-server",
           "run",
           "main.py"
         ]
       }
     }
   }
   ```

   > **Tip:** Find the full path of `uv` with `which uv`

4. **Restart your AI client**

   The WhatsApp bridge must be running for the MCP server to work.

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_contacts` | Search contacts by name or phone number |
| `list_messages` | Retrieve messages with filters and context |
| `list_chats` | List available chats with metadata |
| `get_chat` | Get information about a specific chat |
| `get_chat_info` | Get group details with participant names |
| `get_direct_chat_by_contact` | Find a direct chat with a contact |
| `get_contact_chats` | List all chats involving a contact |
| `get_contact_lid` | Find a contact's LID JID for mentions |
| `get_last_interaction` | Get most recent message with a contact |
| `get_message_context` | Get context around a specific message |
| `send_message` | Send a message with optional reply, mentions |
| `send_file` | Send a file with optional caption, reply, mentions |
| `send_audio_message` | Send audio as a WhatsApp voice message |
| `download_media` | Download media from a message |
| `refresh_chats` | Refresh all chat names from WhatsApp |
| `reset_messages` | Clear message database |

### send_message Parameters

```
recipient         - Phone number or JID (required)
message           - Message text (required)
quoted_message_id - Message ID to reply to (optional)
quoted_chat_jid   - Chat JID of the quoted message (optional)
mentions          - List of phone numbers to mention (optional)
```

### send_file Parameters

```
recipient         - Phone number or JID (required)
media_path        - Absolute path to the file (required)
message           - Caption text (optional)
quoted_message_id - Message ID to reply to (optional)
quoted_chat_jid   - Chat JID of the quoted message (optional)
mentions          - List of phone numbers to mention (optional)
```

## Architecture

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): Connects to WhatsApp web API, handles auth, stores messages in SQLite, serves REST API on port 56271.

2. **Python MCP Server** (`whatsapp-mcp-server/`): Implements MCP protocol, provides tools for AI assistants to interact with WhatsApp.

### Data Flow

```
AI Assistant → MCP Server (Python) → Bridge REST API (Go) → WhatsApp
                    ↕
              SQLite Database
```

## Troubleshooting

- **Bridge won't connect**: Make sure you're running the latest compiled binary (`go build -o whatsapp-bridge main.go`)
- **QR code not displaying**: Restart the bridge. Check terminal QR code support.
- **"Client outdated" error**: This fork has the fix. Rebuild the bridge.
- **Messages not loading**: After first auth, wait a few minutes for history sync.
- **Out of sync**: Delete `whatsapp-bridge/store/messages.db` and restart the bridge. Keep `whatsapp.db` to avoid re-scanning QR.
- **Port conflict**: The bridge uses port 56271. Check with `lsof -i :56271`.

## License

MIT
