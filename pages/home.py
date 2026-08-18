import streamlit as st
from shared import (
    inject_global_styles, accent_bar, get_pages, INDIGO, AMBER, INK,
    OPENROUTER_API_KEY, YOUTUBE_API_KEY,
)

inject_global_styles()
accent_bar()

pages = get_pages()

# --- Connection status badges ---
def status_badge(name, connected):
    color = "#2E7D32" if connected else "#C62828"
    tint = "#E8F5E9" if connected else "#FDECEA"
    label = "Connected" if connected else "Not configured"
    icon = "&#9679;"
    return (
        f'<span style="background-color:{tint}; color:{color}; padding:4px 12px; '
        f'border-radius:999px; font-weight:600; font-size:0.8rem; margin-right:8px;">'
        f'{icon} {name}: {label}</span>'
    )

st.markdown(
    status_badge("OpenRouter", bool(OPENROUTER_API_KEY)) +
    status_badge("YouTube API", bool(YOUTUBE_API_KEY)),
    unsafe_allow_html=True,
)

st.write("")

# --- Hero ---
st.markdown(
    f"""
    <h1 style="font-size:3rem; margin-bottom:0;">Article Analyzer</h1>
    <h1 style="font-size:3rem; margin-top:0;
               background: linear-gradient(90deg, {INDIGO} 0%, {AMBER} 100%);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               display:inline-block;">AI-Powered Insight Dashboards</h1>
    """,
    unsafe_allow_html=True,
)
st.write(
    "Paste an article or a YouTube link and get AI-powered sentiment analysis, summarization, "
    "and executive-ready insights - built for making sense of audience and reader feedback fast."
)

st.write("")
st.subheader("Choose a dashboard")

# --- Dashboard cards ---
cards = [
    {
        "icon": "📝",
        "title": "Article Summarizer",
        "desc": "Paste any article and get a concise, 2-3 sentence AI summary in seconds.",
        "page_key": "summarize",
        "color": INDIGO,
    },
    {
        "icon": "💬",
        "title": "Sentiment Analysis Dashboard",
        "desc": "Understand the stance behind any article's writing, with automatic sensitive-topic flagging.",
        "page_key": "sentiment",
        "color": "#2E7D32",
    },
    {
        "icon": "📊",
        "title": "Full Analysis Dashboard",
        "desc": "Run sentiment and summarization together, side by side, and download the combined results.",
        "page_key": "full",
        "color": AMBER,
    },
    {
        "icon": "🎬",
        "title": "YouTube Sentiment Dashboard",
        "desc": "Pull public comments from any YouTube video and see sentiment, trends over time, and an AI executive summary.",
        "page_key": "youtube",
        "color": "#C62828",
    },
]

col1, col2 = st.columns(2)
for i, card in enumerate(cards):
    target_col = col1 if i % 2 == 0 else col2
    with target_col:
        st.markdown(
            f"""
            <div style="border:1px solid #ECEAFB; border-top:4px solid {card['color']};
                        border-radius:12px; padding:18px 20px; margin-bottom:16px; min-height:150px;
                        background-color:white;">
                <div style="font-size:1.6rem;">{card['icon']}</div>
                <div style="font-family:'Sora', sans-serif; font-weight:700; font-size:1.1rem;
                            color:{INK}; margin-top:4px;">{card['title']}</div>
                <div style="color:#555; font-size:0.92rem; margin-top:6px;">{card['desc']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(pages[card["page_key"]], label=f"Open {card['title']}", icon="→")

st.markdown("---")
st.caption("Built with Streamlit, OpenRouter, and the YouTube Data API")
