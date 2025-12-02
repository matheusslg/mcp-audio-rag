import streamlit as st
from supabase import create_client
from google import genai
import os

# Page config
st.set_page_config(
    page_title="Audio RAG",
    page_icon="🎧",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .file-card {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        cursor: pointer;
    }
    .file-card:hover {
        background-color: #f0f2f6;
    }
    .summary-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
    }
    .search-result {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }
    .similarity-badge {
        background-color: #e3f2fd;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize clients
@st.cache_resource
def init_clients():
    supabase = create_client(
        os.environ.get("SUPABASE_URL", st.secrets.get("SUPABASE_URL", "")),
        os.environ.get("SUPABASE_SERVICE_KEY", st.secrets.get("SUPABASE_SERVICE_KEY", ""))
    )
    ai = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY", st.secrets.get("GEMINI_API_KEY", ""))
    )
    return supabase, ai

supabase, ai = init_clients()

# Helper functions
def generate_embedding(text: str) -> list:
    response = ai.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )
    return response.embeddings[0].values

def search_transcripts(query: str, match_count: int = 5) -> list:
    query_vector = generate_embedding(query)
    result = supabase.rpc("search_transcripts", {
        "query_embedding": query_vector,
        "match_threshold": 0.3,
        "match_count": match_count,
    }).execute()
    return result.data or []

def generate_search_insights(query: str, results: list) -> str:
    if not results:
        return ""

    # Combine relevant content
    context = "\n\n---\n\n".join([
        f"From '{r['source_file']}':\n{r['content']}"
        for r in results[:5]
    ])

    response = ai.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Based on the user's question and the relevant audio transcript segments below, provide a helpful AI-generated answer.

**User's Question:** {query}

**Relevant Transcript Segments:**
{context}

**Instructions:**
- Directly answer the user's question using information from the transcripts
- Be concise but comprehensive
- If the transcripts don't fully answer the question, say what information is available
- Use bullet points for clarity when appropriate
- Mention which audio file(s) the information comes from

Provide your response in markdown format."""
    )
    return response.text

def get_all_files() -> list:
    result = supabase.from_("transcripts").select("source_file, created_at").execute()
    if not result.data:
        return []

    file_map = {}
    for row in result.data:
        if row["source_file"] not in file_map:
            file_map[row["source_file"]] = {"count": 0, "date": row["created_at"]}
        file_map[row["source_file"]]["count"] += 1

    return [{"name": k, "chunks": v["count"], "date": v["date"]} for k, v in file_map.items()]

def get_full_transcript(source_file: str) -> str:
    result = supabase.from_("transcripts").select("content").eq("source_file", source_file).order("created_at").execute()
    if not result.data:
        return ""
    return " ".join([r["content"] for r in result.data])

def summarize_transcript(source_file: str) -> str:
    transcript = get_full_transcript(source_file)
    if not transcript:
        return "No transcript found."

    response = ai.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Please provide a comprehensive summary of the following transcript in markdown format.

Structure it with:
## Overview
A brief 2-3 sentence overview

## Key Topics
- Bullet points of main topics

## Key Takeaways
- Important points and conclusions

## Action Items (if any)
- Any mentioned next steps or recommendations

Transcript:
{transcript}"""
    )
    return response.text

# Initialize session state
if "active_view" not in st.session_state:
    st.session_state.active_view = "search"
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None
if "current_summary" not in st.session_state:
    st.session_state.current_summary = None

# Get files
files = get_all_files()

# Sidebar - File list
with st.sidebar:
    st.header("🎧 Audio RAG")
    st.caption("Semantic search over audio transcriptions")

    st.divider()

    # Navigation
    st.subheader("📁 Your Audio Files")

    if files:
        for f in files:
            col1, col2 = st.columns([3, 1])
            with col1:
                display_name = f["name"][:25] + "..." if len(f["name"]) > 25 else f["name"]
                if st.button(f"🎵 {display_name}", key=f"file_{f['name']}", use_container_width=True):
                    st.session_state.selected_file = f["name"]
                    st.session_state.active_view = "file_detail"
                    st.session_state.current_summary = None
            with col2:
                st.caption(f"{f['chunks']} chunks")
    else:
        st.info("No audio files yet")

    st.divider()

    # Quick actions
    if st.button("🔍 Search", use_container_width=True):
        st.session_state.active_view = "search"
        st.session_state.selected_file = None

# Main content
if st.session_state.active_view == "search":
    st.title("🔍 Search Your Audio")
    st.markdown("Find specific topics, quotes, or discussions across all your transcriptions")

    # Search input
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("", placeholder="What was discussed about AI evaluation?", label_visibility="collapsed")
    with col2:
        num_results = st.selectbox("Results", [5, 10, 15, 20], label_visibility="collapsed")

    if query:
        with st.spinner("Searching your audio files..."):
            results = search_transcripts(query, num_results)

        if results:
            # AI Insights section
            st.markdown("### 🤖 AI Answer")
            with st.spinner("Generating insights..."):
                insights = generate_search_insights(query, results)

            st.markdown(f"""
            <div class="summary-container">
            {insights}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"### 📚 Source Segments ({len(results)} found)")
            st.caption("These are the transcript segments used to generate the answer above")

            for i, r in enumerate(results):
                with st.expander(f"📄 {r['source_file']} — {r['similarity']:.0%} match"):
                    st.markdown(f"> {r['content']}")
        else:
            st.warning("No results found. Try different keywords.")
    else:
        # Show recent files as suggestions
        if files:
            st.markdown("### 💡 Or explore your files")
            cols = st.columns(min(3, len(files)))
            for i, f in enumerate(files[:3]):
                with cols[i]:
                    if st.button(f"📂 {f['name'][:20]}...", key=f"quick_{f['name']}", use_container_width=True):
                        st.session_state.selected_file = f["name"]
                        st.session_state.active_view = "file_detail"
                        st.rerun()

elif st.session_state.active_view == "file_detail" and st.session_state.selected_file:
    selected = st.session_state.selected_file

    # Header
    st.title(f"🎵 {selected}")

    # File info
    file_info = next((f for f in files if f["name"] == selected), None)
    if file_info:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Chunks", file_info["chunks"])
        with col2:
            st.metric("Added", file_info["date"][:10])
        with col3:
            chars = len(get_full_transcript(selected))
            st.metric("Characters", f"{chars:,}")

    st.divider()

    # Action tabs
    tab1, tab2 = st.tabs(["📝 Summary", "📄 Full Transcript"])

    with tab1:
        if st.button("✨ Generate AI Summary", type="primary", use_container_width=True):
            with st.spinner("Generating summary with Gemini..."):
                st.session_state.current_summary = summarize_transcript(selected)

        if st.session_state.current_summary:
            st.markdown('<div class="summary-container">', unsafe_allow_html=True)
            st.markdown(st.session_state.current_summary)
            st.markdown('</div>', unsafe_allow_html=True)

            # Download button
            st.download_button(
                "📥 Download Summary",
                st.session_state.current_summary,
                file_name=f"{selected}_summary.md",
                mime="text/markdown"
            )
        else:
            st.info("Click the button above to generate an AI-powered summary of this audio file.")

    with tab2:
        transcript = get_full_transcript(selected)
        st.text_area("", transcript, height=500, label_visibility="collapsed")
        st.download_button(
            "📥 Download Transcript",
            transcript,
            file_name=f"{selected}_transcript.txt",
            mime="text/plain"
        )

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("[GitHub](https://github.com/matheusslg/mcp-audio-rag) • Built with Streamlit")
