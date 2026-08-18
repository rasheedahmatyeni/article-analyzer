import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro, sentiment_badge_html,
    stat_pill_html, INDIGO, AMBER,
    full_analysis, word_reading_counts, load_uploaded_file,
)

inject_global_styles()
accent_bar()

st.title("📊 Full Analysis Dashboard")
dashboard_intro(
    "Run sentiment analysis and summarization together in a single pass, side by side, and "
    "download both results as one combined file - useful when you need the full picture on an "
    "article without switching between dashboards."
)

if "full_area" not in st.session_state:
    st.session_state.full_area = ""

uploaded_f = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_full")
if uploaded_f is not None:
    st.session_state.full_area = load_uploaded_file(uploaded_f)

full_input = st.text_area("Article Text", height=220, key="full_area")

word_count, reading_minutes = word_reading_counts(full_input)
p1, p2 = st.columns(2)
p1.markdown(stat_pill_html("Word Count", word_count, INDIGO, "#F1EEFE", "📄"), unsafe_allow_html=True)
p2.markdown(stat_pill_html("Reading Time", f"{reading_minutes} min", AMBER, "#FFF3E0", "⏱"), unsafe_allow_html=True)
st.write("")


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

    if not sentiment_result.get("sentiment"):
        st.error(sentiment_result.get("reason", "Something went wrong."))
    else:
        st.success("Full analysis complete.")

        if sentiment_result.get("sensitive"):
            st.warning(
                "This text touches on a sensitive topic (violence, abuse, trauma, or similar). "
                "The sentiment label reflects the tone/stance of the writing only - it is not a "
                "judgment on the subject matter itself."
            )

        sentiment_display = f"Sentiment: {sentiment_result['sentiment']}\nReason: {sentiment_result['reason']}"

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown(sentiment_badge_html(sentiment_result["sentiment"]), unsafe_allow_html=True)
                st.text_area("Sentiment", value=sentiment_display, height=150, label_visibility="collapsed")
        with col2:
            with st.container(border=True):
                st.markdown("**Summary**")
                st.text_area("Summary", value=summary_result, height=150, label_visibility="collapsed")

        combined = f"--- SENTIMENT ---\n{sentiment_display}\n\n--- SUMMARY ---\n{summary_result}"
        st.download_button("Download Full Results", data=combined, file_name="full_analysis_result.txt")
