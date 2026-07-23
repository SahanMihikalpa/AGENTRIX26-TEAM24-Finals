# `infrastructure/config.py` — Settings (single config source)

**Layer:** infrastructure (cross-cutting) · **Stage:** 0

## 🎯 කාර්යය
System එකේ **හැම tunable එකක්ම** එකම තැනක. `.env` + environment variables වලින් read කරන, validated
`Settings` object එකක් (Pydantic Settings). **Environment එක read කරන එකම තැන මේකයි** — scatter වුණු
`os.getenv()` calls නෑ.

## 🏛️ Architecture එකේ තැන
`infrastructure` එකේ ඉන්නේ config එක cross-cutting concern එකක් නිසා. **වැදගත්:** `domain` සහ
`application` layers මේක **direct import කරන්නේ නෑ** — concrete values `api` layer එකේදී inject වෙනවා
(dependency rule එක ආරක්ෂා කරන්න).

## 🔍 Code Walkthrough
`Settings(BaseSettings)` — groups:
- **App/Server:** `app_env`, `log_level`, `host`, `port`, `cors_origins`.
- **Data stores:** `sqlite_path`, `chroma_dir`, `source_pool_dir`.
- **LLM:** `gemini_api_key`, `groq_api_key`, `llm_model` (= `gemini-2.5-flash`),
  `llm_fallback_model` (= `llama-3.1-8b-instant`).
- **Web:** `tavily_api_key`, `web_allowlist` (= `gov.lk`).
- **Embeddings:** `embedding_model` (= `BAAI/bge-base-en-v1.5`).
- **Guardrails:** `confidence_threshold` (**τ=0.6, AD-8**), `max_acquisition_loops` (**N=2, AD-2**).
- **Gateway:** `llm_rate_limit_rpm` (**15, AD-10**).

Comma-separated values (`cors_origins`, `web_allowlist`) parse කරන `@property` දෙකක්. `get_settings()`
`@lru_cache` — environment එක **එක පාරයි** read කරන්නේ.

## ⚠️ ගොටුවෙන්න පුළුවන් තැන්
- τ, N, rpm වගේ **architectural constants හැම එකක්ම මෙතන** — code එකේ magic numbers නෑ. Tune කරන්නේ
  මෙතන හෝ `.env` එකේ.
- `llm_model` **`gemini-2.5-flash`** විය යුතුයි — `gemini-2.0-flash` මේ project එකේ free-tier `limit: 0`
  (429 error). `.env` එකේ override එකකින් back to 2.0 නොකරන්න.
