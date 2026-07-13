import streamlit as st
import time
from dotenv import load_dotenv
from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TRANSCRIPT",
    page_icon="▌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

/* ── Root Variables ── */
:root {
    --paper:    #F5F3EE;
    --ink:      #0D0D0D;
    --ink-2:    #3A3A3A;
    --ink-3:    #888880;
    --rule:     #C8C4BB;
    --red:      #C8382A;
    --surface:  #EDEAE3;
    --serif:    'DM Serif Display', Georgia, serif;
    --mono:     'IBM Plex Mono', 'Courier New', monospace;
}

/* ── Reset ── */
html, body, [class*="css"] {
    font-family: var(--mono) !important;
    background-color: var(--paper) !important;
    color: var(--ink) !important;
}

.stApp { background: var(--paper) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--paper) !important;
    border-right: 2px solid var(--ink) !important;
}
[data-testid="stSidebar"] * { color: var(--ink) !important; }
[data-testid="stSidebar"] .block-container { padding-top: 2rem !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--paper); }
::-webkit-scrollbar-thumb { background: var(--rule); }

/* ── Typography ── */
h1, h2, h3 {
    font-family: var(--serif) !important;
    color: var(--ink) !important;
    font-weight: 400 !important;
}

/* ── Issue Line (top of sidebar) ── */
.issue-line {
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-3);
    border-bottom: 1px solid var(--rule);
    padding-bottom: 0.75rem;
    margin-bottom: 1.25rem;
}

/* ── Masthead ── */
.masthead {
    border-bottom: 3px solid var(--ink);
    padding-bottom: 0.5rem;
    margin-bottom: 0.3rem;
}

.masthead-title {
    font-family: var(--serif);
    font-size: clamp(2.8rem, 6vw, 5rem);
    font-weight: 400;
    line-height: 0.95;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin: 0;
}

.masthead-kicker {
    font-family: var(--mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--ink-3);
    margin-top: 0.5rem;
    margin-bottom: 0;
}

/* ── Folio (narrow rule label) ── */
.folio {
    font-family: var(--mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--red);
    margin-bottom: 0.25rem;
    display: block;
}

/* ── Section Rule ── */
.rule {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 1.5rem 0 !important;
}

.rule-heavy {
    border: none;
    border-top: 2px solid var(--ink);
    margin: 1.5rem 0 !important;
}

/* ── Pipeline Step (newspaper index style) ── */
.step-index {
    display: grid;
    grid-template-columns: 1.5rem 1fr auto;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.45rem 0;
    border-bottom: 1px dotted var(--rule);
    font-family: var(--mono);
    font-size: 0.75rem;
}

.step-num {
    font-weight: 600;
    color: var(--ink-3);
}

.step-label-active  { font-weight: 600; color: var(--ink); }
.step-label-done    { font-weight: 400; color: var(--ink-2); text-decoration: line-through; text-decoration-color: var(--rule); }
.step-label-pending { font-weight: 300; color: var(--ink-3); }

.step-status-active  { color: var(--red); font-weight: 600; }
.step-status-done    { color: var(--ink-3); }
.step-status-pending { color: var(--rule); }

@keyframes blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
}
.cursor { animation: blink 1s step-end infinite; }

/* ── Inputs — force light bg + dark text ── */
.stTextInput > div > div {
    background: var(--paper) !important;
}

.stTextInput > div > div > input,
.stTextInput input {
    background: var(--paper) !important;
    background-color: var(--paper) !important;
    -webkit-text-fill-color: var(--ink) !important;
    color: var(--ink) !important;
    caret-color: var(--ink) !important;
    border: none !important;
    border-bottom: 1.5px solid var(--ink) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    padding: 0.4rem 0.2rem !important;
    box-shadow: none !important;
}

.stTextInput > div > div > input:focus,
.stTextInput input:focus {
    border-bottom-color: var(--red) !important;
    box-shadow: none !important;
    background: var(--paper) !important;
    -webkit-text-fill-color: var(--ink) !important;
    color: var(--ink) !important;
}

.stTextInput > div > div > input::placeholder,
.stTextInput input::placeholder {
    color: var(--ink-3) !important;
    -webkit-text-fill-color: var(--ink-3) !important;
    font-style: italic;
    opacity: 1 !important;
}

/* Kill Chrome/Safari autofill dark bg */
.stTextInput input:-webkit-autofill,
.stTextInput input:-webkit-autofill:hover,
.stTextInput input:-webkit-autofill:focus,
.stTextInput input:-webkit-autofill:active {
    -webkit-box-shadow: 0 0 0 1000px var(--paper) inset !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--ink) !important;
    transition: background-color 5000s ease-in-out 0s;
}

