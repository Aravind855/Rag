"""
OKF (Open Knowledge Format v0.2) Autonomous Knowledge Agent.

Navigates and retrieves from an OKF v0.2 bundle directly using an LLM-Wiki
pattern (no chunking, no vector database).
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool

# Force UTF-8 output encoding for Windows compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from llm import get_llm
from OKF.okf_toolkit import OKFBundleToolkit

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OKFAgent")

SYSTEM_PROMPT = """You are the NexaCore Autonomous Knowledge Agent, powered by the Open Knowledge Format (OKF v0.2).
You navigate an authoritative, machine-readable LLM-Wiki knowledge bundle.

YOUR CORE OPERATING RULES:
1. NEVER GUESS OR HALLUCINATE: For any question about policies, SLAs, APIs, quotas, rate limits, or architecture, you MUST inspect and retrieve the corresponding OKF concept before answering.
2. DISCOVERY WORKFLOW:
   - When searching via `find_concepts(query=...)`, use concise search keywords (e.g. 'api standards', 'rate limit', 'reimbursement', 'SEV-1', 'commission', 'identity').
   - Once identified, call `read_concept(concept_id_or_path=...)` to retrieve the complete, authoritative text.
   - Once you have called `read_concept(...)` and retrieved the document, SYNTHESIZE your final answer directly from it. Do not repeatedly re-search for terms already present in the retrieved content.
   - Check `inspect_trust(concept_id=...)` if you need to verify sign-off authority or freshness.
3. GROUNDED SYNTHESIS: Quote exact numbers, SLA targets, status codes, and formulas directly from the retrieved document.
4. MANDATORY CITATIONS: Always cite the authoritative Concept ID (e.g. `[nc.eng.api_standards]`), type, and verifier in your final answer.
"""


class OKFAgent:
    """Autonomous Knowledge Agent that traverses and retrieves from an OKF bundle."""

    def __init__(
        self,
        bundle_path: str = "d:/RAG/OKF/OKF_bundle",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        verbose: bool = True
    ):
        self.toolkit = OKFBundleToolkit(bundle_path)
        self.verbose = verbose
        
        # Initialize LLM via multi-provider factory
        self.llm = get_llm(
            provider=provider,
            model=model,
            temperature=temperature
        )
        
        # Build LangChain-compatible tools
        self.tools = self._create_tools()
        self.tools_map = {t.name: t for t in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _create_tools(self) -> List[Any]:
        """Wrap toolkit methods into LangChain tool definitions."""
        tk = self.toolkit

        @tool
        def browse_catalog(domain: str = "") -> str:
            """Browse the OKF catalog. Pass empty string for root catalog, or domain name like 'engineering', 'security', 'finance', 'operations', 'sales'."""
            return tk.browse_catalog(domain)

        @tool
        def find_concepts(query: str, concept_type: str = "") -> str:
            """Search for concepts by keyword (e.g. 'rate limit', 'SEV-1', 'p95', 'reimbursement', 'commission'). Optionally filter by concept_type."""
            return tk.find_concepts(query, concept_type if concept_type else None)

        @tool
        def read_concept(concept_id_or_path: str) -> str:
            """Retrieve the entire content of an OKF concept by its ID (e.g. 'nc.eng.api_standards') or file path."""
            return tk.read_concept(concept_id_or_path)

        @tool
        def inspect_trust(concept_id: str) -> str:
            """Inspect trust signals, verification tier, verifier identity, and freshness for a concept ID."""
            return tk.inspect_trust(concept_id)

        @tool
        def list_all_concepts() -> str:
            """List all registered concept IDs, titles, and types in the bundle."""
            return tk.list_all_concepts()

        return [browse_catalog, find_concepts, read_concept, inspect_trust, list_all_concepts]

    def ask(self, question: str, max_iterations: int = 6) -> str:
        """Run the agent against a user query and return the synthesized response."""
        messages: List[Any] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=question)
        ]

        if self.verbose:
            print("\n" + "=" * 70)
            print(f"[USER QUERY]: {question}")
            print("=" * 70)

        for step in range(1, max_iterations + 1):
            ai_msg: AIMessage = self.llm_with_tools.invoke(messages)
            messages.append(ai_msg)

            # Check if LLM requested tool calls
            tool_calls = getattr(ai_msg, "tool_calls", [])
            if not tool_calls:
                # Agent has arrived at the final response
                if self.verbose:
                    print(f"\n[AGENT FINAL ANSWER]:\n{ai_msg.content}")
                return ai_msg.content

            # Execute requested tool calls
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool_args = tc.get("args", {})
                call_id = tc.get("id")

                if self.verbose:
                    print(f"\n> [Agent Action {step}]: {tool_name}({tool_args})")

                if tool_name in self.tools_map:
                    try:
                        tool_func = self.tools_map[tool_name]
                        result = tool_func.invoke(tool_args)
                    except Exception as err:
                        result = f"Error executing tool {tool_name}: {err}"
                else:
                    result = f"Tool {tool_name} not found."

                if self.verbose:
                    preview = str(result)[:180].replace("\n", " ")
                    print(f"  |-- Result Preview: {preview}...")

                messages.append(ToolMessage(content=str(result), tool_call_id=call_id))

        return "Agent exceeded maximum tool call iterations without reaching an answer."


def interactive_cli():
    """Run an interactive CLI session with the OKF Knowledge Agent."""
    print("=" * 70)
    print(" NEXACORE OKF v0.2 AUTONOMOUS KNOWLEDGE AGENT")
    print(" (Direct File-Based LLM-Wiki Traversal - No Vector DB / No RAG)")
    print("=" * 70)
    print("Type your questions below. Type 'exit' or 'quit' to end.\n")

    agent = OKFAgent(bundle_path="d:/RAG/OKF/OKF_bundle", verbose=True)

    while True:
        try:
            query = input("\nAsk OKF Agent > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Exiting OKF Agent. Goodbye!")
                break
            agent.ask(query)
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].lower()
        if first_arg in ["-i", "--interactive", "chat"]:
            interactive_cli()
        else:
            cli_question = " ".join(sys.argv[1:])
            agent = OKFAgent(bundle_path="d:/RAG/OKF/OKF_bundle", verbose=True)
            agent.ask(cli_question)
    else:
        # Default to interactive mode if run directly without arguments
        interactive_cli()
