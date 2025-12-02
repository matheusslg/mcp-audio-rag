-- Enable the pgvector extension
create extension if not exists vector;

-- Create the transcripts table
create table if not exists transcripts (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  source_file text not null,
  embedding vector(768), -- Gemini text-embedding-004 outputs 768 dimensions
  created_at timestamp with time zone default now()
);

-- Create an index for faster vector similarity search
create index if not exists transcripts_embedding_idx
  on transcripts
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Create the search function
create or replace function search_transcripts(
  query_embedding vector(768),
  match_threshold float default 0.7,
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  source_file text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    t.id,
    t.content,
    t.source_file,
    1 - (t.embedding <=> query_embedding) as similarity
  from transcripts t
  where 1 - (t.embedding <=> query_embedding) > match_threshold
  order by t.embedding <=> query_embedding
  limit match_count;
end;
$$;
