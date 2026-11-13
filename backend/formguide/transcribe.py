"""Server-side dictation: audio from the chat's microphone -> text.

    transcription:
      provider: faster_whisper      # default: a local Whisper model (the `transcribe` extra)
      model: small                  # tiny | base | small | medium | large-v3 | a local path
      device: auto                  # auto | cpu | cuda
      compute_type: int8            # int8 on a CPU, float16 on a GPU
      language: null                # null: the request's language, else detected
      max_seconds: 120              # longer recordings are cut
      max_bytes: 10000000           # a larger upload gets 413
    # or provider: openai (model: whisper-1 | gpt-4o-transcribe, OPENAI_API_KEY)
    # or provider: "my_app.speech:transcribe"   # fn(data: bytes, filename, language) -> str (sync or async)

The faster-whisper model is loaded on the first request (downloaded once into the Hugging Face cache)
and runs in a worker thread, so a turn never waits on it.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import io
import threading
from dataclasses import dataclass
from typing import Any

KEYS = {"provider", "model", "device", "compute_type", "language", "max_seconds", "max_bytes"}


@dataclass
class TranscriptionConfig:
    provider: str = "faster_whisper"
    model: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    language: str | None = None
    max_seconds: int = 120
    max_bytes: int = 10_000_000

    @classmethod
    def parse(cls, raw: Any) -> TranscriptionConfig | None:
        """The YAML section -> a config; None (or false) turns transcription off, true means the defaults."""
        if raw in (None, False):
            return None
        if raw is True:
            return cls()
        if not isinstance(raw, dict):
            raise ValueError("transcription must be a mapping (provider, model, ...) or true")
        unknown = set(raw) - KEYS
        if unknown:
            raise ValueError(f"transcription: unknown key(s) {sorted(unknown)}; allowed: {sorted(KEYS)}")
        c = cls(**{k: v for k, v in raw.items() if v is not None or k == "language"})
        c.max_seconds = max(1, int(c.max_seconds))
        c.max_bytes = max(1000, int(c.max_bytes))
        return c


class TooLarge(ValueError):
    """The recording is over max_bytes."""


class Transcriber:
    def __init__(self, cfg: TranscriptionConfig):
        self.cfg = cfg
        self._model: Any = None
        self._lock = threading.Lock()

    async def transcribe(self, data: bytes, filename: str = "audio.webm", language: str | None = None) -> dict:
        """{text, language} for one recording."""
        if len(data) > self.cfg.max_bytes:
            raise TooLarge(f"the recording is over {self.cfg.max_bytes} bytes")
        lang = _lang(self.cfg.language or language)
        p = self.cfg.provider
        if p == "faster_whisper":
            return await asyncio.to_thread(self._local, data, lang)
        if p == "openai":
            return await self._openai(data, filename, lang)
        if ":" in p:   # a host's own function
            mod, _, name = p.partition(":")
            fn = getattr(importlib.import_module(mod), name)
            out = fn(data, filename, lang)
            text = await out if inspect.isawaitable(out) else out
            return {"text": str(text or "").strip(), "language": lang}
        raise ValueError(f"transcription.provider: unknown {p!r} (faster_whisper, openai or module:function)")

    def _load(self) -> Any:
        with self._lock:
            if self._model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as e:  # pragma: no cover - the optional extra
                    raise RuntimeError("transcription needs the `transcribe` extra: pip install 'formguide[transcribe]'") from e
                self._model = WhisperModel(self.cfg.model, device=self.cfg.device, compute_type=self.cfg.compute_type)
            return self._model

    def _local(self, data: bytes, lang: str | None) -> dict:
        model = self._load()
        audio = decode(data, self.cfg.max_seconds)
        if not len(audio):
            return {"text": "", "language": lang}
        segments, info = model.transcribe(audio, language=lang, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        return {"text": text, "language": getattr(info, "language", None) or lang}

    async def _openai(self, data: bytes, filename: str, lang: str | None) -> dict:
        from openai import AsyncOpenAI   # comes with langchain-openai

        model = self.cfg.model if self.cfg.model not in ("small", "") else "whisper-1"
        r = await AsyncOpenAI().audio.transcriptions.create(model=model, file=(filename, data),
                                                           **({"language": lang} if lang else {}))
        return {"text": (r.text or "").strip(), "language": lang}


SAMPLE_RATE = 16000


def decode(data: bytes, max_seconds: int) -> Any:
    """Any recording the browser makes (webm/opus, mp4/aac, ogg, wav) -> 16 kHz mono float32 samples, cut at
    max_seconds. Decoded here (PyAV) rather than by faster-whisper, whose own decoder follows PyAV's API less."""
    import av
    import numpy as np

    out: list = []
    total, limit = 0, SAMPLE_RATE * max_seconds
    with av.open(io.BytesIO(data)) as box:
        stream = next((s for s in box.streams if s.type == "audio"), None)
        if stream is None:
            return np.zeros(0, dtype=np.float32)
        resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        for frame in box.decode(stream):
            for f in resampler.resample(frame):
                a = f.to_ndarray().reshape(-1)
                out.append(a)
                total += len(a)
            if total >= limit:
                break
        for f in resampler.resample(None):
            out.append(f.to_ndarray().reshape(-1))
    pcm = np.concatenate(out) if out else np.zeros(0, dtype=np.int16)
    return (pcm[:limit].astype(np.float32) / 32768.0)


def _lang(v: str | None) -> str | None:
    """'ru-RU' -> 'ru'; Whisper takes the two-letter code."""
    if not v:
        return None
    return str(v).strip().split("-")[0].split("_")[0].lower()[:3] or None
