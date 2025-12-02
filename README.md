# MCP Audio RAG Server

An MCP (Model Context Protocol) server that enables semantic search over audio transcriptions using Google Gemini. Transcribe audio files and let Claude search through them to find relevant information.

## Architecture

```
Audio Files → Gemini (transcription) → Chunks → Embeddings → Supabase (pgvector)
                                                                    ↓
Claude ← MCP Server ← Vector Search ←─────────────────────────────────┘
```

## Features

- **Transcription**: Uses Gemini models for accurate audio transcription (model selection supported)
- **Embeddings**: Uses Gemini text-embedding-004 (768 dimensions)
- **Vector Search**: PostgreSQL with pgvector for semantic similarity search
- **MCP Integration**: Works with Claude Code CLI and Claude Desktop
- **Model Selection**: Choose from multiple Gemini models for transcription

## Available Models

| Model | Description |
|-------|-------------|
| `gemini-3-pro-preview` | Newest, most intelligent |
| `gemini-2.5-flash` | **Default** - best price/performance |
| `gemini-2.5-flash-lite` | Ultra fast, cheapest |
| `gemini-2.5-pro` | Advanced thinking/reasoning |
| `gemini-2.0-flash` | Previous gen workhorse |
| `gemini-2.0-flash-lite` | Previous gen fast |

## Prerequisites

- Node.js 18+
- Google AI (Gemini) API key
- Supabase account (free tier works)

## Setup

### 1. Clone and Install

```bash
git clone https://github.com/matheusslg/mcp-audio-rag.git
cd mcp-audio-rag
npm install
```

### 2. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Choose a name, password, and region
4. Wait for the project to be created (~2 minutes)

### 3. Set Up the Database

1. In your Supabase dashboard, go to **SQL Editor**
2. Copy the contents of `supabase/schema.sql`
3. Paste and run the SQL

This creates:
- The `transcripts` table with vector support (768 dimensions)
- An index for fast similarity search
- The `search_transcripts` RPC function

### 4. Get Your Credentials

**From Supabase:**
1. Go to **Settings** → **API**
2. Copy the **Project URL** (this is `SUPABASE_URL`)
3. Copy the **service_role** key (this is `SUPABASE_SERVICE_KEY`)

**From Google AI Studio:**
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create a new API key

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
GEMINI_API_KEY=your-gemini-api-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

## MCP Tools

### `ingest_audio`
Transcribe an audio file and store it in the knowledge base.

**Parameters:**
- `file_path` (string, required): Absolute path to the audio file
- `model` (string, optional): Gemini model to use for transcription. Default: `gemini-2.5-flash`

**Supported formats:** `.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`

### `search_transcripts`
Search through stored transcriptions for specific topics or quotes.

**Parameters:**
- `query` (string, required): The topic or question to search for
- `match_count` (number, optional): Number of results to return (default: 5)

## Configuring MCP Clients

### Claude Code CLI

Edit `~/.claude.json`:

```json
{
  "mcpServers": {
    "audio-rag": {
      "command": "npx",
      "args": ["tsx", "/path/to/mcp-audio-rag/src/server.ts"],
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-role-key"
      }
    }
  }
}
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "audio-rag": {
      "command": "npx",
      "args": ["tsx", "/path/to/mcp-audio-rag/src/server.ts"],
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-role-key"
      }
    }
  }
}
```

## Usage Examples

Once configured, you can ask Claude:

**Ingestion:**
- "Transcribe /path/to/meeting.mp3"
- "Ingest /path/to/podcast.m4a using gemini-2.5-pro"
- "Transcribe this audio with gemini-3-pro-preview: /path/to/lecture.wav"

**Search:**
- "Search my audio recordings for discussions about project deadlines"
- "What did they say about vector search in my recordings?"
- "Find any mentions of architecture in my audio notes"

## Project Structure

```
mcp-audio-rag/
├── src/
│   └── server.ts         # MCP server implementation
├── supabase/
│   └── schema.sql        # Database schema
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

## How It Works

1. **Ingestion**: Audio files are uploaded to Gemini, transcribed using your chosen model, chunked into segments with overlap (1000 chars, 200 overlap), converted to embeddings, and stored in Supabase with pgvector.

2. **Search**: When you ask Claude a question, the MCP server converts your query to an embedding and performs a vector similarity search to find the most relevant transcript segments.

3. **Response**: Claude receives the matching segments with their source files and similarity scores, then synthesizes an answer.

## Troubleshooting

**"Missing required environment variable"**
- Ensure your `.env` file exists and has all three variables set
- For MCP clients, ensure the env variables are in the config JSON

**"No relevant audio segments found"**
- The default similarity threshold is 0.3
- Ensure you've ingested audio files first
- Try rephrasing your search query

**Supabase connection errors**
- Verify your SUPABASE_URL starts with `https://`
- Ensure you're using the `service_role` key, not the `anon` key

**Transcription taking too long**
- Try using `gemini-2.5-flash-lite` or `gemini-2.0-flash-lite` for faster processing
- Large audio files take longer to upload and process

## License

MIT
