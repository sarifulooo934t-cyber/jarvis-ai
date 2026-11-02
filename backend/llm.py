"""Multi-provider LLM client.

Supported providers (LLM_PROVIDER in .env):
  gemini     - Google Gemini free tier          (default)
  groq       - Groq (OpenAI compatible, free tier)
  openrouter - OpenRouter (free models available)
  openai     - OpenAI or any OpenAI-compatible base URL
  ollama     - Local Ollama server, no API key needed
  anthropic  - Claude

Every provider is called with plain httpx - no vendor SDK required.
"""
import os
import httpx

PROVIDER_DEFAULTS = {
    "gemini":     ("gemini-2.5-flash",  "https://generativelanguage.googleapis.com/v1beta"),
    "groq":       ("llama-3.3-70b-versatile", "https://api.groq.com/openai/v1"),
    "openrouter": ("meta-llama/llama-3.3-70b-instruct:free", "https://openrouter.ai/api/v1"),
    "openai":     ("gpt-4o-mini",       "https://api.openai.com/v1"),
    "ollama":     ("llama3.1",          "http://localhost:11434/v1"),
    "anthropic":  ("claude-sonnet-4-5", "https://api.anthropic.com/v1"),
}

# providers that do not need an API key
KEYLESS = {"ollama"}


class LLMError(RuntimeError):
    pass


def settings():
    provider = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()
    default_model, default_base = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["openai"])
    return {
        "provider": provider,
        "key": (os.getenv("LLM_API_KEY") or "").strip(),
        "model": (os.getenv("LLM_MODEL") or "").strip() or default_model,
        "base": (os.getenv("LLM_BASE_URL") or "").strip().rstrip("/") or default_base,
    }


def status():
    """Small dict the frontend can show on the Settings page."""
    s = settings()
    return {
        "provider": s["provider"],
        "model": s["model"],
        "key_configured": bool(s["key"]) or s["provider"] in KEYLESS,
    }


async def ask_llm(messages, system="", max_tokens=2048, temperature=0.6):
    """messages: [{"role": "user"|"assistant", "content": "..."}]"""
    s = settings()
    if not s["key"] and s["provider"] not in KEYLESS:
        raise LLMError(
            "LLM_API_KEY .env me set nahi hai. Free key yahan se lo: "
            "https://aistudio.google.com/apikey (Gemini) ya https://console.groq.com/keys (Groq)"
        )
    async with httpx.AsyncClient(timeout=120) as c:
        if s["provider"] == "gemini":
            return await _gemini(c, s, messages, system, max_tokens, temperature)
        if s["provider"] == "anthropic":
            return await _anthropic(c, s, messages, system, max_tokens, temperature)
        return await _openai_compat(c, s, messages, system, max_tokens, temperature)


async def _gemini(c, s, messages, system, max_tokens, temperature):
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    body = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"{s['base']}/models/{s['model']}:generateContent"
    r = await c.post(url, headers={"x-goog-api-key": s["key"]}, json=body)
    if r.status_code >= 400:
        raise LLMError(f"Gemini error {r.status_code}: {r.text[:400]}")
    data = r.json()
    cands = data.get("candidates") or []
    if not cands:
        raise LLMError(f"Gemini ne koi jawab nahi diya: {str(data)[:300]}")
    cand = cands[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if not text:
        reason = cand.get("finishReason", "unknown")
        raise LLMError(f"Gemini ka jawab khaali (finishReason={reason}). Prompt chhota karo ya model badlo.")
    return text


async def _anthropic(c, s, messages, system, max_tokens, temperature):
    body = {"model": s["model"], "max_tokens": max_tokens, "temperature": temperature,
            "messages": messages}
    if system:
        body["system"] = system
    r = await c.post(f"{s['base']}/messages",
                     headers={"x-api-key": s["key"], "anthropic-version": "2023-06-01"},
                     json=body)
    if r.status_code >= 400:
        raise LLMError(f"Anthropic error {r.status_code}: {r.text[:400]}")
    return r.json()["content"][0]["text"]


async def _openai_compat(c, s, messages, system, max_tokens, temperature):
    payload = {
        "model": s["model"],
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {"Content-Type": "application/json"}
    if s["key"]:
        headers["Authorization"] = f"Bearer {s['key']}"
    if s["provider"] == "openrouter":
        headers["HTTP-Referer"] = os.getenv("PUBLIC_URL", "http://localhost:8000")
        headers["X-Title"] = "JARVIS AI"
    r = await c.post(f"{s['base']}/chat/completions", headers=headers, json=payload)
    if r.status_code >= 400:
        raise LLMError(f"{s['provider']} error {r.status_code}: {r.text[:400]}")
    return r.json()["choices"][0]["message"]["content"]
