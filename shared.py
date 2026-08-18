"""Shared constants, styling, and business logic for the Article Analyzer multi-page app.

Every page under pages/ imports from this module rather than duplicating logic, so the
sentiment engine, API clients, and visual identity stay consistent across dashboards.
"""

import os
import re
import json
from datetime import datetime, timezone

import requests
import pandas as pd
import streamlit as st
from openrouter import OpenRouter
from pypdf import PdfReader
from docx import Document

# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", os.getenv("YOUTUBE_API_KEY", ""))

# Fast, cost-effective models offered for comment sentiment + summary generation
SENTIMENT_MODELS = {
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "Claude 3.5 Haiku": "anthropic/claude-3.5-haiku",
    "DeepSeek R1": "deepseek/deepseek-r1",
}

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
INDIGO = "#6C4FF6"
INDIGO_DARK = "#5636D9"
AMBER = "#FFB020"
INK = "#1B1E2B"
SENTIMENT_COLORS = {"Positive": "#2E7D32", "Neutral": "#5A5D6B", "Negative": "#C62828"}
SENTIMENT_TINTS = {"Positive": "#E8F5E9", "Neutral": "#EEEEF2", "Negative": "#FDECEA"}


def get_pages():
    """Returns the app's Page objects, keyed by a short name.

    Defined once here so app.py (for st.navigation) and pages/home.py (for st.page_link) both
    work with actual Page objects rather than raw string paths - passing a string to st.page_link
    from inside a page that lives in a subfolder can resolve relative to the wrong directory.
    """
    return {
        "home": st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        "summarize": st.Page("pages/summarize_dashboard.py", title="Article Summarizer", icon="📝"),
        "sentiment": st.Page("pages/sentiment_dashboard.py", title="Sentiment Analysis Dashboard", icon="💬"),
        "full": st.Page("pages/full_analysis_dashboard.py", title="Full Analysis Dashboard", icon="📊"),
        "youtube": st.Page("pages/youtube_dashboard.py", title="YouTube Sentiment Dashboard", icon="🎬"),
    }


def inject_global_styles():
    """Injects the shared visual identity: Sora display font, indigo/amber accents, and
    consistent styling for buttons, tabs, the sidebar nav, and sentiment badges/cards."""
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

        /* Signature gradient bar, used at the top of every page */
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

        .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
        .stTabs [aria-selected="true"] {{
            color: {INDIGO} !important;
            border-bottom-color: {INDIGO} !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: {INDIGO} !important; }}

        /* Sidebar navigation */
        section[data-testid="stSidebar"] {{
            background-color: #FFFFFF;
            border-right: 1px solid #ECEAFB;
        }}
        section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
            border-radius: 8px;
            font-weight: 600;
        }}
        section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {{
            background-color: #F1EEFE;
            color: {INDIGO} !important;
        }}

        .sentiment-badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 999px;
            font-weight: 700;
            font-family: 'Sora', sans-serif;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }}

        .dashboard-intro {{
            background-color: #F1EEFE;
            border-left: 4px solid {INDIGO};
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 1.2rem;
            color: {INK};
        }}

        .stat-pill {{
            border-radius: 10px;
            padding: 10px 14px;
        }}
        </style>
    """, unsafe_allow_html=True)


def accent_bar():
    st.markdown('<div class="accent-bar"></div>', unsafe_allow_html=True)


def dashboard_intro(text):
    """A colored callout box describing what a dashboard page does, shown under its title."""
    st.markdown(f'<div class="dashboard-intro">{text}</div>', unsafe_allow_html=True)


def sentiment_badge_html(label):
    """A small colored pill for a sentiment label, falling back to gray for unknown/error states."""
    color = SENTIMENT_COLORS.get(label, "#5A5D6B")
    tint = SENTIMENT_TINTS.get(label, "#EEEEF2")
    text = label if label else "N/A"
    return (
        f'<span class="sentiment-badge" style="background-color:{tint}; color:{color};">'
        f"{text}</span>"
    )


def sentiment_card_html(label, value):
    """A color-coded metric card (green/gray/red) for a sentiment count."""
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


def stat_pill_html(label, value, color, tint, icon=""):
    """A small stat card used on the YouTube dashboard's video-info header (views, likes, etc.)."""
    return f"""
        <div class="stat-pill" style="background-color:{tint};">
            <div style="color:{color}; font-weight:700; font-size:0.72rem;
                        text-transform:uppercase; letter-spacing:0.03em;">{icon} {label}</div>
            <div style="color:{INK}; font-size:1.3rem; font-weight:800;
                        font-family:'Sora', sans-serif;">{value}</div>
        </div>
    """


