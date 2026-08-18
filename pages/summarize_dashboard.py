import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro,
    summarize_with_llm, word_and_reading_stats, load_uploaded_file, SAMPLE_ARTICLES,
)

inject_global_styles()
accent_bar()

st.title("📝 Article Summarizer")
dashboard_intro(
    "Paste in any article, blog post, or document and get a concise AI-generated summary in "
    "2-3 sentences - useful for quickly triaging long reads or extracting the key takeaway."
)

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

summary_input = st.text_area("Article Text", height=220, key="summary_area")
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
