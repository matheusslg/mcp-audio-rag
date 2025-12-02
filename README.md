# MCP Audio RAG Server

> Transform your audio files into a searchable knowledge base using AI. Ask Claude questions about your meetings, podcasts, lectures, or any audio content.

<p align="center">
  <a href="https://www.buymeacoffee.com/matheusslg" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
  </a>
</p>

## What is this?

This is an MCP (Model Context Protocol) server that lets you:

1. **Transcribe** any audio file using Google's Gemini AI
2. **Store** the transcriptions in a searchable database
3. **Search** through all your audio content using natural language

Once set up, you can simply ask Claude things like:
- *"What did they discuss about the budget in my meeting recording?"*
- *"Find mentions of machine learning in my podcast collection"*
- *"What were the key points from yesterday's lecture?"*

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Audio File  │ ──▶ │   Gemini    │ ──▶ │  Chunking   │ ──▶ │  Supabase   │
│ (.mp3, etc) │     │ Transcribe  │     │ + Embedding │     │  (pgvector) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │
│   Claude    │ ◀── │   Results   │ ◀── │   Search    │ ◀──────────┘
│  Response   │     │ + Snippets  │     │   Query     │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Gemini API Key** - [Get one free](https://aistudio.google.com/apikey)
- **Supabase Account** - [Sign up free](https://supabase.com)

### Step 1: Clone & Install

```bash
git clone https://github.com/matheusslg/mcp-audio-rag.git
cd mcp-audio-rag
npm install
```

### Step 2: Set Up Supabase Database

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in your dashboard
3. Paste and run the contents of `supabase/schema.sql`

### Step 3: Get Your API Keys

**Supabase** (Settings → API):
- Copy **Project URL** → `SUPABASE_URL`
- Copy **service_role key** → `SUPABASE_SERVICE_KEY`

**Google AI Studio**:
- Create key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → `GEMINI_API_KEY`

### Step 4: Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

### Step 5: Add to Claude

**For Claude Code CLI** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "audio-rag": {
      "command": "npx",
      "args": ["tsx", "/full/path/to/mcp-audio-rag/src/server.ts"],
      "env": {
        "GEMINI_API_KEY": "your-key",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-role-key"
      }
    }
  }
}
```

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

Same config as above.

## Usage

### Transcribe Audio

Just tell Claude to transcribe a file:

```
Transcribe /path/to/meeting.mp3
```

Want to use a specific model? Just ask:

```
Transcribe /path/to/lecture.m4a using gemini-2.5-pro
```

### Search Your Audio

Ask natural questions:

```
What did they say about the project timeline?
Search for mentions of "budget" in my recordings
Find discussions about AI in my podcasts
```

## Available Models

| Model | Best For |
|-------|----------|
| `gemini-2.5-flash` | **Default** - Fast & accurate, great balance |
| `gemini-2.5-flash-lite` | Fastest, cheapest - good for bulk processing |
| `gemini-2.5-pro` | Best quality - complex audio, multiple speakers |
| `gemini-3-pro-preview` | Newest - cutting edge capabilities |
| `gemini-2.0-flash` | Reliable - previous generation |
| `gemini-2.0-flash-lite` | Fast - previous generation |

## Supported Audio Formats

`.mp3` `.mp4` `.m4a` `.wav` `.webm` `.mpeg` `.mpga`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No relevant segments found" | Try rephrasing your search, or check if audio was ingested |
| "Missing environment variable" | Check your `.env` file or Claude config has all 3 keys |
| Supabase errors | Make sure you're using `service_role` key, not `anon` key |
| Slow transcription | Use `gemini-2.5-flash-lite` for faster processing |

## Support This Project

If this project saved you time or helped you out, consider buying me a coffee!

<a href="https://www.buymeacoffee.com/matheusslg" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

## License

MIT - Use it however you want!

---

<p align="center">
  Made with Gemini + Supabase + Claude
</p>
