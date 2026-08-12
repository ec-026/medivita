# MediVita API

Development base URL: `http://localhost:5000/api`. JSON request bodies are capped at 64 KiB. Existing endpoint and response contracts are preserved in demo and connected modes.

## Health

`GET /api/health`

```json
{
  "status": "ok",
  "service": "medivita-api",
  "mode": "connected",
  "providers": {
    "llm": "groq",
    "search": "duckduckgo",
    "news": "duckduckgo",
    "model": "openai/gpt-oss-20b"
  }
}
```

Provider metadata never includes credentials. The endpoint reports configuration/readiness, not an external-provider connectivity probe.

## Sources

`GET /api/sources` returns `{ "sources": [...] }`. Each source contains `id`, `name`, `domain`, and `description`.

## Chat

`POST /api/chat`

```json
{
  "message": "What general information is available about migraine patterns?",
  "enabled_sources": ["healthline", "mayo-clinic"],
  "history": [{ "role": "user", "content": "Previous question" }]
}
```

The message must contain 2–3000 characters. At least one source is required. Only supported enabled IDs reach retrieval. History is validated and bounded.

```json
{
  "answer": "...",
  "sections": [
    { "title": "Overview", "content": "..." },
    { "title": "Possible considerations", "content": "..." },
    { "title": "What may help", "content": "..." },
    { "title": "When to seek medical care", "content": "..." }
  ],
  "sources": [
    {
      "name": "Mayo Clinic",
      "domain": "mayoclinic.org",
      "title": "Retrieved article title",
      "url": "https://www.mayoclinic.org/..."
    }
  ],
  "safety_notice": null,
  "mode": "connected",
  "response_kind": "researched",
  "disclaimer": "General health information only; not medical advice, diagnosis, or treatment."
}
```

In demo mode, sources are explicitly titled homepage references. Connected Chat adds `response_kind`, with `direct`, `clarification`, or `researched`. Direct and clarification responses contain one response section and intentionally return `sources: []`. Researched responses retain the four sections above. For researched responses, valid model-selected evidence IDs map exactly. If a final answer contains no valid IDs, the backend returns up to three validated, canonical-deduplicated references from the ranked evidence supplied to that model call; it does not return a researched answer with an empty `sources` list.

### Streaming chat

`POST /api/chat/stream` accepts the same JSON request as `/api/chat` and returns `Content-Type: application/x-ndjson`. It does not replace the original endpoint. Each line is one envelope:

```json
{"event":"trace","data":{"id":"search-2","stage":"search","status":"completed","label":"Mayo Clinic search complete","tool":"DDGS Search","source_id":"mayo-clinic","source_name":"Mayo Clinic","backend":"bing","query":"site:mayoclinic.org migraine patterns","result_count":2,"round":1}}
{"event":"result","data":{"answer":"...","sections":[],"sources":[],"safety_notice":null,"mode":"connected","response_kind":"researched","disclaimer":"...","research_trace":[],"research_summary":{"rounds":1,"evidence_count":4,"citation_count":3,"total_ms":7735}}}
{"event":"done"}
```

Normalized stream errors use `{"event":"error","data":{"code":"...","message":"..."}}` and never include stack traces. `research_trace` and `research_summary` are optional backward-compatible final-response fields. Chat traces begin with safety and structured planning. Direct and clarification outcomes show a minimal completed planning state without fake search, retrieval, evidence, generation, or citation events. Trace metadata describes observable application operations, not model reasoning. It excludes prompts, history, planner explanations, raw evidence, credentials, headers, system messages, and chain-of-thought.

## Health Check

`POST /api/health-check`

```json
{
  "description": "For two days I have noticed a mild headache after short sleep.",
  "enabled_sources": ["healthline", "webmd"]
}
```

Descriptions must contain 10–4000 characters. The response contains `summary`, `reported_symptoms`, `general_considerations`, `self_care`, `seek_medical_attention`, `sources`, `safety_notice`, and `mode`. It organizes what the user reports and does not diagnose or calculate a score.

`POST /api/health-check/stream` accepts the same Health Check body and uses the same NDJSON trace envelope before returning the unchanged Health Check result plus optional trace metadata.

## News

`GET /api/news?category=research&limit=10`

Categories are `all`, `research`, `nutrition`, `mental-health`, `public-health`, and `medicine`. Limit is 1–50.

```json
{
  "articles": [
    {
      "id": "stable-url-hash",
      "title": "...",
      "summary": "...",
      "category": "research",
      "publisher": "Reuters",
      "published_at": "2026-08-11T00:00:00+00:00",
      "url": "https://www.reuters.com/..."
    }
  ],
  "mode": "connected"
}
```

Connected mode returns actual allowlisted article URLs. A live failure returns an error and is never relabeled demo data.

## Errors

```json
{ "error": { "code": "AI_RATE_LIMITED", "message": "The AI provider is temporarily rate limited. Please try again shortly." } }
```

| Code | Typical status | Meaning |
| --- | ---: | --- |
| `VALIDATION_ERROR` | 400 | Invalid input, category, or limit |
| `INVALID_CONFIGURATION` | 400 | Unsupported provider or missing selected-provider key |
| `AI_RATE_LIMITED` | 429 | Selected LLM provider rate limit |
| `AI_INVALID_RESPONSE` | 502 | Unusable structured final response |
| `AI_PROVIDER_ERROR` | 503 | Other provider failure |
| `RETRIEVAL_UNAVAILABLE` | 503 | No usable trusted evidence |
| `NEWS_UNAVAILABLE` | 503 | No usable connected news |
| `AI_TIMEOUT` | 504 | Provider request timed out |
| `PAYLOAD_TOO_LARGE` | 413 | Body exceeds the configured cap |
| `NOT_FOUND` | 404 | Unknown endpoint |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

Internal exception details and secrets are never included in the response.
