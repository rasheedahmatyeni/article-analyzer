import streamlit as st
from transformers import pipeline
import os
from openrouter import OpenRouter
from pypdf import PdfReader
from docx import Document

st.set_page_config(page_title="Article Analyzer", page_icon="📰", layout="centered")

# Soft blue and white styling
st.markdown("""
    <style>
    .stApp { background-color: white; }
    .stButton>button {
        background-color: #4a6fa5;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #3d5c8a;
        color: white;
    }
    div[data-testid="stMetric"] {
        background-color: #f0f5fa;
        padding: 10px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Load API key from Streamlit secrets (or environment as a fallback for local runs)
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))


@st.cache_resource
def load_sentiment_model():
    return pipeline("sentiment-analysis")


sentiment_analyzer = load_sentiment_model()


def analyze_sentiment(text):
    if not text.strip():
        return "Please enter some text to analyze."
    result = sentiment_analyzer(text[:512])[0]
    label = result["label"]
    score = result["score"]
    return f"Sentiment: {label}\nConfidence: {score:.2%}"


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
        return "Please enter some text to analyze.", ""
    return analyze_sentiment(text), summarize_with_llm(text)


def word_and_reading_stats(text):
    if not text.strip():
        return "0 words · 0 min read"
    word_count = len(text.split())
    reading_minutes = max(1, round(word_count / 200))
    return f"{word_count} words · ~{reading_minutes} min read"


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


st.title("Article Analyzer")
st.write("Paste any article to get AI-powered sentiment analysis and summarization.")

tab1, tab2, tab3 = st.tabs(["Summarize", "Sentiment Analysis", "Full Analysis"])

# ---------- Summarize tab ----------
with tab1:
    if "summary_text" not in st.session_state:
        st.session_state.summary_text = ""

    st.write("**Try a sample:**")
    cols = st.columns(3)
    for i, (name, text) in enumerate(SAMPLE_ARTICLES.items()):
        if cols[i].button(name, key=f"sample_summary_{i}"):
            st.session_state.summary_text = text

    uploaded = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_summary")
    if uploaded is not None:
        st.session_state.summary_text = load_uploaded_file(uploaded)

    summary_input = st.text_area("Article Text", value=st.session_state.summary_text, height=200, key="summary_area")
    st.caption(word_and_reading_stats(summary_input))

    if st.button("Summarize", type="primary"):
        with st.spinner("Summarizing..."):
            result = summarize_with_llm(summary_input)
        st.text_area("Summary", value=result, height=150)
        st.download_button("Download Summary", data=result, file_name="summary_result.txt")

# ---------- Sentiment Analysis tab ----------
with tab2:
    if "sentiment_text" not in st.session_state:
        st.session_state.sentiment_text = ""

    uploaded_s = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_sentiment")
    if uploaded_s is not None:
        st.session_state.sentiment_text = load_uploaded_file(uploaded_s)

    sentiment_input = st.text_area("Article Text", value=st.session_state.sentiment_text, height=200, key="sentiment_area")
    st.caption(word_and_reading_stats(sentiment_input))

    if st.button("Analyze Sentiment", type="primary"):
        with st.spinner("Analyzing..."):
            result = analyze_sentiment(sentiment_input)
        st.text_area("Sentiment Result", value=result, height=80)

# ---------- Full Analysis tab ----------
with tab3:
    if "full_text" not in st.session_state:
        st.session_state.full_text = ""

    uploaded_f = st.file_uploader("Or upload a .txt, .pdf, or .docx file", type=["txt", "pdf", "docx"], key="upload_full")
    if uploaded_f is not None:
        st.session_state.full_text = load_uploaded_file(uploaded_f)

    full_input = st.text_area("Article Text", value=st.session_state.full_text, height=200, key="full_area")
    st.caption(word_and_reading_stats(full_input))

    if st.button("Run Full Analysis", type="primary"):
        with st.spinner("Running full analysis..."):
            sentiment_result, summary_result = full_analysis(full_input)

        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Sentiment", value=sentiment_result, height=150)
        with col2:
            st.text_area("Summary", value=summary_result, height=150)

        combined = f"--- SENTIMENT ---\n{sentiment_result}\n\n--- SUMMARY ---\n{summary_result}"
        st.download_button("Download Full Results", data=combined, file_name="full_analysis_result.txt")

st.markdown("---")
st.caption("Built with Hugging Face Transformers, OpenRouter, and Streamlit")