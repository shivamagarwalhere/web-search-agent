import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm import GeminiClient
from .search import DuckDuckGoSearchTool, SearchResult

@dataclass
class AgentTraceStep:
    step: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return {"step": self.step, "detail": self.detail}

@dataclass
class ResearchAgentResult:
    topic: str
    questions: List[str]
    search_results: List[SearchResult]
    report_markdown: str
    trace: List[AgentTraceStep] = field(default_factory=list)

    def sources_json(self) -> List[Dict[str, str]]:
        return [item.to_dict() for item in self.search_results]

    def trace_json(self) -> List[Dict[str, str]]:
        return [step.to_dict() for step in self.trace]

class ResearchAgent:
    def __init__(
        self,
        llm: GeminiClient,
        search_tool: Optional[DuckDuckGoSearchTool] = None,
        *,
        verbose: bool = False,
    ) -> None:
        self.llm = llm
        self.search_tool = search_tool or DuckDuckGoSearchTool()
        self.verbose = verbose
        self.trace: List[AgentTraceStep] = []

    def run(
        self, topic: str, *, num_questions: int = 5, results_per_question: int = 3
    ) -> ResearchAgentResult:
        self.trace = []
        self._log("START", f"Topic received: {topic}")

        questions = self.generate_research_questions(topic, count=num_questions)
        self._log("PLAN", f"Generated {len(questions)} research questions.")

        all_results: List[SearchResult] = []
        for idx, question in enumerate(questions, start=1):
            self._log("ACTION", f"Searching question {idx}/{len(questions)}: {question}")
            results = self.search_tool.search_and_extract(
                question, max_results=results_per_question
            )
            all_results.extend(results)
            self._log("OBSERVATION", f"Collected {len(results)} results for question {idx}.")

        report = self.compile_report(topic, questions, all_results)
        self._log("FINISH", "Compiled final markdown report.")

        return ResearchAgentResult(
            topic=topic,
            questions=questions,
            search_results=all_results,
            report_markdown=report,
            trace=self.trace,
        )

    def generate_research_questions(self, topic: str, *, count: int = 5) -> List[str]:
        system_instruction = (
            "You are a research planning assistant. Return only valid JSON. "
            "Do not include markdown fences."
        )
        prompt = f"""
Generate {count} well-structured research questions for this topic:
{topic}

Requirements:
- Questions should cover different angles of the topic.
- Questions should be specific enough for web search.
- Return only JSON in this schema:
{{
  "questions": ["question 1", "question 2"]
}}
""".strip()

        raw = self.llm.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=1.0,
            max_output_tokens=1200,
        )
        data = self._parse_json(raw)
        questions = data.get("questions", []) if isinstance(data, dict) else []
        questions = [str(q).strip() for q in questions if str(q).strip()]

        if not questions:
            raise ValueError(f"Gemini did not return questions in expected JSON format: {raw}")

        return questions[:count]

    def compile_report(
        self, topic: str, questions: List[str], search_results: List[SearchResult]
    ) -> str:
        evidence = self._build_evidence_block(search_results)
        questions_block = "\n".join(f"{idx}. {q}" for idx, q in enumerate(questions, start=1))

        system_instruction = (
            "You are a careful research analyst. Use only the evidence provided. "
            "Do not invent facts. Write concise markdown. Cite sources with [S1], [S2], etc."
        )
        prompt = f"""
Create a structured research report for the topic: {topic}

Research questions:
{questions_block}

Evidence collected from web search:
{evidence}

Report requirements:
- Use markdown.
- Include a clear title.
- Include an introduction.
- Create one section per research question.
- Summarize findings using the supplied evidence.
- Add source markers like [S1] next to claims.
- Include a conclusion.
- Include a final "Sources" section listing source id, title, and URL.
""".strip()

        return self.llm.generate(
            prompt,
            system_instruction=system_instruction,
            temperature=1.0,
            max_output_tokens=8192,
        )

    def save_outputs(self, result: ResearchAgentResult, output_dir: str | Path = "reports") -> Dict[str, Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = self._slugify(result.topic)[:70] or "research_report"

        report_path = out / f"{timestamp}_{slug}.md"
        sources_path = out / f"{timestamp}_{slug}_sources.json"
        trace_path = out / f"{timestamp}_{slug}_trace.json"

        report_path.write_text(result.report_markdown, encoding="utf-8")
        sources_path.write_text(json.dumps(result.sources_json(), indent=2), encoding="utf-8")
        trace_path.write_text(json.dumps(result.trace_json(), indent=2), encoding="utf-8")

        return {"report": report_path, "sources": sources_path, "trace": trace_path}

    def _build_evidence_block(self, results: List[SearchResult]) -> str:
        blocks = []
        for idx, item in enumerate(results, start=1):
            text = item.content or item.snippet
            blocks.append(
                f"[S{idx}]\nQuestion: {item.question}\nTitle: {item.title}\nURL: {item.url}\n"
                f"Snippet: {item.snippet}\nExtracted text: {text[:2200]}"
            )
        return "\n\n".join(blocks)

    def _log(self, step: str, detail: str) -> None:
        self.trace.append(AgentTraceStep(step=step, detail=detail))
        if self.verbose:
            print(f"[{step}] {detail}")

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        # Splitting the backticks ensures the markdown parser doesn't terminate the block early
        cleaned = re.sub(r"^" + "``" + "`" + r"(?:json)?", "", cleaned).strip()
        cleaned = re.sub("``" + "`" + r"$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")
