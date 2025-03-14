# Perplexity MCP Server

## Overview

The Perplexity MCP Server is a Node.js implementation of Anthropic's Model Context Protocol (MCP) that enables Claude to interact with Perplexity's language models. This server provides a secure bridge between Claude and Perplexity AI's capabilities, allowing for enhanced AI interactions through tool use.

## Available Tools

The server currently implements two main tools:

### 1. perplexity_chat

Advanced chat completion tool with full message history support.

```javascript
{
  "name": "perplexity_chat",
  "description": "Generate a chat completion using Perplexity AI",
  "parameters": {
    "model": "string (optional) - One of: llama-3.1-sonar-small-128k-online, llama-3.1-sonar-large-128k-online, llama-3.1-sonar-huge-128k-online",
    "messages": "array of {role, content} objects - The conversation history",
    "temperature": "number (optional) - Sampling temperature between 0-2"
  }
}
```

### 2. perplexity_ask

Simplified single-query interface for quick questions.

```javascript
{
  "name": "perplexity_ask",
  "description": "Send a simple query to Perplexity AI",
  "parameters": {
    "query": "string - The question or prompt to send",
    "model": "string (optional) - One of: llama-3.1-sonar-small-128k-online, llama-3.1-sonar-large-128k-online, llama-3.1-sonar-huge-128k-online"
  }
}
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/perplexity-mcp-server.git
   cd perplexity-mcp-server
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Create `.env` file:

   ```env
   PERPLEXITY_API_KEY=your-api-key-here
   ```

4. Build the project:
   ```bash
   npm run build
   ```

## Claude Desktop Configuration

To add this server to Claude Desktop, update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    //more servers...
    "perplexity": {
      "command": "node",
      "args": ["path\\to\\perplexity-mcp-server\\dist\\index.js"],
      "env": {
        "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY"
      }
    }
    //more servers...
  }
}
```

The configuration file is typically located at:

- Windows: `%APPDATA%/Claude/config/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/config/claude_desktop_config.json`
- Linux: `~/.config/Claude/config/claude_desktop_config.json`

## Development

Start the development server with automatic recompilation:

```bash
npm run dev
```

The server uses TypeScript and implements the MCP protocol using the `@modelcontextprotocol/sdk` package.

## Architecture

### Core Components

1. **PerplexityServer Class**

   - Implements MCP server protocol
   - Handles tool registration and execution
   - Manages error handling and server lifecycle

2. **Tools System**
   - Modular tool definitions
   - Type-safe tool handlers
   - Structured input validation

### Technical Details

- Built with TypeScript for type safety
- Uses `@modelcontextprotocol/sdk` for MCP implementation
- Communicates via stdio transport
- Environment-based configuration

## Error Handling

The server implements comprehensive error handling:

- API error reporting
- Invalid tool requests handling
- Connection error management
- Process signal handling

## Dependencies

- `@modelcontextprotocol/sdk`: ^1.0.3
- `dotenv`: ^16.4.7
- `isomorphic-fetch`: ^3.0.0

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- API keys are managed through environment variables
- Input validation for all tool parameters
- Error messages are sanitized before output
- Process isolation through MCP protocol

## License

This project is licensed under the ISC License.

## Troubleshooting

Common issues and solutions:

1. **Server Not Found**

   - Verify the path in `claude_desktop_config.json` is correct
   - Ensure the server is built (`npm run build`)
   - Check if Node.js is in your PATH

2. **Authentication Errors**

   - Verify your Perplexity API key in .env
   - Check if the API key has the required permissions

3. **Tool Execution Errors**
   - Verify the tool parameters match the schema
   - Check network connectivity
   - Review server logs for detailed error messages
