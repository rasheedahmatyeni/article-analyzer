import streamlit as st
import os
import re
import json
import requests
import pandas as pd
import plotly.express as px
from openrouter import OpenRouter
from pypdf import PdfReader
from docx import Document

st.set_page_config(page_title="Article Analyzer", page_icon="📰", layout="centered")

# Color tokens. Indigo is the primary "pop" accent (buttons, tabs, headings); amber is the
# secondary highlight (used sparingly). Sentiment colors stay separate and meaningful - they're
# reused consistently across metric cards, badges, and the charts on the YouTube tab.
INDIGO = "#6C4FF6"
INDIGO_DARK = "#5636D9"
AMBER = "#FFB020"
INK = "#1B1E2B"
SENTIMENT_COLORS = {"Positive": "#2E7D32", "Neutral": "#5A5D6B", "Negative": "#C62828"}
SENTIMENT_TINTS = {"Positive": "#E8F5E9", "Neutral": "#EEEEF2", "Negative": "#FDECEA"}

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&display=swap');

    .stApp {{ background-color: #FAFAFF; }}

    h1, h2, h3, .stTabs [data-baseweb="tab"] p {{
        font-family: 'Sora', sans-serif !important;
        color: {INK};
    }}
    h1 {{ font-weight: 800 !important; }}
    h2, h3 {{ font-weight: 700 !important; }}

    /* Signature gradient bar across the top of the app */
    .accent-bar {{
        height: 6px;
        width: 100%;
        border-radius: 6px;
        background: linear-gradient(90deg, {INDIGO} 0%, {AMBER} 100%);
        margin-bottom: 1.4rem;
    }}

    .stButton>button, .stDownloadButton>button {{
        background: linear-gradient(90deg, {INDIGO} 0%, {INDIGO_DARK} 100%);
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(108, 79, 246, 0.25);
    }}
    .stButton>button:hover, .stDownloadButton>button:hover {{
        background: linear-gradient(90deg, {INDIGO_DARK} 0%, {INDIGO_DARK} 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(108, 79, 246, 0.35);
    }}

    div[data-testid="stMetric"] {{
        background-color: #F1EEFE;
        padding: 10px;
        border-radius: 10px;
        border-left: 4px solid {INDIGO};
    }}

    /* Tabs: indigo underline + label on the active tab */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [aria-selected="true"] {{
        color: {INDIGO} !important;
        border-bottom-color: {INDIGO} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ background-color: {INDIGO} !important; }}

    .sentiment-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 999px;
        font-weight: 700;
        font-family: 'Sora', sans-serif;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="accent-bar"></div>', unsafe_allow_html=True)

# Load API keys from Streamlit secrets (or environment as a fallback for local runs)
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))

# Fast, cost-effective models offered for comment sentiment + summary generation
SENTIMENT_MODELS = {
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "Claude 3.5 Haiku": "anthropic/claude-3.5-haiku",
    "DeepSeek R1": "deepseek/deepseek-r1",
}



# Shared guidance used by every sentiment classifier in the app. The key fix here: emotional tone
# (sadness, nostalgia, crying) is NOT the same as negative sentiment - a comment can be sad AND
# supportive, which is Positive. But this cuts both ways: don't default everything with warmth or
# fandom language to Positive either. Real criticism, complaints, and requests framed politely are
# still Negative, and plain factual or ambiguous comments are still Neutral.
SENTIMENT_GUIDANCE = (
    "Classify SENTIMENT - the writer's underlying stance or opinion toward the subject - not just the "
    "emotional tone of their words. Apply this in BOTH directions:\n\n"
    "1) Sadness, grief, nostalgia, tears, or missing someone are NOT automatically Negative. If the "
    "writer is sad but still supportive, loving, proud, or hopeful, that is Positive.\n"
    "2) But do not default everything emotional or fan-toned to Positive either. A comment can be "
    "polite, warm, or use affectionate language and still be Negative if it expresses a complaint, "
    "criticism, unmet expectation, or a request for something to be fixed/improved. Look for the "
    "actual grievance underneath the tone.\n"
    "3) Use Neutral for purely factual statements, questions, or comments with no discernible praise "
    "or complaint either way. Not every comment has to be Positive - a realistic set of comments on "
    "any video should include some Neutral and some Negative ones. Do not force a Positive label just "
    "because the video's topic is emotional.\n"
    "4) A worried or concerned observation about a PERSON in the video (e.g. noting they seem quiet, "
    "tired, or subdued) is usually Neutral, not Negative - it's an observation, not a complaint about "
    "the content, unless the writer also criticizes the video/creators. Likewise, a sad-looking emoji "
    "(😟, :() attached to a purely factual correction or clarification does NOT make the comment "
    "Negative - judge the actual sentence content, not just whether an emoji looks sad. Reserve "
    "Negative for comments that actually criticize, complain about, or express displeasure with the "
    "content, creators, or subject - not for every comment that merely mentions something sad or "
    "expresses concern.\n\n"
    "Examples:\n"
    "- \"I'll miss him so much, fighting Hobi! We'll wait for you\" -> Positive (sad but supportive)\n"
    "- \"Seeing him cry broke my heart, love you J-Hope\" -> Positive (emotional but affectionate)\n"
    "- \"This video was boring and way too long\" -> Negative (direct criticism)\n"
    "- \"Please add English subtitles next time, hard to follow without them\" -> Negative (a "
    "complaint/request, even though it's polite)\n"
    "- \"This was too much to watch, I wish they'd shown something lighter instead\" -> Negative "
    "(criticism of content choice, despite emotional framing)\n"
    "- \"He enlists next month\" -> Neutral (factual, no clear stance)\n"
    "- \"What song is playing in the background?\" -> Neutral (a question, no stance)\n"
    "- \"I don't like how they edited this, feels rushed\" -> Negative (criticism of the content)\n"
    "- \"Jin is quiet again 😟\" -> Neutral (a concerned observation about a person, not a complaint "
    "about the video)\n"
    "- \"3:03 embarrassing everyone ❌ getting embarrassed by everyone ✅\" -> Neutral (a factual "
    "correction using emoji as right/wrong markers, not an expression of sentiment)"
)


def sentiment_badge_html(label):
    """A small colored pill for a sentiment label, falling back to gray for unknown/error states."""
    color = SENTIMENT_COLORS.get(label, "#5A5D6B")
    tint = SENTIMENT_TINTS.get(label, "#EEEEF2")
    text = label if label else "N/A"
    return (
        f'<span class="sentiment-badge" style="background-color:{tint}; color:{color};">'
        f"{text}</span>"
    )


def analyze_sentiment(text):
    """Classify article-level sentiment via an LLM, using the same tone-vs-stance guidance as comments.

    Returns a dict: {"sentiment": str, "reason": str, "sensitive": bool}. When "sensitive" is True,
    the sentiment label describes the writing's tone/stance only - never an endorsement of the topic
    itself (e.g. a well-written academic paper on assault can be "Positive" in tone while the subject
    matter remains serious; that distinction needs to be visible, not buried in a reasoning sentence).
    """
    if not text.strip():
        return {"sentiment": "", "reason": "Please enter some text to analyze.", "sensitive": False}
    if not OPENROUTER_API_KEY:
        return {"sentiment": "", "reason": "Error: OPENROUTER_API_KEY not set. Please add it to your Streamlit secrets.", "sensitive": False}

    system_prompt = (
        "You are a sentiment classification engine for article text. " + SENTIMENT_GUIDANCE +
        "\n\nAlso flag SENSITIVE TOPICS. If the subject matter involves violence, abuse, assault, "
        "trauma, death, self-harm, or other serious/distressing subject matter - regardless of how "
        "constructive, academic, or measured the writing's tone is - mark it as sensitive. A "
        "Positive/Negative label on such content always describes the writing's tone or stance only, "
        "never an endorsement of the topic, and this needs to be flagged explicitly rather than left "
        "implicit.\n\n"
        "Respond in exactly this format and nothing else:\n"
        "Sentiment: <Positive/Negative/Neutral>\n"
        "Sensitive: <Yes/No>\n"
        "Reason: <one short sentence explaining the stance, not just the tone>"
    )

    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        response = client.chat.send(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:3000]},
            ],
            stream=False,
        )
    raw = response.choices[0].message.content.strip()

    sentiment, sensitive, reason = "Unknown", False, raw
    for line in raw.splitlines():
        if line.lower().startswith("sentiment:"):
            sentiment = line.split(":", 1)[1].strip()
        elif line.lower().startswith("sensitive:"):
            sensitive = line.split(":", 1)[1].strip().lower().startswith("y")
        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()

    return {"sentiment": sentiment, "reason": reason, "sensitive": sensitive}


