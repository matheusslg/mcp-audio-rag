import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { createClient } from "@supabase/supabase-js";
import { GoogleGenAI, createPartFromUri } from "@google/genai";
import dotenv from "dotenv";
import fs from "fs";
import path from "path";

dotenv.config();

const SUPPORTED_FORMATS = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"];
const CHUNK_SIZE = 1000;
const CHUNK_OVERLAP = 200;

interface TranscriptDocument {
  id: string;
  content: string;
  source_file: string;
  similarity: number;
}

// Validate required environment variables
const requiredEnvVars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY"];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`Missing required environment variable: ${envVar}`);
    process.exit(1);
  }
}

// Initialize Clients
const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });

// Create MCP Server
const server = new McpServer({
  name: "audio-knowledge-base",
  version: "1.0.0",
});

// Helper function to chunk text with overlap
function chunkText(text: string, chunkSize: number, overlap: number): string[] {
  const chunks: string[] = [];
  let start = 0;

  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.slice(start, end));
    start += chunkSize - overlap;
    if (start + overlap >= text.length) break;
  }

  return chunks;
}

// Helper function to get MIME type
function getMimeType(ext: string): string {
  const mimeTypes: Record<string, string> = {
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".mpeg": "audio/mpeg",
    ".mpga": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
  };
  return mimeTypes[ext] || "audio/mpeg";
}

// Generate embeddings using Gemini
async function generateEmbedding(text: string): Promise<number[]> {
  const response = await ai.models.embedContent({
    model: "text-embedding-004",
    contents: text,
  });
  return response.embeddings?.[0]?.values || [];
}

// Ingest Audio Tool
server.tool(
  "ingest_audio",
  "Transcribe an audio file and store it in the knowledge base for later searching.",
  {
    file_path: z.string().describe("Absolute path to the audio file to transcribe"),
  },
  async ({ file_path }) => {
    try {
      // Validate file exists
      if (!fs.existsSync(file_path)) {
        return {
          content: [{ type: "text" as const, text: `File not found: ${file_path}` }],
          isError: true,
        };
      }

      // Validate format
      const ext = path.extname(file_path).toLowerCase();
      if (!SUPPORTED_FORMATS.includes(ext)) {
        return {
          content: [{
            type: "text" as const,
            text: `Unsupported format: ${ext}\n\nSupported: ${SUPPORTED_FORMATS.join(", ")}`,
          }],
          isError: true,
        };
      }

      const fileName = path.basename(file_path);
      const results: string[] = [];
      results.push(`Processing: ${fileName}\n`);

      // Step 1: Upload file to Gemini
      results.push("Uploading audio to Gemini...");

      const uploadedFile = await ai.files.upload({
        file: file_path,
        config: {
          mimeType: getMimeType(ext),
          displayName: fileName,
        },
      });

      // Wait for file processing
      let file = await ai.files.get({ name: uploadedFile.name! });
      while (file.state === "PROCESSING") {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        file = await ai.files.get({ name: uploadedFile.name! });
      }

      if (file.state === "FAILED") {
        return {
          content: [{ type: "text" as const, text: `File processing failed: ${file.name}` }],
          isError: true,
        };
      }

      results.push("Upload complete\n");

      // Step 2: Transcribe with Gemini
      results.push("Transcribing audio with Gemini...");

      const transcriptionResult = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: [
          createPartFromUri(file.uri!, file.mimeType!),
          "Transcribe this audio file. Output only the transcription text, nothing else. Do not add any commentary, timestamps, or speaker labels unless they are clearly spoken in the audio.",
        ],
      });

      const transcriptText = transcriptionResult.text || "";
      results.push(`Transcription complete (${transcriptText.length} characters)\n`);

      // Clean up uploaded file
      await ai.files.delete({ name: file.name! });

      // Step 3: Chunk the transcript
      const chunks = chunkText(transcriptText, CHUNK_SIZE, CHUNK_OVERLAP);
      results.push(`Split into ${chunks.length} chunks\n`);

      // Step 4: Generate embeddings and store
      results.push("Generating embeddings and storing...");

      let storedCount = 0;
      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];

        // Generate embedding with Gemini
        const embedding = await generateEmbedding(chunk);

        // Store in Supabase
        const { error } = await supabase.from("transcripts").insert({
          content: chunk,
          source_file: fileName,
          embedding: embedding,
        });

        if (error) {
          results.push(`Warning: Failed to store chunk ${i + 1}: ${error.message}`);
        } else {
          storedCount++;
        }
      }

      results.push(`Stored ${storedCount}/${chunks.length} chunks\n`);

      // Summary
      const preview = transcriptText.slice(0, 300) + (transcriptText.length > 300 ? "..." : "");
      results.push("---");
      results.push("Transcript Preview:");
      results.push(`"${preview}"`);
      results.push("---");
      results.push(`\nDone! You can now search this audio with search_transcripts.`);

      return {
        content: [{ type: "text" as const, text: results.join("\n") }],
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      return {
        content: [{ type: "text" as const, text: `Error: ${errorMessage}` }],
        isError: true,
      };
    }
  }
);

// Search Tool
server.tool(
  "search_transcripts",
  "Search through audio transcriptions to find specific topics or quotes.",
  {
    query: z.string().describe("The topic or question to search for in the audio logs"),
    match_count: z.number().optional().describe("Number of results to return (default 5)"),
  },
  async ({ query, match_count = 5 }) => {
    try {
      // Generate embedding for query
      const queryVector = await generateEmbedding(query);

      // Call the Supabase RPC function
      const { data: documents, error } = await supabase.rpc("search_transcripts", {
        query_embedding: queryVector,
        match_threshold: 0.3,
        match_count: match_count,
      });

      if (error) {
        console.error("Supabase Error:", error);
        return {
          content: [{ type: "text" as const, text: `Database error: ${error.message}` }],
          isError: true,
        };
      }

      if (!documents || documents.length === 0) {
        return {
          content: [{ type: "text" as const, text: "No relevant audio segments found." }],
        };
      }

      const formattedResults = (documents as TranscriptDocument[])
        .map(
          (doc) =>
            `[Source: ${doc.source_file}]\n"${doc.content.trim()}"\n(Similarity: ${doc.similarity.toFixed(2)})`
        )
        .join("\n\n---\n\n");

      return {
        content: [{ type: "text" as const, text: formattedResults }],
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      return {
        content: [{ type: "text" as const, text: `Server error: ${errorMessage}` }],
        isError: true,
      };
    }
  }
);

// Start the Server
const transport = new StdioServerTransport();
await server.connect(transport);

console.error("Audio Knowledge Base MCP Server running on Stdio...");
