import streamlit as st
from shared import inject_global_styles, get_pages

st.set_page_config(page_title="Article Analyzer", page_icon="📰", layout="wide")
inject_global_styles()

pages = get_pages()
pg = st.navigation([pages["home"], pages["full"], pages["youtube"]])
pg.run()