/* ── File Uploader — match paper theme, compact size ── */
[data-testid="stFileUploader"] {
    background: transparent !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: var(--paper) !important;
    background-color: var(--paper) !important;
    border: 1.5px dashed var(--rule) !important;
    border-radius: 0 !important;
    padding: 0.6rem 0.75rem !important;
    min-height: unset !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--ink) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] {
    color: var(--ink) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div {
    color: var(--ink-2) !important;
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] svg {
    fill: var(--ink-3) !important;
}
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stBaseButton-secondary"] {
    background: var(--paper) !important;
    color: var(--ink) !important;
    border: 1px solid var(--ink) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
    padding: 0.25rem 0.6rem !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
    background: var(--ink) !important;
    color: var(--paper) !important;
}
[data-testid="stFileUploaderFile"] {
    background: var(--paper) !important;
    color: var(--ink) !important;
    font-family: var(--mono) !important;
    font-size: 0.7rem !important;
}
[data-testid="stFileUploaderFileName"] {
    color: var(--ink) !important;
}

/* Selectbox — same treatment */
.stSelectbox > div > div {
    background: var(--paper) !important;
    background-color: var(--paper) !important;
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    border: none !important;
    border-bottom: 1.5px solid var(--ink) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    box-shadow: none !important;
}
.stSelectbox * {
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
}

/* Selectbox dropdown menu */
div[data-baseweb="select"] > div {
    background: var(--paper) !important;
    color: var(--ink) !important;
}
div[data-baseweb="popover"] {
    background: var(--paper) !important;
}
div[data-baseweb="popover"] * {
    background: var(--paper) !important;
    color: var(--ink) !important;
}

/* ── Button ── */
.stButton > button {
    background: var(--ink) !important;
    color: var(--paper) !important;
    -webkit-text-fill-color: var(--paper) !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-weight: 600 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 1.5rem !important;
    transition: background 0.15s !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: var(--red) !important;
}

/* ── Content Cards (ruled sections) ── */
.press-section {
    border-top: 2px solid var(--ink);
    padding-top: 0.75rem;
    margin-bottom: 1.5rem;
}

.press-section-label {
    font-family: var(--mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--red);
    margin-bottom: 0.6rem;
}

.press-section-title {
    font-family: var(--serif);
    font-size: 1.6rem;
    line-height: 1.1;
    color: var(--ink);
    margin-bottom: 0.75rem;
}

.press-body {
    font-family: var(--mono);
    font-size: 0.8rem;
    line-height: 1.9;
    color: var(--ink-2);
}

/* ── Transcript box ── */
.transcript-raw {
    font-family: var(--mono);
    font-size: 0.75rem;
    line-height: 1.8;
    color: var(--ink-3);
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
    border-left: 2px solid var(--rule);
    padding-left: 1rem;
    margin-top: 0.5rem;
}

/* ── Chat ── */
.chat-scroll {
    max-height: 360px;
    overflow-y: auto;
    margin-bottom: 1rem;
    padding-right: 0.5rem;
}

.chat-entry {
    display: grid;
    grid-template-columns: 4rem 1fr;
    gap: 0.5rem;
    padding: 0.65rem 0;
    border-bottom: 1px dotted var(--rule);
    align-items: start;
}

.chat-gutter {
    font-family: var(--mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding-top: 0.15rem;
}

.chat-gutter-you { color: var(--red); }
.chat-gutter-ai  { color: var(--ink-3); }

.chat-text {
    font-family: var(--mono);
    font-size: 0.82rem;
    line-height: 1.7;
    color: var(--ink-2);
}

/* ── Empty state ── */
.empty-state {
    padding: 5rem 0 4rem;
    border-top: 2px solid var(--ink);
}

.empty-headline {
    font-family: var(--serif);
    font-size: clamp(2rem, 4vw, 3.2rem);
    font-weight: 400;
    font-style: italic;
    color: var(--ink);
    line-height: 1.15;
    max-width: 600px;
}

.empty-deck {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--ink-3);
    line-height: 1.8;
    margin-top: 1rem;
    max-width: 420px;
}

.tag-row {
    display: flex;
    gap: 1.5rem;
    margin-top: 2rem;
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-3);
}

.tag-row span::before { content: "— "; }

/* ── Overrides for Streamlit chrome ── */
.stProgress > div > div > div { background: var(--ink) !important; }
.stSpinner > div { border-top-color: var(--ink) !important; }
[data-testid="stMarkdownContainer"] p {
    font-family: var(--mono) !important;
    color: var(--ink-2) !important;
    font-size: 0.82rem !important;
    line-height: 1.8 !important;
}
label {
    font-family: var(--mono) !important;
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: var(--ink-3) !important;
}

