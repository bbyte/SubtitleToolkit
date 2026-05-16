"""
Calibration worker thread for SubtitleToolkit.

Probes an AI model with progressively larger translation requests to find
the maximum reliable chunk size and concurrent-worker count.

Algorithm
---------
Phase 1 — Chunk size
    Sends translation batches of size 5, 10, 20, 30, 50, 75, 100.
    For each, the response is checked for completeness (≥ 90% of items
    returned).  Stops at the first failure; the last success is the
    recommended chunk size.

Phase 2 — Concurrency
    Fires 1 … 5 identical small requests simultaneously using a thread pool.
    Stops when a rate-limit error is detected; the last fully-successful
    concurrency level is the recommended worker count.

Results are written to QSettings via ``app.calibration.store``.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import QThread, Signal

# ── Constants ─────────────────────────────────────────────────────────────────

# Default base URLs for OpenAI-compatible providers that are NOT openai itself.
# The calibration worker uses these when no explicit base_url is supplied.
_PROVIDER_BASE_URLS: Dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "xai":        "https://api.x.ai/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "deepseek":   "https://api.deepseek.com",
    "kimi":       "https://api.moonshot.cn/v1",
    "moonshot":   "https://api.moonshot.cn/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai/",
    "zai":        "https://api.z.ai/api/paas/v4/",
    "local":      "http://localhost:1234/v1",
}

CHUNK_SIZES:   List[int] = [5, 10, 20, 30, 50, 75, 100]
WORKER_COUNTS: List[int] = [1, 2, 3, 4, 5]

# Total number of individual probes (used for progress bar range)
TOTAL_PROBES: int = len(CHUNK_SIZES) + len(WORKER_COUNTS)

_SYSTEM_PROMPT = (
    "You are a professional subtitle translator. "
    "Translate the provided English subtitles to Spanish. "
    "Return ONLY a JSON object with the same numeric string keys and "
    "Spanish-translated values. Do not add any explanation or extra text."
)

# 80 diverse English subtitle-like sentences used as calibration test data.
# Sentence length varies intentionally to mimic real subtitle files.
_TEST_SUBTITLES: List[str] = [
    "Hello.",
    "Wait.",
    "Stop right there.",
    "I can't believe it.",
    "What time is it?",
    "About three o'clock.",
    "Let's go outside.",
    "Did you hear that?",
    "Something's wrong.",
    "Everything is fine.",
    "Can you help me?",
    "I'll be right back.",
    "Don't worry about it.",
    "We should leave now.",
    "The meeting starts soon.",
    "Where did you go?",
    "I was at the store.",
    "Are you feeling better?",
    "Much better, thank you.",
    "Let me know if you need anything.",
    "The package arrived this morning.",
    "Did you open it yet?",
    "Not yet, I was waiting for you.",
    "We're running out of time.",
    "Just five more minutes.",
    "I promise I'll be quick.",
    "She looked surprised.",
    "He didn't say a word.",
    "They left without saying goodbye.",
    "It was a long journey.",
    "But we finally made it.",
    "Welcome to your new home.",
    "Thank you, I love it.",
    "The view is incredible.",
    "You can see the whole city.",
    "I've never seen anything like it.",
    "Neither have I.",
    "This changes everything.",
    "Are you sure about that?",
    "Absolutely certain.",
    "Then we have no choice.",
    "What are you thinking?",
    "I'm thinking we should reconsider.",
    "It's not that simple.",
    "Nothing ever is.",
    "We need a plan.",
    "I already have one.",
    "Tell me.",
    "We wait until nightfall.",
    "And then?",
    "And then we move.",
    "That's it? That's the plan?",
    "Simple plans work best.",
    "I suppose you're right.",
    "I usually am.",
    "Don't push your luck.",
    "Fair enough.",
    "The signal is weak here.",
    "We'll lose contact soon.",
    "Then say what you need to say.",
    "I'll make this quick.",
    "Stay safe out there.",
    "You too.",
    "See you on the other side.",
    "Let's hope so.",
    "Ready when you are.",
    "Three, two, one.",
    "Now.",
    "Run!",
    "Don't stop.",
    "We're almost there.",
    "Just a little further.",
    "I can see the exit.",
    "Keep moving.",
    "We made it.",
    "I knew we would.",
    "I never doubted it.",
    "Yes you did.",
    "Okay, maybe a little.",
    "A little is fine.",
    "What do we do now?",
    "We rest. Then we keep going.",
]


# ── Worker ────────────────────────────────────────────────────────────────────

class CalibrationWorker(QThread):
    """
    Background QThread that probes an AI model and emits progress signals.

    Signals
    -------
    phase_started(phase_id, description)
        Emitted at the start of each calibration phase.
    probe_done(probe_id, result_dict)
        Emitted after each individual probe completes.
    log_message(level, text)
        Human-readable progress lines: 'info' | 'warning' | 'error'.
    progress(n)
        Number of completed probes (use with TOTAL_PROBES for a progress bar).
    finished(results_dict)
        Emitted when calibration completes successfully.
        ``results_dict`` keys: max_chunk_size, max_workers, latency_avg_ms.
    error(message)
        Emitted on a fatal error that prevents calibration from completing.
    """

    phase_started = Signal(str, str)   # phase_id, description
    probe_done    = Signal(str, dict)  # probe_id, result dict
    log_message   = Signal(str, str)   # level, text
    progress      = Signal(int)        # completed probe count
    finished      = Signal(dict)       # final results
    error         = Signal(str)        # fatal error message
    raw_log       = Signal(str, str)   # label, content (for debug tab)

    def __init__(
        self,
        provider:  str,
        model:     str,
        api_key:   str,
        base_url:  str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.provider  = provider.lower().strip()
        self.model     = model.strip()
        self.api_key   = api_key.strip()
        # Use the supplied base_url, or fall back to the known default for this provider
        self.base_url  = base_url.strip() or _PROVIDER_BASE_URLS.get(self.provider, "")
        self._stop     = False
        self._done     = 0   # completed probes

    def stop(self) -> None:
        """Request graceful stop after the current probe finishes."""
        self._stop = True

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:
            self.error.emit(str(exc))

    def _run(self) -> None:
        # ── Phase 1: chunk size ───────────────────────────────────────────────
        self.phase_started.emit("chunk", "Phase 1 — Testing chunk sizes")
        self.log_message.emit("info", "Testing how many subtitles can be translated per request…")

        max_chunk  = CHUNK_SIZES[0]
        latencies: List[float] = []

        for size in CHUNK_SIZES:
            if self._stop:
                return
            result = self._probe_chunk(size)
            self._done += 1
            self.progress.emit(self._done)
            self.probe_done.emit(f"chunk_{size}", result)

            if result["success"]:
                max_chunk = size
                latencies.append(result["latency_ms"])
                self.log_message.emit(
                    "info",
                    f"✓  Chunk {size:>3}  — OK  ({result['latency_ms']:.0f} ms)",
                )
            else:
                reason = result["reason"]
                # Auth errors are fatal — abort immediately so we don't save bad defaults
                if "authentication" in reason or "auth" in reason:
                    self.error.emit(
                        f"Authentication failed (401): {reason}\n\n"
                        "Check that your API key is correct for this provider."
                    )
                    return
                self.log_message.emit(
                    "warning",
                    f"✗  Chunk {size:>3}  — {reason}  (stopping here)",
                )
                # Skip remaining larger sizes
                self._done += len(CHUNK_SIZES) - CHUNK_SIZES.index(size) - 1
                self.progress.emit(self._done)
                break

            time.sleep(0.4)   # brief pause between probes

        if not latencies:
            self.log_message.emit(
                "warning",
                "⚠  All chunk probes failed — model may wrap JSON in code fences "
                "(fixed automatically) or API key / endpoint may be invalid. "
                "Re-run calibration; if it still fails check the API key.",
            )

        # ── Phase 2: concurrent workers ───────────────────────────────────────
        self.phase_started.emit("workers", "Phase 2 — Testing concurrent workers")
        self.log_message.emit("info", "Testing how many parallel requests are allowed…")

        max_workers = 1
        test_chunk  = max(5, max_chunk // 2)   # conservative chunk for concurrency test

        for n in WORKER_COUNTS:
            if self._stop:
                return
            ok, reason = self._probe_workers(n, test_chunk)
            self._done += 1
            self.progress.emit(self._done)
            self.probe_done.emit(f"workers_{n}", {"success": ok, "workers": n, "reason": reason})

            if ok:
                max_workers = n
                self.log_message.emit("info", f"✓  Workers {n}  — OK")
            else:
                if "authentication" in reason or "auth" in reason:
                    self.error.emit(
                        f"Authentication failed (401): {reason}\n\n"
                        "Check that your API key is correct for this provider."
                    )
                    return
                self.log_message.emit("warning", f"✗  Workers {n}  — {reason}  (stopping here)")
                self._done += len(WORKER_COUNTS) - WORKER_COUNTS.index(n) - 1
                self.progress.emit(self._done)
                break

            time.sleep(1.0)   # rate-limit window between worker probes

        # ── Save & report ─────────────────────────────────────────────────────
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        results = {
            "max_chunk_size": max_chunk,
            "max_workers":    max_workers,
            "latency_avg_ms": avg_latency,
        }

        from app.calibration.store import save_calibration
        save_calibration(self.model, results)

        self.finished.emit(results)

    # ── Probe helpers ─────────────────────────────────────────────────────────

    def _probe_chunk(self, chunk_size: int) -> Dict[str, Any]:
        """Send one translation request of *chunk_size* items; return result dict."""
        n       = min(chunk_size, len(_TEST_SUBTITLES))
        payload = {str(i + 1): _TEST_SUBTITLES[i] for i in range(n)}
        t0      = time.time()

        try:
            raw = self._call_api(payload)
        except Exception as exc:
            reason = self._classify_error(exc)
            self.raw_log.emit(
                f"chunk_{chunk_size} — EXCEPTION",
                f"Error: {exc}",
            )
            return {
                "success":    False,
                "reason":     reason,
                "latency_ms": (time.time() - t0) * 1000,
            }

        latency_ms = (time.time() - t0) * 1000

        # Emit raw response before any processing
        preview = raw[:800] + ("…" if len(raw) > 800 else "")
        self.raw_log.emit(
            f"chunk_{chunk_size} — raw response ({len(raw)} chars, {latency_ms:.0f} ms)",
            preview,
        )

        stripped = self._strip_markdown_fence(raw)
        if stripped != raw.strip():
            self.raw_log.emit(
                f"chunk_{chunk_size} — after fence strip ({len(stripped)} chars)",
                stripped[:400] + ("…" if len(stripped) > 400 else ""),
            )
        raw = stripped

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.raw_log.emit(
                f"chunk_{chunk_size} — JSON parse ERROR",
                f"{exc}\n\nFirst 200 chars of input:\n{raw[:200]}",
            )
            return {"success": False, "reason": f"invalid JSON: {str(exc)[:60]}", "latency_ms": latency_ms}

        if not isinstance(parsed, dict):
            self.raw_log.emit(
                f"chunk_{chunk_size} — wrong type",
                f"Expected dict, got {type(parsed).__name__}: {str(parsed)[:200]}",
            )
            return {"success": False, "reason": "response is not a JSON object", "latency_ms": latency_ms}

        expected = len(payload)
        actual   = len(parsed)
        self.raw_log.emit(
            f"chunk_{chunk_size} — parsed OK",
            f"Keys returned: {actual}/{expected}  |  Keys: {list(parsed.keys())[:10]}",
        )
        if actual < expected * 0.9:
            return {
                "success":    False,
                "reason":     f"truncated — got {actual}/{expected} items",
                "latency_ms": latency_ms,
            }

        return {"success": True, "reason": "ok", "latency_ms": latency_ms}

    def _probe_workers(self, n_workers: int, chunk_size: int) -> Tuple[bool, str]:
        """
        Launch *n_workers* concurrent probes.  Return (all_ok, reason_string).
        """
        results: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(self._probe_chunk, chunk_size) for _ in range(n_workers)]
            for fut in as_completed(futures):
                results.append(fut.result())

        rate_limits = [r for r in results if "rate" in r.get("reason", "").lower()]
        if rate_limits:
            return False, "rate limit"

        failures = [r for r in results if not r["success"]]
        if failures:
            return False, failures[0].get("reason", "probe failed")

        return True, "ok"

    # ── API layer ─────────────────────────────────────────────────────────────

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        """Strip ```json … ``` or ``` … ``` code fences that some models add."""
        text = text.strip()
        text = re.sub(r'^```[a-zA-Z]*\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return text.strip()

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        msg = str(exc).lower()
        if "rate" in msg or "429" in msg:
            return "rate limit"
        if "timeout" in msg:
            return "timeout"
        if "auth" in msg or "401" in msg or "403" in msg:
            return "authentication error"
        if "context" in msg or "length" in msg or "token" in msg:
            return "context length exceeded"
        return str(exc)[:80]

    def _call_api(self, payload: Dict[str, str]) -> str:
        """Dispatch a translation request to the appropriate SDK."""
        user_msg = (
            "Translate these English subtitles to Spanish. "
            "Return only a JSON object with the same keys.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )
        if self.provider == "claude":
            return self._call_anthropic(user_msg)
        else:
            return self._call_openai_compat(user_msg)

    def _call_openai_compat(self, user_msg: str) -> str:
        import openai

        kwargs: Dict[str, Any] = {"api_key": self.api_key, "timeout": 90.0}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        client = openai.OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, user_msg: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key, timeout=90.0)
        resp = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text if resp.content else ""