def summarize_with_llm(text):
    if not text.strip():
        return "Please enter some text to summarize."
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not set. Please add it to your Streamlit secrets."

    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        response = client.chat.send(
            model="openrouter/free",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Summarize the following text concisely in 2-3 sentences.",
                },
                {"role": "user", "content": text},
            ],
            stream=False,
        )
    return response.choices[0].message.content


def full_analysis(text):
    if not text.strip():
        return {"sentiment": "", "reason": "Please enter some text to analyze.", "sensitive": False}, ""
    return analyze_sentiment(text), summarize_with_llm(text)


def word_and_reading_stats(text):
    if not text.strip():
        return "0 words · 0 min read"
    word_count = len(text.split())
    reading_minutes = max(1, round(word_count / 200))
    return f"{word_count} words · ~{reading_minutes} min read"


def load_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return ""
    extension = uploaded_file.name.lower().rsplit(".", 1)[-1]

    if extension == "txt":
        return uploaded_file.read().decode("utf-8")
    elif extension == "pdf":
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    elif extension == "docx":
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    else:
        return "Unsupported file type."


def extract_video_id(url):
    """Pull the 11-character YouTube video ID out of common URL formats."""
    if not url:
        return None
    patterns = [
        r"(?:v=|/embed/|/shorts/)([0-9A-Za-z_-]{11})",
        r"youtu\.be/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_youtube_comments(video_id, max_results=50):
    """Fetch top-level comments for a video via the official YouTube Data API v3."""
    if not YOUTUBE_API_KEY:
        return None, "Error: YOUTUBE_API_KEY not set. Please add it to your Streamlit secrets."

    comments = []
    endpoint = "https://www.googleapis.com/youtube/v3/commentThreads"
    page_token = None

    try:
        while len(comments) < max_results:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(100, max_results - len(comments)),
                "order": "relevance",
                "textFormat": "plainText",
                "key": YOUTUBE_API_KEY,
            }
            if page_token:
                params["pageToken"] = page_token

            response = requests.get(endpoint, params=params, timeout=15)
            if response.status_code == 403:
                return None, "Error: Comments are disabled for this video, or the API key lacks permission."
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet.get("authorDisplayName", "Unknown"),
                    "text": snippet.get("textDisplay", ""),
                    "likes": snippet.get("likeCount", 0),
                    "published_at": snippet.get("publishedAt", ""),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching comments: {e}"

    return comments, None


