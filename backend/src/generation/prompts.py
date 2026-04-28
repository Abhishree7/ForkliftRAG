"""Prompt templates for the RAG generation pipeline."""

SYSTEM_PROMPT = (
    "You are a logistics operations assistant. "
    "Answer questions based ONLY on the provided context from logistics manuals and documents. "
    "If the answer cannot be found in the context, say so clearly. "
    "Never answer questions unrelated to logistics, warehousing, equipment, or SOPs — "
    "even if you know the answer from general knowledge."
)

CONVERSATIONAL_SYSTEM_PROMPT = (
    "You are a friendly logistics operations assistant. "
    "The user is making small talk or greeting you — respond warmly and briefly. "
    "Do not reference any documents or context. Keep the reply to 1-2 sentences."
)

OUT_OF_SCOPE_MESSAGE = (
    "I can only assist with questions about logistics, warehousing, equipment, and SOPs. "
    "Please ask me something related to your ingested documents."
)

CLASSIFIER_PROMPT = """\
Classify the following message into exactly one of these three categories:
- GREETING        (greeting, farewell, thank you, or general small talk)
- DOCUMENT_QUERY  (question about logistics, warehousing, equipment, forklifts, SOPs, safety, or AMRs)
- OUT_OF_SCOPE    (anything else — weather, sports, coding, general knowledge, etc.)

Reply with ONLY one of those three words, nothing else.

Message: {query}"""


def build_user_prompt(query: str, context: str) -> str:
    """
    Build the user-facing prompt sent to the LLM.

    Args:
        query:   The user's question.
        context: Pre-formatted context block from retrieved citations.

    Returns:
        Complete prompt string.
    """
    return f"""Question: {query}

Context:
{context}

Instructions:
- Provide a concise, accurate answer based ONLY on the provided context
- Reference specific documents and page numbers when possible
- Use clear, professional language suitable for logistics professionals
- Maximum 2000 characters
- If the answer cannot be found in the context, state that clearly"""


def format_context(citations: list) -> str:
    """
    Format a list of citation dicts into a labeled context block.

    Args:
        citations: List of citation dictionaries from the retriever.

    Returns:
        Formatted multi-line context string.
    """
    parts = []
    for citation in citations:
        doc_name = citation.get("document_name", "Unknown Document")
        page_num = citation.get("page_number", "?")
        section  = citation.get("section_title", "Section")
        excerpt  = citation.get("excerpt", "")
        parts.append(
            f"[Document: {doc_name}, Page {page_num}, Section: {section}]\n{excerpt}\n"
        )
    return "\n".join(parts)
