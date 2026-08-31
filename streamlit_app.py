from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import streamlit as st

from app.arxiv_expert import ArxivExpertService, ScientificNLP
from app.chatbot import RetrievalChatbot
from app.config import AppConfig
from app.llm import OpenAICompatibleLLMClient
from app.medical_qa import MedicalQAService
from app.memory import ConversationMemoryStore
from app.monitoring import AppMonitor
from app.reasoning import ReasoningEngine
from app.schemas import ImageInput
from app.updater import KnowledgeBaseUpdater
from app.validation import ResponseValidator
from app.vector_store import VectorStore
from app.vision import VisualAnalyzer

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MEDQUAD_DIR = PROJECT_ROOT / "dataset" / "MedQuAD"
SAMPLE_MEDQUAD_PATH = PROJECT_ROOT / "dataset" / "medquad_sample" / "sample_medquad_records.json"
DEFAULT_ARXIV_PATH = PROJECT_ROOT / "dataset" / "arxiv" / "arxiv-metadata-oai-snapshot.json"
SAMPLE_ARXIV_PATH = PROJECT_ROOT / "dataset" / "arxiv_sample" / "sample_arxiv_cs.jsonl"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
CHATBOT_MODES = [
    "General / Multimodal Assistant",
    "Medical Q&A (MedQuAD)",
    "Research Expert (arXiv CS)",
]


@st.cache_resource
def load_config() -> AppConfig:
    return AppConfig.load(PROJECT_ROOT / "sources.json")


@st.cache_resource
def build_services() -> tuple[AppConfig, VectorStore, KnowledgeBaseUpdater, RetrievalChatbot]:
    config = load_config()
    vector_store = VectorStore(config)
    updater = KnowledgeBaseUpdater(config, vector_store)
    monitor = AppMonitor()
    llm_client = OpenAICompatibleLLMClient(config.llm) if config.llm.enabled else None
    chatbot = RetrievalChatbot(
        config,
        vector_store,
        monitor,
        llm_client,
        memory_store=ConversationMemoryStore(config.session_store_path),
        visual_analyzer=VisualAnalyzer(llm_client),
        validator=ResponseValidator(),
        reasoning_engine=ReasoningEngine(),
    )
    return config, vector_store, updater, chatbot


@st.cache_resource
def load_medical_service(dataset_dir_text: str) -> MedicalQAService:
    dataset_dir = Path(dataset_dir_text).expanduser()
    if not dataset_dir.is_absolute():
        dataset_dir = PROJECT_ROOT / dataset_dir
    return MedicalQAService.from_dataset(dataset_dir, fallback_sample_path=SAMPLE_MEDQUAD_PATH)


@st.cache_resource
def load_arxiv_service(dataset_path_text: str, use_local_llm: bool) -> ArxivExpertService:
    dataset_path = Path(dataset_path_text).expanduser()
    if not dataset_path.is_absolute():
        dataset_path = PROJECT_ROOT / dataset_path
    return ArxivExpertService.from_dataset(
        dataset_path,
        fallback_sample_path=SAMPLE_ARXIV_PATH,
        use_local_llm=use_local_llm,
    )


def persist_uploaded_image(uploaded_file) -> str:
    """Store an uploaded image under a stable, safe name for the vision pipeline."""
    content = uploaded_file.getvalue()
    digest = hashlib.sha256(content).hexdigest()[:16]
    suffix = Path(uploaded_file.name).suffix.lower() or ".png"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(content)
    return str(path)


def render_composer_menu(current_mode: str):
    """Render the compact control menu that sits beside the message composer."""
    def switch_mode() -> None:
        st.session_state.active_chatbot_mode = st.session_state.composer_mode

    with st.popover("☰", help="Chatbot mode and image upload", use_container_width=True):
        selected_mode = st.selectbox(
            "Chatbot mode",
            CHATBOT_MODES,
            index=CHATBOT_MODES.index(current_mode),
            key="composer_mode",
            on_change=switch_mode,
        )
        uploaded_image = None
        if selected_mode == "General / Multimodal Assistant":
            uploaded_image = st.file_uploader(
                "Add image",
                type=["png", "jpg", "jpeg", "webp"],
                key="composer_image_upload",
            )

    return uploaded_image


