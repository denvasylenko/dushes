"""Configuration: in code (GuideConfig) or from a YAML file (load_config).

In code:

    from formguide import FormGuide, GuideConfig, Models, KnowledgeBase, VectorStoreIndex, SkillRegistry
    from langchain_openai import AzureChatOpenAI, ChatOpenAI

    guide = FormGuide(GuideConfig(
        models=Models(agent=AzureChatOpenAI(azure_deployment="gpt-5", api_version="2025-04-01-preview"),
                      research=ChatOpenAI(model="gpt-5-mini")),
        domain_packs=DomainPackRegistry(directory="domain_packs"),
        knowledge=KnowledgeBase("data/kb", index=VectorStoreIndex(my_pgvector),
                                scopes={"loan_application": ["loan_application", "bank_common"]}),
        skills=SkillRegistry.from_dir("skills"),
    ))

From YAML (paths are relative to the YAML file, ${ENV_VARS} are expanded). The shortest
working file is one line, `model: "openai:gpt-5"` (one model for every role); the
FORMGUIDE_MODEL environment variable does the same without a file. Everything else is optional:

    data_dir: data
    model: "anthropic:claude-haiku-5-5"              # one model for every role, or per role:
    models:
      agent: {class: "langchain_openai:AzureChatOpenAI", azure_deployment: gpt-5, api_version: "2025-04-01-preview"}
      research: "openai:gpt-5-mini"                 # init_chat_model string
      extract: {provider: anthropic, model: claude-haiku-5-5, max_tokens: 8000}
    components:                                      # your tags; a field is a role or a field spec
      containers: {Tabs: tabs, Tab: tab}
      fields: {TextField: text, Select: {role: select, value: id, options_prop: items}}
    domain_packs: {dir: domain_packs, provider: "my_app.packs:load_pack"}
    knowledge:
      dir: data/kb
      index: bm25                                   # or {factory: "my_app.vectors:make_store", filter: "my_app.vectors:ns_filter"}
      scopes: {loan_application: [loan_application, bank_common]}
    skills: {dir: skills}
    tools: ["my_app.tools:check_status"]
    memory: {max_history_tokens: 60000, keep_turns: 4, model: "anthropic:claude-haiku-5-5"}
    checkpointer: {sqlite: data/checkpoints.sqlite}  # model history; default in memory
    transcripts: {dir: data/transcripts}             # what the user saw; default files under data_dir
    max_tool_rounds: 10
    interrupt_mode: legacy                           # confirmation cards: legacy (CopilotKit) | structured (AG-UI 1.0) | both
    confirm_tools: [submit_application]              # these tools always ask the user before running
    suggestions: {enabled: true, max: 3}             # quick replies after each answer (a cheap model)
    actions: {request_file: false, review_form: true}   # switch agent actions off (true | false | auto)
    attachments: {enabled: true, privacy_note: "Your file stays on our server; only the values reach the chat."}
    tracing: {callbacks: ["my_app.tracing:langfuse_handler"], tags: [staging]}   # LangSmith: env vars only
    # tracing: {otel: {exporter: otlp, endpoint: "http://collector:4317"}}   # OpenTelemetry (formguide[otel])
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver

from .attachments.extract import AttachmentStore
from .domain.packs import DomainPackRegistry
from .form.layout import DEFAULT_COMPONENTS, ComponentMap
from .knowledge.base import KnowledgeBase
from .knowledge.index import BM25Index, SearchIndex, VectorStoreIndex
from .agent.actions import parse_config as parse_actions
from .agent.memory import MemoryConfig
from .otel import check as check_otel
from .models import Models
from .skills import SkillRegistry, import_object
from .transcript import FileTranscriptStore, MemoryTranscriptStore, TranscriptStore, sqlite_checkpointer


def default_models() -> Models:
    """FORMGUIDE_MODEL (an init_chat_model string such as "openai:gpt-5") or the Anthropic defaults."""
    env = os.environ.get("FORMGUIDE_MODEL")
    return Models(agent=env) if env else Models.anthropic()


@dataclass
class SuggestionsConfig:
    """Quick replies: 1..max short next messages after each answer (a CUSTOM `suggestions` event)."""
    enabled: bool = False
    model: Any = None          # ModelSpec; default: the memory role's model
    max: int = 3
    timeout: float = 4.0       # seconds; on timeout or error no event is sent


@dataclass
class TracingConfig:
    """Tracers for every turn. LangSmith needs nothing here: set LANGSMITH_TRACING=true and its API key.
    `callbacks`: factories returning LangChain callback handlers (e.g. Langfuse); `tags`: added to every turn."""
    callbacks: list[Any] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    # OpenTelemetry export: {exporter: otlp | zipkin | azure_monitor | console | host | "module:factory",
    # endpoint?, headers?, service_name?, sample_ratio?} (see otel.py); None = off
    otel: dict | None = None


@dataclass
class GuideConfig:
    models: Models = field(default_factory=default_models)
    data_dir: str | Path = "data"                   # deps maps, KB and attachments default to subfolders
    components: ComponentMap = DEFAULT_COMPONENTS
    domain_packs: DomainPackRegistry | None = None   # default: no packs (neutral persona)
    knowledge: KnowledgeBase | None = None           # default: BM25 over <data_dir>/kb
    skills: SkillRegistry | None = None
    attachments: AttachmentStore | None = None       # default: <data_dir>/attachments
    tools: list[BaseTool] = field(default_factory=list)   # extra tools for every form
    checkpointer: BaseCheckpointSaver | None = None  # model history; default in memory (sqlite_checkpointer(), Postgres, Redis)
    transcripts: TranscriptStore | None = None       # display transcript; default: files under <data_dir>/transcripts
    max_tool_rounds: int = 10
    learn_dependencies: bool = True                  # persist observed field dependencies per form
    memory: MemoryConfig = field(default_factory=MemoryConfig)   # long-chat compaction
    # How confirmation cards reach the client: "legacy" = CUSTOM on_interrupt (CopilotKit,
    # ag-ui-langgraph), "structured" = RUN_FINISHED.outcome interrupts (AG-UI 1.0), or "both".
    interrupt_mode: str = "legacy"
    confirm_tools: list[str] = field(default_factory=list)   # tools that always ask the user first
    suggestions: SuggestionsConfig = field(default_factory=SuggestionsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    # Which agent actions exist: {action: True | False | "auto"} (see agent/actions.py); missing = default.
    actions: dict[str, Any] = field(default_factory=dict)
    attachments_enabled: bool = True                 # False: no uploads and no reading of attached files
    privacy_note: str = ""                           # shown on upload requests (`privacy`)


# ===================================================================== YAML


def _expand(v: Any) -> Any:
    if isinstance(v, str):
        return os.path.expandvars(v)
    if isinstance(v, dict):
        return {k: _expand(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_expand(x) for x in v]
    return v


def _model(spec: Any) -> Any:
    """YAML model spec: init_chat_model string / {provider, model, ...} / {class: "pkg:Class", ...kwargs}.
    Kept as a spec; FormGuide builds it (formguide.models.build_model)."""
    return spec


def _index(spec: Any) -> SearchIndex:
    if spec in (None, "bm25"):
        return BM25Index()
    obj = import_object(spec["factory"])()
    if hasattr(obj, "search") and hasattr(obj, "ephemeral"):   # already a SearchIndex
        return obj
    flt = import_object(spec["filter"]) if spec.get("filter") else None
    return VectorStoreIndex(obj, filter_builder=flt, fetch_factor=int(spec.get("fetch_factor", 5)))


def load_config(path: str | Path) -> GuideConfig:
    path = Path(path)
    raw = _expand(yaml.safe_load(path.read_text()) or {})
    base = path.parent

    def rel(p: str | None) -> Path | None:
        return (base / p).resolve() if p else None

    cfg = GuideConfig()
    cfg.data_dir = rel(raw.get("data_dir", "data"))
    if raw.get("model"):
        cfg.models = Models(agent=_model(raw["model"]))
    if isinstance(raw.get("models"), str):
        cfg.models = Models(agent=raw["models"])
    elif raw.get("models"):
        m = raw["models"]
        cfg.models = Models(agent=_model(m["agent"]), research=_model(m.get("research")),
                            compile=_model(m.get("compile")), extract=_model(m.get("extract")))
    if raw.get("components"):
        c = raw["components"]
        cfg.components = ComponentMap(containers=c.get("containers") or DEFAULT_COMPONENTS.containers,
                                      fields=c.get("fields") or DEFAULT_COMPONENTS.fields)
    if raw.get("domain_packs"):
        d = raw["domain_packs"]
        cfg.domain_packs = DomainPackRegistry(
            directory=rel(d.get("dir")), packs=d.get("packs"),
            provider=import_object(d["provider"]) if d.get("provider") else None)
    k = raw.get("knowledge") or {}
    cfg.knowledge = KnowledgeBase(rel(k.get("dir")) or Path(cfg.data_dir) / "kb", index=_index(k.get("index")),
                                  scopes=k.get("scopes"))
    if raw.get("skills"):
        cfg.skills = SkillRegistry.from_dir(rel(raw["skills"].get("dir", "skills")))
    cfg.tools = [import_object(t) for t in raw.get("tools") or []]
    cfg.max_tool_rounds = int(raw.get("max_tool_rounds", cfg.max_tool_rounds))
    cp = raw.get("checkpointer")
    if isinstance(cp, dict) and cp.get("sqlite"):
        cfg.checkpointer = sqlite_checkpointer(rel(cp["sqlite"]))
    tr = raw.get("transcripts")
    if tr == "memory":
        cfg.transcripts = MemoryTranscriptStore()
    elif isinstance(tr, dict) and tr.get("dir"):
        cfg.transcripts = FileTranscriptStore(rel(tr["dir"]))
    cfg.learn_dependencies = bool(raw.get("learn_dependencies", True))
    cfg.interrupt_mode = str(raw.get("interrupt_mode", cfg.interrupt_mode))
    if cfg.interrupt_mode not in ("legacy", "structured", "both"):
        raise ValueError("interrupt_mode must be legacy, structured or both")
    if raw.get("memory"):
        m = raw["memory"]
        cfg.memory = MemoryConfig(max_history_tokens=m.get("max_history_tokens", 60_000),
                                  keep_turns=int(m.get("keep_turns", 4)), model=m.get("model"))
    ct = raw.get("confirm_tools") or []
    if not isinstance(ct, list) or not all(isinstance(x, str) for x in ct):
        raise ValueError("confirm_tools must be a list of tool names")
    cfg.confirm_tools = list(ct)
    tr = raw.get("tracing") or {}
    unknown = set(tr) - {"callbacks", "tags", "otel"}
    if unknown:
        raise ValueError(f"tracing: unknown key(s) {sorted(unknown)}")
    factories = []
    for ref in tr.get("callbacks") or []:
        try:
            factories.append(import_object(str(ref)))
        except (ImportError, AttributeError) as e:
            raise ValueError(f"tracing.callbacks: cannot import {ref!r}: {e}") from None
    otel_spec = check_otel(tr["otel"]) if tr.get("otel") is not None else None
    cfg.tracing = TracingConfig(callbacks=factories, tags=[str(t) for t in tr.get("tags") or []], otel=otel_spec)
    cfg.actions = parse_actions(raw.get("actions"))
    at = raw.get("attachments")
    if at is not None:
        at = {"enabled": at} if isinstance(at, bool) else at
        unknown = set(at) - {"enabled", "privacy_note"}
        if unknown:
            raise ValueError(f"attachments: unknown key(s) {sorted(unknown)}")
        cfg.attachments_enabled = bool(at.get("enabled", True))
        cfg.privacy_note = str(at.get("privacy_note") or "").strip()[:200]
    sg = raw.get("suggestions")
    if sg is not None:
        sg = {"enabled": sg} if isinstance(sg, bool) else sg
        unknown = set(sg) - {"enabled", "model", "max", "timeout"}
        if unknown:
            raise ValueError(f"suggestions: unknown key(s) {sorted(unknown)}")
        cfg.suggestions = SuggestionsConfig(enabled=bool(sg.get("enabled", True)), model=sg.get("model"),
                                            max=max(1, min(int(sg.get("max", 3)), 5)),
                                            timeout=float(sg.get("timeout", 4.0)))
    return cfg
