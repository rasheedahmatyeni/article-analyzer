# 📰 Article Analyzer

A Python app that takes any article and gives back both sentiment analysis and an AI-generated summary — combining a local Hugging Face transformer model with an LLM API, wrapped in an interactive Streamlit interface.

**🔗 Live app:** [article-analyzer0.streamlit.app](https://article-analyzer0.streamlit.app/)

![Python](https://img.shields.io/badge/Python-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![HuggingFace](https://img.shields.io/badge/🤗%20Transformers-NLP-yellow)

---

## 📋 Overview

Article Analyzer takes a piece of text — pasted in or provided as a link — and returns two things: a sentiment analysis of the tone, and a concise, AI-generated summary of the content. It combines a locally-run Hugging Face transformer model for sentiment classification with an LLM (via the OpenRouter API) for summarization, giving a fast, lightweight sentiment score alongside a genuinely readable summary.

Built and deployed end-to-end — from local development through to a live, publicly accessible app — this project also surfaced and addressed a real limitation in off-the-shelf sentiment models: **tone-topic conflation**, where sentiment models can misclassify advocacy or issue-driven writing (e.g. an article passionately describing a serious problem) as "negative" simply because the *subject matter* is heavy, even when the *writing* isn't expressing negativity. A second-pass zero-shot topic classifier (`facebook/bart-large-mnli`) was introduced to help disentangle topic from tone.

## ✨ Features

- **Sentiment analysis** — powered by Hugging Face Transformers, classifying the emotional tone of the input text
- **AI-generated summarization** — powered by an LLM via the OpenRouter API, condensing articles into clear, readable summaries
- **Simple, interactive interface** — built with Streamlit, no technical knowledge required to use
- **Tone vs. topic awareness** — an in-progress zero-shot classification layer to reduce misclassification of advocacy/issue-focused content as simply "negative"

## 🛠️ Tech Stack

- **Python** — core language
- **Streamlit** — interactive web interface and deployment
- **Hugging Face Transformers** — local sentiment analysis model
- **OpenRouter API** — LLM-powered summarization
- **Gradio** *(early prototyping, later migrated to Streamlit for deployment)*

## 🚀 Running Locally

```bash
# Clone the repo
git clone https://github.com/rasheedahmatyeni/article-analyzer.git
cd article-analyzer

# Create a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

**Note:** you'll need your own OpenRouter API key to run the summarization feature — set it as an environment variable or in Streamlit secrets rather than hardcoding it in the source.

## 📁 Project Structure

```
article-analyzer/
├── app.py                  # Main Streamlit application
├── requirements.txt         # Python dependencies
├── summary_result.txt        # Sample summarization output
├── full_analysis_result.txt   # Sample full analysis output
├── .gradio/                 # Early Gradio prototype files
├── .devcontainer/            # Dev container configuration
└── .gitignore
```

## 🧩 Real-World Challenges Solved

Building and deploying this app end-to-end involved working through several genuine production issues:

- **Windows Application Control** blocking pip installs, requiring an alternate install approach
- **Transformers v5 breaking changes** that required adjusting model-loading code
- **An exposed API key**, requiring key rotation and a git history rewrite to fully remove it from version control
- **Gradio → Streamlit migration**, moving from an early prototype interface to a production-ready deployment target
- **Tone-topic conflation** in the sentiment pipeline, discovered through real testing and addressed with a second-pass zero-shot topic classifier

## 👩🏽‍💻 Author

**Rasheedah Matyeni**
[LinkedIn](https://linkedin.com/in/rasheedah-matyeni) · [Portfolio](https://rasheedah-matyeni-portfolio.vercel.app)