def main() -> None:
    st.set_page_config(page_title="Unified AI Chatbot", page_icon=":robot_face:", layout="wide")
    st.title("Unified AI Chatbot")

    config, _vector_store, updater, chatbot = build_services()
    if "knowledge_base_ready" not in st.session_state:
        updater.sync()
        st.session_state.knowledge_base_ready = True
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = uuid.uuid4().hex
    session_id = st.session_state.chat_session_id
    domain = st.session_state.get("active_chatbot_mode", CHATBOT_MODES[0])
    if domain == "General / Multimodal Assistant":
        render_general_chat(config, updater, chatbot, session_id, domain)
    elif domain == "Medical Q&A (MedQuAD)":
        render_medical_chat(session_id, domain)
    else:
        render_arxiv_chat(session_id, domain)


def render_general_chat(
    config: AppConfig,
    updater: KnowledgeBaseUpdater,
    chatbot: RetrievalChatbot,
    session_id: str,
    domain: str,
) -> None:
    history_key = f"general_ui_history_{session_id}"
    history = st.session_state.setdefault(history_key, [])
    for message in history:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(message["content"])
            else:
                render_general_response(message["response"])

    menu_column, prompt_column = st.columns([1, 11], vertical_alignment="bottom")
    with menu_column:
        menu_image = render_composer_menu(domain)
    with prompt_column:
        question = st.chat_input("Ask the assistant", key="general_chat_input")
    if not question:
        return

    image_inputs: list[ImageInput] = []
    if menu_image is not None:
        image_hash = hashlib.sha256(menu_image.getvalue()).hexdigest()
        if image_hash != st.session_state.get("last_consumed_image_hash"):
            image_inputs.append(ImageInput(path=persist_uploaded_image(menu_image)))
            st.session_state.last_consumed_image_hash = image_hash

    response = chatbot.answer(question, session_id=session_id, image_inputs=image_inputs)
    history.extend(
        [
            {"role": "user", "content": question},
            {"role": "assistant", "response": response},
        ]
    )
    st.rerun()


def render_general_response(response) -> None:
    st.write(response.answer)
    if response.follow_up_question:
        st.info(response.follow_up_question)

    with st.popover("Details", icon=":material/info:"):
        st.caption("Response diagnostics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Used LLM", "Yes" if response.used_llm else "No")
        col2.metric("Needs Clarification", "Yes" if response.needs_clarification else "No")
        validation_label = "Grounded" if response.validation and response.validation.grounded else "Needs Review"
        col3.metric("Validation", validation_label)

        if response.sentiment:
            sentiment_col1, sentiment_col2 = st.columns(2)
            sentiment_col1.metric("Detected Sentiment", response.sentiment.label.title())
            sentiment_col2.metric("Sentiment Confidence", f"{response.sentiment.score:.2f}")

        if response.language:
            language_col1, language_col2, language_col3 = st.columns(3)
            language_col1.metric("Detected Language", response.language.language_name)
            language_col2.metric("Language Confidence", f"{response.language.confidence:.2f}")
            language_col3.metric("Mixed Input", "Yes" if response.language.mixed_language else "No")

        st.divider()
        st.caption("Evidence")
        for item in response.evidence:
            st.markdown(f"**{item.modality.title()}** - `{item.source}`")
            st.write(item.summary)
            if item.details:
                for detail in item.details:
                    st.write(f"- {detail}")

        st.divider()
        st.caption("Sources")
        for source in response.sources:
            st.write(source)

        st.divider()
        st.caption("Validation")
        if response.validation is None:
            st.write("No validation output.")
        else:
            st.write(
                {
                    "grounded": response.validation.grounded,
                    "confidence": response.validation.confidence,
                    "issues": response.validation.issues,
                }
            )

        st.divider()
        st.caption("Language")
        if response.language is None:
            st.write("No language output.")
        else:
            st.write(
                {
                    "primary_language": response.language.primary_language,
                    "detected_languages": response.language.detected_languages,
                    "normalized_query": response.language.normalized_query,
                    "ambiguous": response.language.ambiguous,
                    "notes": response.language.notes,
                }
            )