def classify_comments_sentiment(comments, model, batch_size=25):
    """Classify each comment as Positive/Negative/Neutral using an OpenRouter LLM, in batches."""
    if not comments:
        return comments
    if not OPENROUTER_API_KEY:
        for c in comments:
            c["sentiment"] = "Unknown"
        return comments

    system_prompt = (
        "You are a sentiment classification engine for YouTube comments. For each numbered comment, "
        "classify it as exactly one of: Positive, Negative, or Neutral.\n\n" + SENTIMENT_GUIDANCE +
        '\n\nRespond ONLY with a JSON array of objects like [{"index": 0, "sentiment": "Positive"}] '
        "and nothing else - no markdown, no preamble."
    )

    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        for start in range(0, len(comments), batch_size):
            batch = comments[start:start + batch_size]
            numbered = "\n".join(f"{i}. {c['text'][:500]}" for i, c in enumerate(batch))

            try:
                response = client.chat.send(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": numbered},
                    ],
                    stream=False,
                )
                raw = response.choices[0].message.content.strip()
                raw = raw.replace("```json", "").replace("```", "").strip()
                results = json.loads(raw)
                sentiment_map = {r["index"]: r["sentiment"] for r in results}
            except (json.JSONDecodeError, KeyError, TypeError, IndexError, AttributeError):
                sentiment_map = {}

            for i, c in enumerate(batch):
                c["sentiment"] = sentiment_map.get(i, "Neutral")

    return comments


