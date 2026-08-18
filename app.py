import streamlit as st
from shared import inject_global_styles

st.set_page_config(page_title="Article Analyzer", page_icon="📰", layout="wide")
inject_global_styles()

home_page = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
youtube_page = st.Page("pages/youtube_dashboard.py", title="YouTube Sentiment Dashboard", icon="🎬")
summarize_page = st.Page("pages/summarize_dashboard.py", title="Article Summarizer", icon="📝")
sentiment_page = st.Page("pages/sentiment_dashboard.py", title="Sentiment Analysis Dashboard", icon="💬")
full_page = st.Page("pages/full_analysis_dashboard.py", title="Full Analysis Dashboard", icon="📊")

pg = st.navigation([home_page, summarize_page, sentiment_page, full_page, youtube_page])
pg.run()
