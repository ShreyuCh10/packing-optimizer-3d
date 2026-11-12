"""Evidence-grounded decision workflow over the local OKF Markdown repository.

The project package retriever searches SQLite package inventory, not Markdown.
This workflow therefore uses a small deterministic section search over the
existing OKF files and the project's shared Azure LLM configuration. It does
not create or require a vector database.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.models import llm

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[2]
OKF_DIR = BACKEND_DIR / "data" / "okf"
MAX_RETRIEVAL_RETRIES = 2
MAX_RETRIEVED_SECTIONS = 12


class OKFDecisionState(TypedDict, total=False):
    user_query: str
    search_queries: List[str]
    retrieved_documents: List[Dict[str, Any]]
    extracted_information: Dict[str, Any]
    missing_information: List[str]
    conflicts: List[str]
    evidence_sufficient: bool
    decision: str
    reasoning: str
    sources: List[Dict[str, Any]]
    retry_count: int
    final_response: str
    objective: str


class QueryAnalysis(BaseModel):
    objective: str = Field(description="Decision or information the user is asking for")
    search_queries: List[str] = Field(description="Short focused phrases to search the OKF documents")


class ExtractedEvidence(BaseModel):
    facts: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    evidence_sufficient: bool = False
    source_ids: List[str] = Field(default_factory=list)


class DecisionDraft(BaseModel):
    decision: str
    reasoning: str
    source_ids: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)


def _invoke_structured(schema: type[BaseModel], system: str, user: str) -> Optional[BaseModel]:
    try:
        return llm.with_structured_output(schema).invoke(
            [("system", system), ("human", user)]
        )
    except Exception:
        logger.exception("okf.structured_llm.failed schema=%s", schema.__name__)
        return None


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9]+", value or "")
        if len(token) > 2
    }


def _fallback_queries(query: str) -> List[str]:
    tokens = sorted(_tokens(query))
    return [query] + ([" ".join(tokens)] if tokens else [])


def analyze_query_node(state: OKFDecisionState) -> Dict[str, Any]:
    query = str(state.get("user_query") or "").strip()
    analysis = _invoke_structured(
        QueryAnalysis,
        "Analyze the user's packaging knowledge question. Produce concise search phrases for the supplied OKF documents. Do not answer the question or add assumed requirements.",
        query,
    )
    if analysis:
        queries = [q.strip() for q in analysis.search_queries if q.strip()]
        return {
            "objective": analysis.objective,
            "search_queries": list(dict.fromkeys([query, *queries])),
        }
    return {"objective": query, "search_queries": _fallback_queries(query)}


def _read_okf_sections() -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    if not OKF_DIR.is_dir():
        return sections
    for path in sorted(OKF_DIR.rglob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            logger.exception("okf.document.read_failed path=%s", path)
            continue
        heading = path.stem
        start_line = 1
        body: List[str] = []
        for line_number, line in enumerate(lines, start=1):
            if line.startswith("#"):
                if body and "\n".join(body).strip():
                    sections.append(_make_section(path, heading, start_line, body))
                heading = line.lstrip("#").strip() or path.stem
                start_line = line_number
                body = [line]
            else:
                if not body:
                    start_line = line_number
                body.append(line)
        if body and "\n".join(body).strip():
            sections.append(_make_section(path, heading, start_line, body))
    return sections


def _make_section(path: Path, heading: str, start_line: int, lines: List[str]) -> Dict[str, Any]:
    relative = path.relative_to(BACKEND_DIR).as_posix()
    return {
        "source_id": f"{relative}#{re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')}",
        "path": relative,
        "section": heading,
        "line_start": start_line,
        "page_number": None,
        "content": "\n".join(lines).strip(),
    }


def retrieve_okf_node(state: OKFDecisionState) -> Dict[str, Any]:
    queries = state.get("search_queries") or _fallback_queries(state.get("user_query", ""))
    query_tokens = _tokens(" ".join(queries))
    scored = []
    for section in _read_okf_sections():
        text_tokens = _tokens(section["section"] + " " + section["content"])
        overlap = len(query_tokens & text_tokens)
        if overlap:
            scored.append((overlap, section))
    scored.sort(key=lambda item: (-item[0], item[1]["path"], item[1]["line_start"]))
    docs = [dict(section, relevance_score=score) for score, section in scored[:MAX_RETRIEVED_SECTIONS]]
    return {"retrieved_documents": docs}


def extract_information_node(state: OKFDecisionState) -> Dict[str, Any]:
    docs = state.get("retrieved_documents", [])
    source_text = "\n\n".join(
        f"[{doc['source_id']}] {doc['content']}" for doc in docs
    )
    prompt = (
        f"User objective: {state.get('objective') or state.get('user_query')}\n"
        f"Evidence (the only source of facts):\n{source_text}"
    )
    extracted = _invoke_structured(
        ExtractedEvidence,
        "Extract facts, rules, requirements, constraints, values, missing inputs, and contradictions from the supplied evidence. Do not infer facts beyond it. Cite source_ids exactly as shown. Mark evidence sufficient only when these sources support a useful answer to the user's objective.",
        prompt,
    )
    if extracted:
        data = extracted.model_dump()
        valid_ids = {doc["source_id"] for doc in docs}
        data["source_ids"] = [sid for sid in data["source_ids"] if sid in valid_ids]
        return {"extracted_information": data, "missing_information": data["missing_information"], "conflicts": data["conflicts"], "evidence_sufficient": bool(data["evidence_sufficient"] and data["source_ids"])}

    # The deterministic fallback preserves evidence and avoids claiming that
    # an LLM-derived interpretation was made when the configured model failed.
    fallback = {
        "facts": [], "rules": [], "requirements": [], "constraints": [], "values": [],
        "missing_information": ["A configured language model is required to interpret the retrieved evidence for this question."],
        "conflicts": [], "evidence_sufficient": False,
        "source_ids": [doc["source_id"] for doc in docs],
    }
    return {"extracted_information": fallback, "missing_information": fallback["missing_information"], "conflicts": [], "evidence_sufficient": False}


def check_evidence_node(state: OKFDecisionState) -> Dict[str, Any]:
    info = state.get("extracted_information") or {}
    docs = state.get("retrieved_documents") or []
    sufficient = bool(info.get("evidence_sufficient") and docs and info.get("source_ids"))
    return {"evidence_sufficient": sufficient}


def route_evidence(state: OKFDecisionState) -> str:
    if state.get("conflicts"):
        return "conflicting"
    if state.get("evidence_sufficient"):
        return "sufficient"
    if int(state.get("retry_count", 0)) < MAX_RETRIEVAL_RETRIES:
        return "retry"
    return "insufficient"


def retry_retrieval_node(state: OKFDecisionState) -> Dict[str, Any]:
    retry_count = int(state.get("retry_count", 0)) + 1
    info = state.get("extracted_information") or {}
    existing = state.get("search_queries", [])
    additions = info.get("missing_information", [])
    return {
        "retry_count": retry_count,
        "search_queries": list(dict.fromkeys([*existing, *[str(item) for item in additions if str(item).strip()]])),
    }


def make_decision_node(state: OKFDecisionState) -> Dict[str, Any]:
    info = state.get("extracted_information") or {}
    draft = _invoke_structured(
        DecisionDraft,
        "Make a concise evidence-based decision for the user's objective. Use only extracted evidence. Cite only supplied source IDs. If an essential input is missing, make the decision conditional or state that no definitive decision is possible. Do not invent facts.",
        f"Objective: {state.get('objective') or state.get('user_query')}\nEvidence: {info}",
    )
    valid_ids = {doc["source_id"] for doc in state.get("retrieved_documents", [])}
    if not draft:
        return {
            "decision": "No definitive decision can be made from the available OKF evidence.",
            "reasoning": "The configured language model could not interpret the retrieved evidence. No unsupported conclusion was generated.",
            "sources": [doc for doc in state.get("retrieved_documents", [])],
        }
    source_ids = [sid for sid in draft.source_ids if sid in valid_ids]
    if not source_ids:
        return {
            "decision": "No definitive decision can be made because the generated recommendation did not cite retrieved OKF evidence.",
            "reasoning": "The workflow requires traceable document support for a decision, and no valid source reference was returned.",
            "missing_information": list(dict.fromkeys([*state.get("missing_information", []), "A decision linked to at least one retrieved OKF source."])),
            "sources": [doc for doc in state.get("retrieved_documents", [])],
        }
    docs_by_id = {doc["source_id"]: doc for doc in state.get("retrieved_documents", [])}
    return {
        "decision": draft.decision,
        "reasoning": draft.reasoning,
        "missing_information": list(dict.fromkeys([*state.get("missing_information", []), *draft.missing_information])),
        "sources": [docs_by_id[sid] for sid in source_ids],
    }


def conflicting_evidence_node(state: OKFDecisionState) -> Dict[str, Any]:
    return {
        "decision": "No definitive decision can be made until the conflicting OKF evidence is resolved.",
        "reasoning": "The retrieved evidence contains conflicting statements. See the conflict list and source references below.",
        "sources": state.get("retrieved_documents", []),
    }


def insufficient_evidence_node(state: OKFDecisionState) -> Dict[str, Any]:
    return {
        "decision": "The OKF documents do not provide sufficient evidence for a definitive decision.",
        "reasoning": "The bounded retrieval attempts did not find evidence that supports the requested decision. Supply the missing information or add authoritative OKF guidance.",
        "sources": state.get("retrieved_documents", []),
    }


def generate_response_node(state: OKFDecisionState) -> Dict[str, Any]:
    lines = [f"Decision: {state.get('decision', 'No decision available.')}", "", f"Reasoning: {state.get('reasoning', '')}"]
    missing = state.get("missing_information", [])
    conflicts = state.get("conflicts", [])
    sources = state.get("sources", [])
    if missing:
        lines.extend(["", "Missing information:", *[f"- {item}" for item in missing]])
    if conflicts:
        lines.extend(["", "Conflicts:", *[f"- {item}" for item in conflicts]])
    if sources:
        lines.extend(["", "Sources:"])
        for source in sources:
            location = f"{source.get('path')} — {source.get('section')} (line {source.get('line_start')}"
            if source.get("page_number") is not None:
                location += f", page {source['page_number']}"
            location += ")"
            lines.append(f"- {location}; source ID: `{source.get('source_id')}`")
    else:
        lines.extend(["", "Sources: No relevant OKF sections were retrieved."])
    lines.extend(["", "Caveat: OKF Markdown sources have no page numbers; file, section, and starting line are provided instead."])
    return {"final_response": "\n".join(lines)}


builder = StateGraph(OKFDecisionState)
builder.add_node("analyze_query", analyze_query_node)
builder.add_node("retrieve_okf", retrieve_okf_node)
builder.add_node("extract_information", extract_information_node)
builder.add_node("check_evidence", check_evidence_node)
builder.add_node("retry_retrieval", retry_retrieval_node)
builder.add_node("make_decision", make_decision_node)
builder.add_node("conflicting_response", conflicting_evidence_node)
builder.add_node("insufficient_response", insufficient_evidence_node)
builder.add_node("generate_response", generate_response_node)
builder.add_edge(START, "analyze_query")
builder.add_edge("analyze_query", "retrieve_okf")
builder.add_edge("retrieve_okf", "extract_information")
builder.add_edge("extract_information", "check_evidence")
builder.add_conditional_edges(
    "check_evidence", route_evidence,
    {"retry": "retry_retrieval", "sufficient": "make_decision", "conflicting": "conflicting_response", "insufficient": "insufficient_response"},
)
builder.add_edge("retry_retrieval", "retrieve_okf")
builder.add_edge("make_decision", "generate_response")
builder.add_edge("conflicting_response", "generate_response")
builder.add_edge("insufficient_response", "generate_response")
builder.add_edge("generate_response", END)

okf_workflow = builder
app = builder.compile()


def run_okf_decision(user_query: str) -> Dict[str, Any]:
    """Run the OKF evidence workflow and return its complete trace state."""
    result = app.invoke({"user_query": user_query, "retry_count": 0})
    return dict(result)
