"""formguide: a chat agent that guides users through large configurable forms.

Form-agnostic core; everything domain-specific is configured: models (any LangChain
chat model), component library, domain packs, business documents + search index
(BM25 or any LangChain vector store) and their scopes, skills and extra tools.

    from formguide import FormGuide, load_config
    guide = FormGuide(load_config("formguide.yaml"))
"""
from .attachments.extract import AttachmentStore
from .config import GuideConfig, load_config
from .domain.packs import DomainPack, DomainPackRegistry
from .form.layout import ComponentMap
from .guide import FormGuide
from .knowledge.base import KnowledgeBase
from .knowledge.index import BM25Index, Chunk, SearchIndex, VectorStoreIndex
from .models import Models
from .skills import Skill, SkillRegistry
from .transcript import FileTranscriptStore, MemoryTranscriptStore, TranscriptStore, sqlite_checkpointer

__all__ = [
    "AttachmentStore", "BM25Index", "Chunk", "ComponentMap", "DomainPack", "DomainPackRegistry", "FormGuide",
    "FileTranscriptStore", "GuideConfig", "KnowledgeBase", "MemoryTranscriptStore", "Models", "SearchIndex", "Skill",
    "SkillRegistry", "TranscriptStore", "VectorStoreIndex", "load_config", "sqlite_checkpointer",
]