def generate_executive_summary(comments, model):
    """Generate an AI executive summary of audience feedback: overview, praise, and pain points."""
    if not comments:
        return "No comments to summarize."
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not set. Please add it to your Streamlit secrets."

    sentiment_counts = pd.Series([c.get("sentiment", "Unknown") for c in comments]).value_counts().to_dict()
    sample = "\n".join(f"- [{c.get('sentiment', 'Unknown')}] {c['text'][:200]}" for c in comments[:60])

    system_prompt = (
        "You are a business analyst summarizing YouTube audience feedback for an executive audience. "
        "Given a set of comments with sentiment labels, write a concise executive summary with three "
        "sections using markdown headers: '### Overview' (2-3 sentences), '### Main Praise' (bullet "
        "points), and '### Major Complaints / Pain Points' (bullet points). Be specific and actionable."
    )
    user_prompt = f"Sentiment breakdown: {sentiment_counts}\n\nComments:\n{sample}"

    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        response = client.chat.send(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
        )
    return response.choices[0].message.content


SAMPLE_ARTICLES = {
    "Sample: AI in Industry": """Artificial intelligence is transforming industries worldwide. From healthcare to finance, organizations are deploying machine learning models to automate tasks, improve decision-making, and uncover insights from vast datasets. In healthcare, AI systems can now detect certain cancers from medical images with accuracy rivaling experienced radiologists. Financial institutions use AI to detect fraud in real time, saving billions of dollars annually. The transportation sector is being reshaped by autonomous vehicles that rely on deep learning to navigate complex environments. Meanwhile, natural language processing breakthroughs have enabled virtual assistants and translation tools that were unimaginable a decade ago. Despite these advances, challenges remain around data privacy, algorithmic bias, and the displacement of workers in certain sectors. Policymakers, researchers, and industry leaders are working to establish frameworks that ensure AI development proceeds responsibly and equitably.""",
    "Sample: Community News": """The local community center celebrated its 20th anniversary this weekend with a series of events that brought together hundreds of residents. Organizers praised the turnout, noting that the center has become a vital hub for youth programs, elder support services, and cultural celebrations over the past two decades. Volunteers set up food stalls, live music, and children's activities throughout the day. Several long-time members shared stories about how the center helped them through difficult times, from job loss to family struggles. City officials attended the event and announced a new grant that will fund an expansion of the center's after-school tutoring program next year.""",
    "Sample: Negative Review": """The restaurant's service was disappointingly slow, and our order arrived nearly forty minutes after we requested it. When the food finally came, it was lukewarm and clearly not freshly prepared. Several dishes were missing ingredients that were listed on the menu, and when we raised this with the staff, we were met with indifference rather than an apology. The prices, given the quality and experience, felt entirely unjustified. We left the restaurant frustrated and would not recommend it to others looking for a reliable dining experience.""",
}


st.title("Article Analyzer")
st.write("Paste any article to get AI-powered sentiment analysis and summarization.")

tab1, tab2, tab3, tab4 = st.tabs(["Summarize", "Sentiment Analysis", "Full Analysis", "YouTube Insights"])

# ---------- Summarize tab ----------
with tab1:
    if "summary_area" not in st.session_state:
        st.session_state.summary_area = ""

    st.write("**Try a sample:**")
    cols = st.columns(3)
    for i, (name, text) in enumerate(SAMPLE_ARTICLES.items()):
        if cols[i].button(name, key=f"sample_summary_{i}"):
            st.session_state.summary_area = text

    uploaded = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_summary")
    if uploaded is not None:
        st.session_state.summary_area = load_uploaded_file(uploaded)

    summary_input = st.text_area("Article Text", height=200, key="summary_area")
    st.caption(word_and_reading_stats(summary_input))

    def clear_summary_tab():
        st.session_state.summary_area = ""

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run_summarize = st.button("Summarize", type="primary")
    with col_clear:
        st.button("Clear", key="clear_summary", on_click=clear_summary_tab)

    if run_summarize:
        with st.spinner("Summarizing..."):
            result = summarize_with_llm(summary_input)
        st.text_area("Summary", value=result, height=150)
        st.download_button("Download Summary", data=result, file_name="summary_result.txt")

