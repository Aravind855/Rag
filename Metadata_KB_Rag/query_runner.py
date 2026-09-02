"""
End-to-End RAG Query Runner Module for NexaCore Knowledge Base RAG (Project 2).

Orchestrates RAG Query Execution:
1. Receives user prompt + optional metadata filters
2. Calls NexaCoreRetriever for metadata-filtered context retrieval
3. Injects retrieved context & citation labels into grounded system prompt
4. Synthesizes response using Google Gemini LLM
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from llama_index.core.schema import NodeWithScore

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Ensure current directory is in sys.path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from metadata import format_citation_label
from retriever import NexaCoreRetriever

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("NexaCoreQueryRunner")


@dataclass
class QueryResult:
    """Structured response container for RAG query execution."""

    query: str
    answer: str
    retrieved_nodes: List[NodeWithScore]
    citations: List[str]
    execution_time_sec: float
    filters_used: Dict[str, Any]

    def display(self) -> None:
        """Print a formatted human-readable summary of the query result."""
        print("\n" + "=" * 80)
        print(f" NEXACORE KB RAG QUERY RESULT (Time: {self.execution_time_sec:.2f}s)")
        print("=" * 80)
        print(f"\nUser Query     : {self.query}")
        print(f"Metadata Filters: {self.filters_used}")
        print(f"Nodes Retrieved : {len(self.retrieved_nodes)}")
        
        print("\nCitations Used :")
        if self.citations:
            for idx, cit in enumerate(self.citations, 1):
                print(f"  [{idx}] {cit}")
        else:
            print("  None")

        print("\n" + "-" * 80)
        print("GENERATED ANSWER (Grounded in Knowledge Base):")
        print("-" * 80)
        print(self.answer.strip())
        print("=" * 80 + "\n")


class NexaCoreQueryRunner:
    """End-to-End Grounded RAG Query Pipeline powered by NexaCoreRetriever and Google Gemini."""

    def __init__(
        self,
        retriever: Optional[NexaCoreRetriever] = None,
        collection_name: str = "nexacore_kb",
        model_name: str = "gemini-2.5-flash",
    ):
        """Initialize RAG Query Runner.

        Args:
            retriever: Pre-configured NexaCoreRetriever instance.
            collection_name: Qdrant collection name if initializing new retriever.
            model_name: Google Gemini model identifier.
        """
        self.retriever = retriever or NexaCoreRetriever(collection_name=collection_name)
        self.model_name = model_name

        # Ensure API key is configured
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required.")

        os.environ["GEMINI_API_KEY"] = self.api_key
        os.environ["GOOGLE_API_KEY"] = self.api_key

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Initialized NexaCoreQueryRunner using google.genai Client with model '{self.model_name}'.")
        except Exception as err:
            logger.error(f"Failed to initialize google.genai Client: {err}")
            raise err

    def _build_grounded_prompt(self, query: str, formatted_context: str) -> str:
        """Construct grounded prompt instructing LLM to answer strictly based on context."""
        prompt = f"""You are NexaCore Knowledge Assistant, an enterprise RAG AI.
Your task is to answer the user's query accurately using ONLY the provided Knowledge Base Context.

--- GROUNDING INSTRUCTIONS ---
1. Base your answer STRICTLY on the retrieved context blocks below.
2. For every key fact, policy detail, or technical guideline you mention, cite the exact source using the [Source: ... | Dept: ... | Page: ...] citation format provided in the context header.
3. If the context does not contain enough information to answer the question, clearly state: "The provided NexaCore Knowledge Base does not contain information to answer this query."
4. Do NOT make up facts, hallucinate, or use external knowledge not present in the context blocks.

--- RETRIEVED KNOWLEDGE BASE CONTEXT ---
{formatted_context}

--- USER QUERY ---
{query}

--- YOUR GROUNDED RESPONSE (WITH CITATIONS) ---
"""
        return prompt

    def run_query(
        self,
        query: str,
        department: Optional[str] = None,
        document_type: Optional[str] = None,
        file_type: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5,
        min_score: Optional[float] = None,
    ) -> QueryResult:
        """Execute end-to-end retrieval and Gemini answer synthesis."""
        start_time = time.time()
        filters_used = {
            "department": department,
            "document_type": document_type,
            "file_type": file_type,
            "category": category,
        }

        # Step 1: Retrieve metadata-filtered context
        retrieved_nodes = self.retriever.retrieve(
            query=query,
            department=department,
            document_type=document_type,
            file_type=file_type,
            category=category,
            top_k=top_k,
            min_score=min_score,
        )

        # Step 2: Format Context & Citations
        formatted_context = self.retriever.format_retrieved_context(retrieved_nodes)
        citations = [format_citation_label(node.node.metadata) for node in retrieved_nodes if node.node.metadata]

        # Step 3: Build Grounded Prompt
        prompt = self._build_grounded_prompt(query, formatted_context)

        # Step 4: Generate LLM Answer
        logger.info(f"Generating grounded answer using Gemini '{self.model_name}'...")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            answer_text = response.text if hasattr(response, "text") and response.text else "No response generated."
        except Exception as err:
            logger.error(f"Error during Gemini LLM generation: {err}", exc_info=True)
            answer_text = f"An error occurred while generating the answer: {err}"

        exec_time = time.time() - start_time

        result = QueryResult(
            query=query,
            answer=answer_text,
            retrieved_nodes=retrieved_nodes,
            citations=list(dict.fromkeys(citations)),  # Deduplicate preserving order
            execution_time_sec=exec_time,
            filters_used={k: v for k, v in filters_used.items() if v is not None},
        )
        return result


if __name__ == "__main__":
    print("=" * 80)
    print(" NEXACORE KB RAG - END-TO-END RAG QUERY RUNNER TEST")
    print("=" * 80)

    try:
        runner = NexaCoreQueryRunner(collection_name="nexacore_kb", model_name="gemini-2.5-flash")

        # Test Query 1: Policy question with HR filter
        query1 = "What is the policy regarding casual leave and remote work?"
        print(f"\nRunning Query 1: '{query1}' [Filter: department='hr']")
        res1 = runner.run_query(query=query1, department="hr", top_k=3)
        res1.display()

        # Test Query 2: Technical question with engineering filter
        query2 = "What are the core standards for API design and authentication?"
        print(f"\nRunning Query 2: '{query2}' [Filter: department='engineering']")
        res2 = runner.run_query(query=query2, department="engineering", top_k=3)
        res2.display()

    except Exception as ex:
        logger.error(f"Query Runner Test Failed: {ex}", exc_info=True)
        sys.exit(1)