/* Alert override */
.stAlert {
    background: var(--surface) !important;
    border: 1px solid var(--rule) !important;
    border-left: 3px solid var(--ink) !important;
    border-radius: 0 !important;
    color: var(--ink) !important;
}

div[data-testid="stExpander"] {
    border: none !important;
    border-top: 1px solid var(--rule) !important;
    border-radius: 0 !important;
    background: transparent !important;
}

div[data-testid="stExpander"] summary {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--ink-3) !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Helpers ────────────────────────────────────────────────────────────────────
STEPS = [
    ("audio",      "Audio extraction"),
    ("transcript", "Transcription"),
    ("title",      "Title generation"),
    ("summary",    "Summarisation"),
    ("extract",    "Intelligence extraction"),
    ("rag",        "RAG index build"),
]

def build_pipeline_html():
    html = ""
    for i, (key, label) in enumerate(STEPS, 1):
        state = st.session_state.pipeline_steps.get(key, "pending")
        lbl_cls = f"step-label-{state}"
        if state == "active":
            status_html = '<span class="step-status-active cursor">▌</span>'
        elif state == "done":
            status_html = '<span class="step-status-done">✓</span>'
        else:
            status_html = '<span class="step-status-pending">·</span>'

        html += f"""
        <div class="step-index">
            <span class="step-num">{i:02d}</span>
            <span class="{lbl_cls}">{label}</span>
            {status_html}
        </div>"""
    return html