# ---------- Sentiment Analysis tab ----------
with tab2:
    if "sentiment_area" not in st.session_state:
        st.session_state.sentiment_area = ""

    uploaded_s = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_sentiment")
    if uploaded_s is not None:
        st.session_state.sentiment_area = load_uploaded_file(uploaded_s)

    sentiment_input = st.text_area("Article Text", height=200, key="sentiment_area")
    st.caption(word_and_reading_stats(sentiment_input))

    def clear_sentiment_tab():
        st.session_state.sentiment_area = ""

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run_sentiment = st.button("Analyze Sentiment", type="primary")
    with col_clear:
        st.button("Clear", key="clear_sentiment", on_click=clear_sentiment_tab)

    if run_sentiment:
        with st.spinner("Analyzing..."):
            result = analyze_sentiment(sentiment_input)
        if result["sensitive"]:
            st.warning(
                "This text touches on a sensitive topic (violence, abuse, trauma, or similar). "
                "The sentiment label below reflects the tone/stance of the writing only - it is not "
                "a judgment on the subject matter itself."
            )
        display_text = f"Sentiment: {result['sentiment']}\nReason: {result['reason']}"
        st.markdown(sentiment_badge_html(result["sentiment"]), unsafe_allow_html=True)
        st.text_area("Sentiment Result", value=display_text, height=80)

# ---------- Full Analysis tab ----------
with tab3:
    if "full_area" not in st.session_state:
        st.session_state.full_area = ""

    uploaded_f = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_full")
    if uploaded_f is not None:
        st.session_state.full_area = load_uploaded_file(uploaded_f)

    full_input = st.text_area("Article Text", height=200, key="full_area")
    st.caption(word_and_reading_stats(full_input))

    def clear_full_tab():
        st.session_state.full_area = ""

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run_full = st.button("Run Full Analysis", type="primary")
    with col_clear:
        st.button("Clear", key="clear_full", on_click=clear_full_tab)

    if run_full:
        with st.spinner("Running full analysis..."):
            sentiment_result, summary_result = full_analysis(full_input)

        if sentiment_result.get("sensitive"):
            st.warning(
                "This text touches on a sensitive topic (violence, abuse, trauma, or similar). "
                "The sentiment label reflects the tone/stance of the writing only - it is not a "
                "judgment on the subject matter itself."
            )

        sentiment_display = f"Sentiment: {sentiment_result['sentiment']}\nReason: {sentiment_result['reason']}"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(sentiment_badge_html(sentiment_result["sentiment"]), unsafe_allow_html=True)
            st.text_area("Sentiment", value=sentiment_display, height=150)
        with col2:
            st.text_area("Summary", value=summary_result, height=150)

        combined = f"--- SENTIMENT ---\n{sentiment_display}\n\n--- SUMMARY ---\n{summary_result}"
        st.download_button("Download Full Results", data=combined, file_name="full_analysis_result.txt")

