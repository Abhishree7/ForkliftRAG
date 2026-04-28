"""LLM handler for Groq API integration."""
from typing import List, Dict, Optional
from groq import Groq
import logging
import os

from src.generation.prompts import (
    SYSTEM_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT,
    CLASSIFIER_PROMPT,
    build_user_prompt,
    format_context,
)

logger = logging.getLogger(__name__)


class LLMHandler:
    """Handler for Groq API (Llama 3.3 70B)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile",
                 temperature: float = 0.3, max_tokens: int = 500, timeout: int = 60):
        """
        Initialize LLM handler.

        Args:
            api_key:     Groq API key (if None, reads from GROQ_API_KEY env var)
            model:       Groq model name
            temperature: Sampling temperature (0.3 = factual)
            max_tokens:  Maximum tokens in response
            timeout:     Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided and GROQ_API_KEY env var not set")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        try:
            self.client = Groq(api_key=self.api_key, timeout=timeout)
            logger.info(f"Initialized LLM handler with Groq model: {model}")
        except Exception as e:
            logger.error(f"Error initializing LLM handler: {str(e)}")
            raise

    def classify_query(self, query: str) -> str:
        """
        Ask Groq to classify the query.

        Returns one of: 'GREETING', 'DOCUMENT_QUERY', 'OUT_OF_SCOPE'.
        Defaults to 'DOCUMENT_QUERY' on any error.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=5,
                temperature=0,
                messages=[{"role": "user", "content": CLASSIFIER_PROMPT.format(query=query)}],
            )
            label = completion.choices[0].message.content.strip().upper()
            logger.info(f"Query classification: '{label}' for: {query[:60]}")
            if label in ("GREETING", "OUT_OF_SCOPE"):
                return label
            return "DOCUMENT_QUERY"
        except Exception as e:
            logger.warning(f"Classification failed, defaulting to DOCUMENT_QUERY: {e}")
            return "DOCUMENT_QUERY"

    def generate_conversational_response(self, query: str) -> str:
        """
        Generate a short, friendly reply for greetings and small talk —
        no document context involved.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=80,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": CONVERSATIONAL_SYSTEM_PROMPT},
                    {"role": "user",   "content": query},
                ],
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            raise

    def generate_response(self, query: str, citations: List[Dict]) -> str:
        """
        Generate a response using Groq based on retrieved citations.

        Args:
            query:     User query
            citations: List of citation dictionaries from the retriever

        Returns:
            Generated response text
        """
        context = format_context(citations)
        prompt  = build_user_prompt(query, context)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )

            generated_text = completion.choices[0].message.content.strip()
            logger.info(f"Generated response of length {len(generated_text)}")
            return generated_text
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
