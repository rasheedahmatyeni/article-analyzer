import pandas as pd
import plotly.express as px
import streamlit as st
from shared import (
    inject_global_styles, accent_bar, dashboard_intro, INK,
    SENTIMENT_COLORS, SENTIMENT_MODELS, sentiment_card_html, stat_pill_html,
    format_count, time_ago, extract_video_id, fetch_youtube_video_details,
    fetch_youtube_comments, classify_comments_sentiment, generate_executive_summary,
)

inject_global_styles()
accent_bar()

st.title("🎬 YouTube Sentiment Dashboard")
dashboard_intro(
    "Paste a public YouTube video link to pull its comments via the official YouTube Data API, "
    "classify audience sentiment with AI, and get an executive summary of praise and pain "
    "points - plus visual charts showing how opinion breaks down and shifts over time."
)

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
    st.session_state.pop("yt_video", None)


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
        with st.spinner("Fetching video details..."):
            video_details, video_error = fetch_youtube_video_details(video_id)

        if video_error:
            st.error(video_error)
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

                st.session_state.yt_video = video_details
                st.session_state.yt_comments = comments
                st.session_state.yt_summary = summary

if st.session_state.get("yt_comments"):
    video = st.session_state.get("yt_video")
    comments = st.session_state.yt_comments
    df = pd.DataFrame(comments)

    st.success(f"Analysis complete — successfully analyzed the video and {len(comments)} comments.")

    if video:
        st.markdown(
            f"""
            <div style="border:1px solid #ECEAFB; border-radius:12px; padding:18px 20px;
                        background-color:white; margin-bottom:1rem;">
                <div style="font-family:'Sora', sans-serif; font-weight:700; font-size:1.25rem;
                            color:{INK};">{video['title']}</div>
                <div style="color:#666; font-size:0.9rem; margin-top:4px;">
                    {video['channel']} &nbsp;·&nbsp; {time_ago(video['published_at'])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        p1, p2, p3, p4 = st.columns(4)
        p1.markdown(stat_pill_html("Views", format_count(video["views"]), "#6C4FF6", "#F1EEFE", "👁"), unsafe_allow_html=True)
        p2.markdown(stat_pill_html("Likes", format_count(video["likes"]), "#2E7D32", "#E8F5E9", "👍"), unsafe_allow_html=True)
        p3.markdown(stat_pill_html("Comments", format_count(video["comment_count"]), "#1565C0", "#E3F2FD", "💬"), unsafe_allow_html=True)
        p4.markdown(stat_pill_html("Published", time_ago(video["published_at"]), "#B26A00", "#FFF3E0", "📅"), unsafe_allow_html=True)

        if video.get("description"):
            with st.expander("Video description"):
                st.write(video["description"])

    st.write("")
    st.subheader("Executive Summary")
    st.markdown(st.session_state.yt_summary)

    st.subheader("Sentiment Breakdown")
    counts = df["sentiment"].value_counts()

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
