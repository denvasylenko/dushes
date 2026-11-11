"""Display transcript: the conversation as the user saw it, per thread.

Separate from the model's history (the checkpointer): compaction rewrites the
model's history, never this. Entries, in order:

    {"id", "ts", "kind": "user",      "text", "files": [...]}
    {"id", "ts", "kind": "assistant", "text"}
    {"id", "ts", "kind": "tool",      "name", "input"}
    {"id", "ts", "kind": "card",      "changes": [...], "status": pending|accepted|partial|rejected|dismissed,
                                      "names"?: applied names when partial}
    {"id", "ts", "kind": "question",  "question", "options": [{id, label}], "multiple", "allow_text", "field"?,
                                      "status": pending|answered|dismissed, "answer"?: {ids?, labels?, text?}}
    {"id", "ts", "kind": "error",     "text"}
    {"id", "ts", "kind": "notice",    "text"}

Stores: FileTranscriptStore (one JSONL file per thread) and MemoryTranscriptStore.
Implement TranscriptStore to keep transcripts in your own database.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

_THREAD = re.compile(r"^[A-Za-z0-9_\-]{1,100}$")


def check_thread_id(thread_id: str) -> str:
    if not _THREAD.match(thread_id or ""):
        raise ValueError("invalid thread id")
    return thread_id


def new_entry(kind: str, **fields: Any) -> dict[str, Any]:
    return {"id": uuid.uuid4().hex[:12], "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": kind, **fields}


class TranscriptStore(Protocol):
    def append(self, thread_id: str, entry: dict[str, Any]) -> dict[str, Any]: ...
    def update(self, thread_id: str, entry_id: str, **patch: Any) -> None: ...
    def list(self, thread_id: str) -> list[dict[str, Any]]: ...
    def delete(self, thread_id: str) -> None: ...


class MemoryTranscriptStore:
    def __init__(self) -> None:
        self._threads: dict[str, list[dict[str, Any]]] = {}

    def append(self, thread_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        self._threads.setdefault(check_thread_id(thread_id), []).append(entry)
        return entry

    def update(self, thread_id: str, entry_id: str, **patch: Any) -> None:
        for e in self._threads.get(check_thread_id(thread_id), []):
            if e["id"] == entry_id:
                e.update(patch)

    def list(self, thread_id: str) -> list[dict[str, Any]]:
        return [dict(e) for e in self._threads.get(check_thread_id(thread_id), [])]

    def delete(self, thread_id: str) -> None:
        self._threads.pop(check_thread_id(thread_id), None)


class FileTranscriptStore:
    """One JSONL file per thread under `root`."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, thread_id: str) -> Path:
        return self.root / f"{check_thread_id(thread_id)}.jsonl"

    def append(self, thread_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        p = self._path(thread_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def list(self, thread_id: str) -> list[dict[str, Any]]:
        p = self._path(thread_id)
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    def update(self, thread_id: str, entry_id: str, **patch: Any) -> None:
        entries = self.list(thread_id)
        for e in entries:
            if e["id"] == entry_id:
                e.update(patch)
        p = self._path(thread_id)
        p.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")

    def delete(self, thread_id: str) -> None:
        self._path(thread_id).unlink(missing_ok=True)


def pending_card(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The card or question still waiting for the user (its `kind` says which)."""
    return next((e for e in reversed(entries) if e["kind"] in ("card", "question") and e.get("status") == "pending"),
                None)


def sqlite_checkpointer(path: str | Path):
    """A durable LangGraph checkpointer in an SQLite file.

    AsyncSqliteSaver must be created inside a running event loop, while configs are
    usually built at import time; this wrapper creates it on first use.
    """
    from langgraph.checkpoint.base import BaseCheckpointSaver

    class LazySqliteSaver(BaseCheckpointSaver):
        def __init__(self, file: Path):
            super().__init__()
            self.file = file
            self._inner = None

        async def _saver(self):
            if self._inner is None:
                try:
                    import aiosqlite
                    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
                except ImportError as e:
                    raise ImportError("the sqlite checkpointer needs: pip install 'formguide[sqlite]'") from e

                self.file.parent.mkdir(parents=True, exist_ok=True)
                self._inner = AsyncSqliteSaver(await aiosqlite.connect(str(self.file)))
            return self._inner

        async def aget_tuple(self, config):
            return await (await self._saver()).aget_tuple(config)

        async def alist(self, config, *, filter=None, before=None, limit=None):  # noqa: A002
            async for item in (await self._saver()).alist(config, filter=filter, before=before, limit=limit):
                yield item

        async def aput(self, config, checkpoint, metadata, new_versions):
            return await (await self._saver()).aput(config, checkpoint, metadata, new_versions)

        async def aput_writes(self, config, writes, task_id, task_path=""):
            return await (await self._saver()).aput_writes(config, writes, task_id, task_path)

        async def adelete_thread(self, thread_id):
            return await (await self._saver()).adelete_thread(thread_id)

        def get_next_version(self, current, channel):
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            return AsyncSqliteSaver.get_next_version(self, current, channel)

    return LazySqliteSaver(Path(path))