# ---------- YouTube Insights tab ----------
with tab4:
    st.write("Paste a YouTube video link to pull public comments and analyze audience sentiment.")

    yt_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...", key="yt_url")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        model_choice = st.selectbox("Sentiment / Summary Model", list(SENTIMENT_MODELS.keys()), key="yt_model")
    with col_b:
        max_comments = st.slider("Max comments", 10, 100, 50, step=10, key="yt_max")

    def clear_youtube_tab():
        st.session_state.yt_url = ""
        st.session_state.pop("yt_comments", None)
        st.session_state.pop("yt_summary", None)

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run_youtube = st.button("Analyze YouTube Comments", type="primary")
    with col_clear:
        st.button("Clear", key="clear_youtube", on_click=clear_youtube_tab)

    if run_youtube:
        video_id = extract_video_id(yt_url)
        if not video_id:
            st.error("Couldn't find a valid YouTube video ID in that link.")
        else:
            with st.spinner("Fetching comments from YouTube..."):
                comments, error = fetch_youtube_comments(video_id, max_results=max_comments)

            if error:
                st.error(error)
            elif not comments:
                st.warning("No comments found for this video — they may be disabled.")
            else:
                model_id = SENTIMENT_MODELS[model_choice]
                with st.spinner("Classifying comment sentiment..."):
                    comments = classify_comments_sentiment(comments, model_id)
                with st.spinner("Generating executive summary..."):
                    summary = generate_executive_summary(comments, model_id)

                st.session_state.yt_comments = comments
                st.session_state.yt_summary = summary

    if st.session_state.get("yt_comments"):
        comments = st.session_state.yt_comments
        df = pd.DataFrame(comments)

        st.subheader("Executive Summary")
        st.markdown(st.session_state.yt_summary)

        st.subheader("Sentiment Breakdown")
        counts = df["sentiment"].value_counts()

        def sentiment_card(label, value):
            color = SENTIMENT_COLORS[label]
            tint = SENTIMENT_TINTS[label]
            return f"""
                <div style="background-color:{tint}; border-left:4px solid {color};
                            border-radius:10px; padding:14px 16px;">
                    <div style="color:{color}; font-weight:700; font-size:0.85rem;
                                text-transform:uppercase; letter-spacing:0.03em;">{label}</div>
                    <div style="color:{INK}; font-size:1.8rem; font-weight:800;
                                font-family:'Sora', sans-serif;">{value}</div>
                </div>
            """

        c1, c2, c3 = st.columns(3)
        c1.markdown(sentiment_card("Positive", int(counts.get("Positive", 0))), unsafe_allow_html=True)
        c2.markdown(sentiment_card("Neutral", int(counts.get("Neutral", 0))), unsafe_allow_html=True)
        c3.markdown(sentiment_card("Negative", int(counts.get("Negative", 0))), unsafe_allow_html=True)
        st.write("")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            pie_df = counts.reindex(["Positive", "Neutral", "Negative"]).fillna(0).reset_index()
            pie_df.columns = ["Sentiment", "Count"]
            pie_df = pie_df[pie_df["Count"] > 0]
            if not pie_df.empty:
                fig_pie = px.pie(
                    pie_df, names="Sentiment", values="Count",
                    color="Sentiment", color_discrete_map=SENTIMENT_COLORS, hole=0.45,
                )
                fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            timeline_df = df.copy()
            timeline_df["published_at"] = pd.to_datetime(timeline_df["published_at"], errors="coerce")
            timeline_df = timeline_df.dropna(subset=["published_at"])
            if not timeline_df.empty and timeline_df["published_at"].dt.date.nunique() > 1:
                timeline_df["date"] = timeline_df["published_at"].dt.date
                trend = timeline_df.groupby(["date", "sentiment"]).size().reset_index(name="count")
                fig_line = px.line(
                    trend, x="date", y="count", color="sentiment",
                    color_discrete_map=SENTIMENT_COLORS, markers=True,
                )
                fig_line.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10), height=300,
                    xaxis_title="", yaxis_title="Comments", legend_title="",
                )
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.caption("Not enough date spread in these comments to show a trend line.")

        st.subheader("Comments")
        sentiment_filter = st.multiselect(
            "Filter by sentiment",
            ["Positive", "Neutral", "Negative"],
            default=["Positive", "Neutral", "Negative"],
            key="yt_filter",
        )
        filtered = df[df["sentiment"].isin(sentiment_filter)].sort_values("likes", ascending=False)

        st.dataframe(
            filtered[["author", "text", "likes", "sentiment"]].rename(
                columns={"author": "Author", "text": "Comment", "likes": "Likes", "sentiment": "Sentiment"}
            ),
            use_container_width=True,
            hide_index=True,
        )

        csv = filtered.to_csv(index=False)
        st.download_button("Download Comments CSV", data=csv, file_name="youtube_comments_analysis.csv")

st.markdown("---")
st.caption("Built with Streamlit, OpenRouter, and the YouTube Data API")