"""Text brain protocol + mock twin + optional live providers (complete + stream)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Iterator, Optional, Protocol, runtime_checkable


@runtime_checkable
class TextBrain(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str: ...


def stream_text(brain: Any, system: str, user: str) -> Iterator[str]:
    """Yield text deltas from a brain (uses stream() if present, else complete)."""
    stream_fn = getattr(brain, "stream", None)
    if callable(stream_fn):
        yield from stream_fn(system, user)
        return
    text = brain.complete(system, user)
    if text:
        yield text


def chunk_text(text: str, size: int = 14) -> Iterator[str]:
    """Split text into chunks (mock/demo streaming)."""
    if not text:
        return
    for i in range(0, len(text), size):
        yield text[i : i + size]


class MockBrain:
    """Deterministic offline brain — echoes intent, no network."""

    name = "mock"

    def complete(self, system: str, user: str) -> str:
        line = user.strip().splitlines()[0] if user.strip() else "..."
        if len(line) > 200:
            line = line[:200] + "…"
        return (
            f"[mock director] Noted. Phase discipline holds. "
            f"Regarding: {line} — protect theme, cut on emotion, "
            f"justify with canon before novelty."
        )

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield from chunk_text(self.complete(system, user), size=16)


class AnthropicBrain:
    name = "anthropic"

    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or os.environ.get(
            "DIRECTOR_BOT_TEXT_MODEL", "claude-sonnet-4-20250514"
        )

    def complete(self, system: str, user: str) -> str:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed; pip install anthropic"
            ) from exc
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = []
        for block in msg.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip() or ""

    def stream(self, system: str, user: str) -> Iterator[str]:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed; pip install anthropic"
            ) from exc
        client = anthropic.Anthropic()
        with client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for text in stream.text_stream:
                if text:
                    yield text


class OpenAICompatBrain:
    """OpenAI-compatible Chat Completions (OpenAI or xAI Grok)."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        base_url: str,
        model: str,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, system: str, user: str) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.name} HTTP {exc.code}: {err[:400]}") from exc
        choices = payload.get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or "").strip()

    def stream(self, system: str, user: str) -> Iterator[str]:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6,
            "stream": True,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                while True:
                    raw = resp.readline()
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield str(content)
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{self.name} HTTP {exc.code}: {err[:400]}") from exc


def _raw_brain(provider: Optional[str] = None) -> TextBrain:
    from director_bot import config

    name = (provider or config.default_provider()).lower()
    if name == "mock":
        return MockBrain()
    if name == "anthropic":
        if not (os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            return MockBrain()
        return AnthropicBrain()
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            return MockBrain()
        model = os.environ.get("DIRECTOR_BOT_TEXT_MODEL", "gpt-4o-mini")
        return OpenAICompatBrain(
            name="openai",
            api_key=key,
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=model,
        )
    if name == "xai":
        key = os.environ.get("XAI_API_KEY", "")
        if not key:
            return MockBrain()
        model = os.environ.get("DIRECTOR_BOT_TEXT_MODEL", "grok-3")
        return OpenAICompatBrain(
            name="xai",
            api_key=key,
            base_url=os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1"),
            model=model,
        )
    return MockBrain()


def get_brain(
    provider: Optional[str] = None,
    *,
    trace: bool = True,
    project_id: Optional[int] = None,
) -> TextBrain:
    """Return a brain. By default wraps with TracingBrain so every complete()
    is visible in the dashboard Model View /api/brain/traces.
    """
    raw = _raw_brain(provider)
    if not trace:
        return raw
    from director_bot.soul.trace import TracingBrain

    return TracingBrain(raw, project_id=project_id)


def score_candidates_with_brain(
    brain: TextBrain,
    situation: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Optional LLM re-score of candidate actions. Falls back to input on error.

    Expects each candidate dict: {id, action, style_source}.
    Returns list of {id, scores: {criteria...}, notes}.
    """
    if brain.name == "mock" or not candidates:
        return []
    from director_bot.soul.trace import SCORE_SYSTEM, build_score_payload

    payload = build_score_payload(situation, candidates)
    system = SCORE_SYSTEM
    user = json.dumps(payload, indent=2)
    # Prefer traced call with kind=score when wrapped
    call_brain = brain
    if hasattr(brain, "with_context"):
        call_brain = brain.with_context(kind="score")  # type: ignore[assignment]
    try:
        raw = call_brain.complete(system, user)
        # extract JSON array if fenced
        text = raw.strip()
        if "```" in text:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                text = text[start:end]
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []
