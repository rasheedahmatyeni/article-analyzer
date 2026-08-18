import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro, stat_pill_html, INDIGO, AMBER,
    summarize_with_llm, word_reading_counts, load_uploaded_file, SAMPLE_ARTICLES,
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

word_count, reading_minutes = word_reading_counts(summary_input)
p1, p2 = st.columns(2)
p1.markdown(stat_pill_html("Word Count", word_count, INDIGO, "#F1EEFE", "📄"), unsafe_allow_html=True)
p2.markdown(stat_pill_html("Reading Time", f"{reading_minutes} min", AMBER, "#FFF3E0", "⏱"), unsafe_allow_html=True)
st.write("")


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

    if result.startswith(("Error", "Please enter")):
        st.error(result)
    else:
        st.success("Summary generated successfully.")
        with st.container(border=True):
            st.markdown("**Summary**")
            st.text_area("Summary", value=result, height=150, label_visibility="collapsed")
        st.download_button("Download Summary", data=result, file_name="summary_result.txt")
