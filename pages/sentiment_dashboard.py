import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro, sentiment_badge_html,
    analyze_sentiment, word_and_reading_stats, load_uploaded_file,
)

inject_global_styles()
accent_bar()

st.title("💬 Sentiment Analysis Dashboard")
dashboard_intro(
    "Classify the underlying stance of any article - Positive, Negative, or Neutral - based on "
    "the writer's actual opinion, not just emotional word choice. Content on serious or "
    "distressing topics is automatically flagged as sensitive, so a label never reads as a "
    "judgment on the subject matter itself."
)

if "sentiment_area" not in st.session_state:
    st.session_state.sentiment_area = ""

uploaded_s = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_sentiment")
if uploaded_s is not None:
    st.session_state.sentiment_area = load_uploaded_file(uploaded_s)

sentiment_input = st.text_area("Article Text", height=220, key="sentiment_area")
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