def render_medical_chat(session_id: str, domain: str) -> None:
    with st.sidebar:
        st.subheader("Medical Dataset")
        dataset_dir = st.text_input(
            "MedQuAD dataset folder",
            value=os.getenv("MEDQUAD_DATASET_DIR", str(DEFAULT_MEDQUAD_DIR)),
        )

    service = load_medical_service(dataset_dir)
    st.info(
        "This mode provides educational information from indexed medical QA records. "
        "It is not a diagnosis or a substitute for professional medical advice."
    )
    history_key = f"medical_ui_history_{session_id}"
    history = st.session_state.setdefault(history_key, [])
    for message in history:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_medical_result(message["result"])
            else:
                st.write(message["content"])

    menu_column, prompt_column = st.columns([1, 11], vertical_alignment="bottom")
    with menu_column:
        render_composer_menu(domain)
    with prompt_column:
        question = st.chat_input("Ask a medical question", key="medical_question")
    st.metric("Indexed QA Records", len(service.records))
    if not question:
        return

    result = service.answer(question)
    history.extend(
        [
            {"role": "user", "content": question},
            {"role": "assistant", "result": result},
        ]
    )
    st.rerun()


def render_medical_result(result) -> None:
    st.write(result.answer)
    st.warning(result.disclaimer)
    details = st.columns(2)
    details[0].metric("Retrieval score", f"{result.score:.2f}")
    details[1].metric("Question type", result.question_type or "Not specified")
    with st.expander("Medical retrieval details"):
        st.caption("Matched MedQuAD question")
        st.write(result.matched_question or "No direct match")
        st.caption("Source")
        st.code(result.source or "No source")
        if result.focus:
            st.caption(f"Focus: {result.focus}")
        st.caption("Recognized entities")
        if result.entities:
            st.dataframe(
                [{"Entity": entity.text, "Category": entity.category} for entity in result.entities],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.write("No basic medical entities were recognized.")


def render_arxiv_chat(session_id: str, domain: str) -> None:
    with st.sidebar:
        st.subheader("Research Dataset")
        dataset_path = st.text_input(
            "arXiv metadata path",
            value=os.getenv("ARXIV_DATASET_PATH", str(DEFAULT_ARXIV_PATH)),
        )
        use_local_llm = st.toggle("Use local open-source LLM via Ollama", value=False)

    service = load_arxiv_service(dataset_path, use_local_llm)
    history_key = f"research_ui_history_{session_id}"
    history = st.session_state.setdefault(history_key, [])
    for message in history:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_arxiv_result(message["result"])
            else:
                st.write(message["content"])

    menu_column, prompt_column = st.columns([1, 11], vertical_alignment="bottom")
    with menu_column:
        render_composer_menu(domain)
    with prompt_column:
        question = st.chat_input("Ask about computer-science research", key="research_question")
    st.metric("Indexed CS Papers", len(service.papers))
    if not question:
        return

    prior_questions = [message["content"] for message in history if message["role"] == "user"]
    result = service.answer(question, history=prior_questions)
    history.extend(
        [
            {"role": "user", "content": question},
            {"role": "assistant", "result": result},
        ]
    )
    st.rerun()


def render_arxiv_result(result) -> None:
    st.write(result.answer)
    st.caption("Explanation generated locally via Ollama." if result.used_local_llm else "Retrieval and extractive-summary response.")
    if result.papers:
        st.subheader("Relevant CS papers")
        for paper in result.papers:
            with st.expander(paper.title):
                st.caption(f"ID: {paper.paper_id} | Categories: {paper.categories} | Published: {paper.published or 'Unknown'}")
                if paper.authors:
                    st.caption(f"Authors: {paper.authors}")
                st.write(ScientificNLP().summarize(paper))
    if result.concepts:
        st.subheader("Concept visualization")
        st.dataframe(
            [{"Concept": concept.text, "Relevance": concept.score} for concept in result.concepts],
            hide_index=True,
            use_container_width=True,
        )
        st.graphviz_chart(ScientificNLP().concept_graph_dot(result.concepts), use_container_width=True)


if __name__ == "__main__":
    main()