def format_count(n):
    """Formats large numbers the way YouTube does: 1234567 -> '1.2M', 12345 -> '12.3K'."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def time_ago(iso_string):
    """Formats an ISO timestamp as a relative string, e.g. '5 months ago'."""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return ""
    days = (datetime.now(timezone.utc) - dt).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


# ---------------------------------------------------------------------------
# Sentiment guidance shared by every classifier in the app
# ---------------------------------------------------------------------------
# The key fix here: emotional tone (sadness, nostalgia, crying) is NOT the same as negative
# sentiment - a comment can be sad AND supportive, which is Positive. But this cuts both ways:
# don't default everything with warmth or fandom language to Positive either. Real criticism,
# complaints, and requests framed politely are still Negative, and plain factual or ambiguous
# comments are still Neutral.
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


# ---------------------------------------------------------------------------
# Article-level analysis (Summarize / Sentiment Analysis / Full Analysis dashboards)
# ---------------------------------------------------------------------------
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


def word_reading_counts(text):
    """Returns (word_count, reading_minutes) as raw numbers, for rendering as stat pills."""
    if not text.strip():
        return 0, 0
    word_count = len(text.split())
    reading_minutes = max(1, round(word_count / 200))
    return word_count, reading_minutes


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


SAMPLE_ARTICLES = {
    "Sample: AI in Industry": """Artificial intelligence is transforming industries worldwide. From healthcare to finance, organizations are deploying machine learning models to automate tasks, improve decision-making, and uncover insights from vast datasets. In healthcare, AI systems can now detect certain cancers from medical images with accuracy rivaling experienced radiologists. Financial institutions use AI to detect fraud in real time, saving billions of dollars annually. The transportation sector is being reshaped by autonomous vehicles that rely on deep learning to navigate complex environments. Meanwhile, natural language processing breakthroughs have enabled virtual assistants and translation tools that were unimaginable a decade ago. Despite these advances, challenges remain around data privacy, algorithmic bias, and the displacement of workers in certain sectors. Policymakers, researchers, and industry leaders are working to establish frameworks that ensure AI development proceeds responsibly and equitably.""",
    "Sample: Community News": """The local community center celebrated its 20th anniversary this weekend with a series of events that brought together hundreds of residents. Organizers praised the turnout, noting that the center has become a vital hub for youth programs, elder support services, and cultural celebrations over the past two decades. Volunteers set up food stalls, live music, and children's activities throughout the day. Several long-time members shared stories about how the center helped them through difficult times, from job loss to family struggles. City officials attended the event and announced a new grant that will fund an expansion of the center's after-school tutoring program next year.""",
    "Sample: Negative Review": """The restaurant's service was disappointingly slow, and our order arrived nearly forty minutes after we requested it. When the food finally came, it was lukewarm and clearly not freshly prepared. Several dishes were missing ingredients that were listed on the menu, and when we raised this with the staff, we were met with indifference rather than an apology. The prices, given the quality and experience, felt entirely unjustified. We left the restaurant frustrated and would not recommend it to others looking for a reliable dining experience.""",
}


# ---------------------------------------------------------------------------
# YouTube Insights (YouTube Sentiment Dashboard)
# ---------------------------------------------------------------------------
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


def fetch_youtube_video_details(video_id):
    """Fetch title, channel, publish date, description, and stats for a video via YouTube Data API v3."""
    if not YOUTUBE_API_KEY:
        return None, "Error: YOUTUBE_API_KEY not set. Please add it to your Streamlit secrets."

    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,statistics", "id": video_id, "key": YOUTUBE_API_KEY}

    try:
        response = requests.get(endpoint, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching video details: {e}"

    items = data.get("items", [])
    if not items:
        return None, "Video not found - it may be private, deleted, or the link is invalid."

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    details = {
        "title": snippet.get("title", "Untitled"),
        "channel": snippet.get("channelTitle", "Unknown channel"),
        "published_at": snippet.get("publishedAt", ""),
        "description": snippet.get("description", ""),
        "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comment_count": int(stats.get("commentCount", 0)),
    }
    return details, None


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