def render_pipeline_index():
    st.markdown(build_pipeline_html(), unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    from datetime import datetime
    today = datetime.now().strftime("%d %b %Y").upper()
    st.markdown(f'<div class="issue-line">Vol. I &nbsp;·&nbsp; {today} &nbsp;·&nbsp; Meeting Intelligence</div>', unsafe_allow_html=True)

    st.markdown('<span style="font-family:\'DM Serif Display\',serif;font-size:1.5rem;line-height:1.1;color:#0D0D0D">TRANSCRIPT</span>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#888880;margin-bottom:1.5rem;border-bottom:1px solid #C8C4BB;padding-bottom:0.75rem">AI Video Assistant</div>', unsafe_allow_html=True)

    st.markdown('<span class="folio">Input</span>', unsafe_allow_html=True)
    source = st.text_input(
        "URL / PATH",
        placeholder="youtube.com/watch?v=... or /file.mp4"
    )

    st.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.65rem;color:#888880;text-align:center;margin:0.5rem 0;letter-spacing:0.1em;text-transform:uppercase">— or —</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Audio / Video",
        type=["mp3", "wav", "mp4", "m4a", "mov", "webm", "mkv"],
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        import tempfile, os as _os
        suffix = _os.path.splitext(uploaded_file.name)[1]
        _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        _tmp.write(uploaded_file.read())
        _tmp.close()
        source = _tmp.name
        st.markdown(f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.65rem;color:#0D0D0D;margin-top:0.25rem">✓ {uploaded_file.name}</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    language = st.selectbox("Language", ["english", "hinglish"], index=0)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    run_btn = st.button("▶  Run Analysis")

    # Pipeline always rendered into a placeholder so we can update it live
    st.markdown('<div style="height:1.25rem"></div>', unsafe_allow_html=True)
    st.markdown('<span class="folio">Pipeline</span>', unsafe_allow_html=True)
    pipeline_placeholder = st.empty()

    if st.session_state.pipeline_steps:
        with pipeline_placeholder.container():
            render_pipeline_index()

# ─── Main Area ──────────────────────────────────────────────────────────────────

# Masthead
st.markdown("""
<div class="masthead">
    <div class="masthead-kicker">AI Video Assistant &nbsp;·&nbsp; Meeting Intelligence</div>
    <div class="masthead-title">TRANSCRIPT</div>
</div>
<div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#888880;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.25rem">
    Transcribe &nbsp;&nbsp;·&nbsp;&nbsp; Summarise &nbsp;&nbsp;·&nbsp;&nbsp; Chat with your meetings
</div>
<hr class="rule-heavy" style="margin-top:0.75rem !important;">
""", unsafe_allow_html=True)

# ── Run Pipeline ────────────────────────────────────────────────────────────────
if run_btn:
    if not source.strip():
        st.error("Enter a YouTube URL or file path to continue.")
    else:
        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {k: "pending" for k, _ in STEPS}

        progress_placeholder = st.empty()

        def update_step(key, state):
            st.session_state.pipeline_steps[key] = state
            # Live-redraw the sidebar pipeline
            with pipeline_placeholder.container():
                render_pipeline_index()

        # Paint initial pending list immediately
        with pipeline_placeholder.container():
            render_pipeline_index()

        try:
            with progress_placeholder.container():
                st.info("Pipeline running — live status in sidebar")

            update_step("audio", "active")
            chunks = process_input(source)
            update_step("audio", "done")

            update_step("transcript", "active")
            transcript = transcribe_all(chunks, language)
            update_step("transcript", "done")

            update_step("title", "active")
            title = generate_title(transcript)
            update_step("title", "done")

            update_step("summary", "active")
            summary = summarize(transcript)
            update_step("summary", "done")

            update_step("extract", "active")
            action_items = extract_action_items(transcript)
            decisions    = extract_key_decisions(transcript)
            questions    = extract_questions(transcript)
            update_step("extract", "done")

            update_step("rag", "active")
            rag_chain = build_rag_chain(transcript)
            update_step("rag", "done")

            st.session_state.result = {
                "title":          title,
                "transcript":     transcript,
                "summary":        summary,
                "action_items":   action_items,
                "key_decisions":  decisions,
                "open_questions": questions,
                "rag_chain":      rag_chain,
            }
            st.session_state.pipeline_done = True
            progress_placeholder.success("Analysis complete.")
            time.sleep(0.4)
            progress_placeholder.empty()
            st.rerun()

        except Exception as e:
            for k, _ in STEPS:
                if st.session_state.pipeline_steps.get(k) == "active":
                    st.session_state.pipeline_steps[k] = "pending"
            with pipeline_placeholder.container():
                render_pipeline_index()
            progress_placeholder.error(f"Error: {e}")

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # ── Title banner ──
    st.markdown(f"""
    <div class="press-section">
        <div class="press-section-label">Session</div>
        <div class="press-section-title">{r['title']}</div>
    </div>""", unsafe_allow_html=True)

    # ── Summary + Transcript ──
    col1, col2 = st.columns([3, 2], gap="large")

    with col1:
        st.markdown(f"""
        <div class="press-section">
            <div class="press-section-label">Summary</div>
            <div class="press-body">{r['summary']}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        with st.expander("Full Transcript"):
            st.markdown(f'<div class="transcript-raw">{r["transcript"]}</div>', unsafe_allow_html=True)

    # ── Three-column intel ──
    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown(f"""
        <div class="press-section">
            <div class="press-section-label">Action Items</div>
            <div class="press-body">{r['action_items']}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="press-section">
            <div class="press-section-label">Key Decisions</div>
            <div class="press-body">{r['key_decisions']}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="press-section">
            <div class="press-section-label">Open Questions</div>
            <div class="press-body">{r['open_questions']}</div>
        </div>""", unsafe_allow_html=True)

    # ── RAG Chat ──
    st.markdown('<hr class="rule-heavy" style="margin-top:0.5rem !important;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;font-weight:400;color:#0D0D0D;margin-bottom:0.25rem">
        Ask the transcript
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.65rem;color:#888880;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:1rem">
        RAG-powered Q&A
    </div>""", unsafe_allow_html=True)

    # Chat history
    if st.session_state.chat_history:
        chat_html = '<div class="chat-scroll">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f"""
                <div class="chat-entry">
                    <span class="chat-gutter chat-gutter-you">You</span>
                    <span class="chat-text">{msg['content']}</span>
                </div>"""
            else:
                chat_html += f"""
                <div class="chat-entry">
                    <span class="chat-gutter chat-gutter-ai">AI</span>
                    <span class="chat-text">{msg['content']}</span>
                </div>"""
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:1.5rem 0;border-top:1px dotted #C8C4BB;border-bottom:1px dotted #C8C4BB;margin-bottom:1rem">
            <span style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;font-style:italic;color:#888880">
                No questions yet. Ask anything about the meeting above.
            </span>
        </div>""", unsafe_allow_html=True)

    # Chat input
    chat_col1, chat_col2 = st.columns([5, 1], gap="small")
    with chat_col1:
        user_input = st.text_input(
            "Question",
            placeholder="What were the main decisions made?",
            label_visibility="collapsed"
        )
    with chat_col2:
        send_btn = st.button("Send →")

    if send_btn and user_input.strip():
        with st.spinner(""):
            answer = ask_question(r["rag_chain"], user_input.strip())
        st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear chat", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

else:
    # ── Empty / landing state ──
    st.markdown("""
    <div class="empty-state">
        <div class="empty-headline">
            Every meeting deserves<br>a paper trail.
        </div>
        <div class="empty-deck">
            Paste a YouTube URL or local video path into the sidebar.
            Choose your language. Hit Run.<br><br>
            The pipeline transcribes, summarises, extracts decisions,
            and indexes the full transcript for conversation.
        </div>
        <div class="tag-row">
            <span>Transcription</span>
            <span>Summarisation</span>
            <span>RAG Chat</span>
            <span>Action Items</span>
        </div>
    </div>""", unsafe_allow_html=True)