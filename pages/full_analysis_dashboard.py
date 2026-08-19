import pandas as pd
import plotly.express as px
import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro, sentiment_badge_html, sentiment_card_html,
    stat_pill_html, INDIGO, AMBER, SENTIMENT_COLORS, DEFAULT_MODEL,
    full_analysis, classify_comments_sentiment, split_into_sentences,
    word_reading_counts, load_uploaded_file, SAMPLE_ARTICLES,
)

inject_global_styles()
accent_bar()

st.title("📊 Full Analysis Dashboard")
dashboard_intro(
    "Paste any article and get the complete picture in one pass: overall sentiment, an AI "
    "summary, and a sentence-by-sentence sentiment breakdown with charts - showing not just "
    "what the article says, but how its tone shifts from sentence to sentence."
)

if "full_area" not in st.session_state:
    st.session_state.full_area = ""

st.write("**Try a sample:**")
cols = st.columns(3)
for i, (name, text) in enumerate(SAMPLE_ARTICLES.items()):
    if cols[i].button(name, key=f"sample_full_{i}"):
        st.session_state.full_area = text

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
    st.session_state.pop("full_sentence_results", None)
    st.session_state.pop("full_sentiment_result", None)
    st.session_state.pop("full_summary_result", None)


col_run, col_clear = st.columns([1, 1])
with col_run:
    run_full = st.button("Run Full Analysis", type="primary")
with col_clear:
    st.button("Clear", key="clear_full", on_click=clear_full_tab)

if run_full:
    with st.spinner("Analyzing sentiment and generating summary..."):
        sentiment_result, summary_result = full_analysis(full_input)

    if not sentiment_result.get("sentiment"):
        st.error(sentiment_result.get("reason", "Something went wrong."))
        st.session_state.pop("full_sentence_results", None)
    else:
        sentences = split_into_sentences(full_input)
        sentence_dicts = [{"text": s} for s in sentences]
        if sentence_dicts:
            with st.spinner(f"Classifying sentiment across {len(sentence_dicts)} sentences..."):
                sentence_dicts = classify_comments_sentiment(sentence_dicts, DEFAULT_MODEL)

        st.session_state.full_sentiment_result = sentiment_result
        st.session_state.full_summary_result = summary_result
        st.session_state.full_sentence_results = sentence_dicts

if st.session_state.get("full_sentiment_result"):
    sentiment_result = st.session_state.full_sentiment_result
    summary_result = st.session_state.full_summary_result
    sentence_results = st.session_state.get("full_sentence_results", [])

    st.success("Full analysis complete.")

    if sentiment_result.get("sensitive"):
        st.warning(
            "This text touches on a sensitive topic (violence, abuse, trauma, or similar). "
            "Sentiment labels below reflect the tone/stance of the writing only - they are not "
            "a judgment on the subject matter itself."
        )

    # --- Article overview card ---
    st.markdown(
        """
        <div style="border:1px solid #ECEAFB; border-radius:12px; padding:18px 20px;
                    background-color:white; margin-bottom:1rem;">
            <div style="font-family:'Sora', sans-serif; font-weight:700; font-size:1.1rem;">
                Article Overview
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    o1, o2, o3 = st.columns(3)
    o1.markdown(stat_pill_html("Word Count", word_count, INDIGO, "#F1EEFE", "📄"), unsafe_allow_html=True)
    o2.markdown(stat_pill_html("Reading Time", f"{reading_minutes} min", AMBER, "#FFF3E0", "⏱"), unsafe_allow_html=True)
    o3.markdown(stat_pill_html("Sentences Analyzed", len(sentence_results), "#1565C0", "#E3F2FD", "🔎"), unsafe_allow_html=True)
    st.write("")

    # --- Overall sentiment + summary ---
    sentiment_display = f"Sentiment: {sentiment_result['sentiment']}\nReason: {sentiment_result['reason']}"
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Overall Sentiment**")
            st.markdown(sentiment_badge_html(sentiment_result["sentiment"]), unsafe_allow_html=True)
            st.text_area("Sentiment", value=sentiment_display, height=120, label_visibility="collapsed", disabled=True)
    with col2:
        with st.container(border=True):
            st.markdown("**Summary**")
            st.text_area("Summary", value=summary_result, height=120, label_visibility="collapsed", disabled=True)

    combined = f"--- SENTIMENT ---\n{sentiment_display}\n\n--- SUMMARY ---\n{summary_result}"
    st.download_button("Download Sentiment + Summary", data=combined, file_name="full_analysis_result.txt")

    # --- Sentence-level sentiment breakdown ---
    if sentence_results:
        st.write("")
        st.subheader("Sentence-Level Sentiment Breakdown")

        sdf = pd.DataFrame(sentence_results)
        counts = sdf["sentiment"].value_counts()

        c1, c2, c3 = st.columns(3)
        c1.markdown(sentiment_card_html("Positive", int(counts.get("Positive", 0))), unsafe_allow_html=True)
        c2.markdown(sentiment_card_html("Neutral", int(counts.get("Neutral", 0))), unsafe_allow_html=True)
        c3.markdown(sentiment_card_html("Negative", int(counts.get("Negative", 0))), unsafe_allow_html=True)
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
            seq_df = pd.DataFrame({
                "order": range(1, len(sentence_results) + 1),
                "sentiment": [s["sentiment"] for s in sentence_results],
                "height": 1,
            })
            fig_seq = px.bar(
                seq_df, x="order", y="height", color="sentiment",
                color_discrete_map=SENTIMENT_COLORS,
            )
            fig_seq.update_layout(
                margin=dict(t=10, b=10, l=10, r=10), height=300,
                xaxis_title="Sentence order", yaxis=dict(visible=False),
                legend_title="", bargap=0.02,
            )
            st.plotly_chart(fig_seq, use_container_width=True)
            st.caption("Shows how sentiment shifts across the article, sentence by sentence.")

        st.subheader("Sentences")
        sentence_filter = st.multiselect(
            "Filter by sentiment",
            ["Positive", "Neutral", "Negative"],
            default=["Positive", "Neutral", "Negative"],
            key="full_sentence_filter",
        )
        sdf.insert(0, "order", range(1, len(sdf) + 1))
        filtered = sdf[sdf["sentiment"].isin(sentence_filter)]

        st.dataframe(
            filtered[["order", "text", "sentiment"]].rename(
                columns={"order": "#", "text": "Sentence", "sentiment": "Sentiment"}
            ),
            use_container_width=True,
            hide_index=True,
        )

        csv = filtered.to_csv(index=False)
        st.download_button("Download Sentence Breakdown CSV", data=csv, file_name="sentence_sentiment_breakdown.csv")
