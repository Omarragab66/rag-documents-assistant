import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

from api_client import ask_question

load_dotenv(Path(__file__).with_name(".env"))

FALLBACK_MARKER = "Based on the documentation, the most relevant excerpt is:"

st.set_page_config(
    page_title="FastAPI Document Assistant",
    page_icon="📚",
    layout="centered",
)

st.title("FastAPI Document Assistant")
st.caption("Ask questions about the FastAPI documentation")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("badge"):
            st.caption(message["badge"])
        if message.get("sources"):
            with st.expander("Sources"):
                for source in message["sources"]:
                    st.markdown(f"- `{source}`")

question = st.chat_input("Ask a FastAPI question...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the documentation and preparing an answer..."):
            try:
                result = ask_question(question)
                answer = result["answer"]
                sources = result["sources"]
                badge = (
                    "📄 Direct excerpt"
                    if FALLBACK_MARKER in answer
                    else "🤖 Model-generated"
                )
                st.markdown(answer)
                st.caption(badge)
                if sources:
                    with st.expander("Sources"):
                        for source in sources:
                            st.markdown(f"- `{source}`")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "badge": badge,
                    "sources": sources,
                })
            except requests.exceptions.Timeout:
                message = "The backend took too long to respond. Please try again."
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})
            except requests.exceptions.ConnectionError:
                message = "The backend is unavailable. Please start it and try again."
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})
            except requests.exceptions.HTTPError:
                message = "The backend rejected the request. Please check the question and try again."
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})
            except (RuntimeError, ValueError) as error:
                message = f"The assistant could not process the request: {error}"
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})
            except Exception:
                message = "Something went wrong while contacting the assistant. Please try again."
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})
