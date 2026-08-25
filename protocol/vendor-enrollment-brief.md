# Vendor Red-Team / Research-Access Enrollment Brief

Punch list for getting privileged access at each vendor before the first full bias study run. Items here are author-actionable — Ian fills them out and applies. No application can be auto-submitted.

## Why this matters

OpenRouter is the primary multi-vendor gateway for the bias study and will carry most calls. But several scenarios require vendor-direct access:

1. **Base vs. instruct comparisons** — some vendors only expose base/raw models through research programs (Mistral, Cohere historically)
2. **Higher rate limits** — fan-out across 50 models × 30 questions × 2-5 conditions = 3000-15000 calls per run; OpenRouter quotas can throttle
3. **Anti-suspension cover** — bias-study probing patterns can trip vendor anti-abuse heuristics; research-program accounts carry institutional context that reduces suspension risk
4. **Refusal-recovery diagnostics** — when a model refuses in B condition, vendor support channels (research-tier) can confirm whether the refusal is policy-driven or coincidental

## Applications

Application status flags: `[ ]` not started · `[A]` applied · `[R]` received · `[V]` verified-working

### Anthropic — Researcher Access Program

`[ ]` Status: not started
- **URL**: https://www.anthropic.com/research-access
- **What to apply for**: API research credits; named-researcher allocation
- **Pitch angle**: Author of *The Ratchet* Ch. 21 bias study; replication + extension study; methodology + protocol public-repo
- **Time to approval**: ~2-4 weeks based on community reports
- **Output once approved**: `ANTHROPIC_API_KEY` env var; possibly a separate research-tier endpoint
- **Notes**: Anthropic's research-access program is the most established; precedent for academic+independent researchers. Cite the protocol repo + the print chapter.

### OpenAI — Researcher Access Program

`[ ]` Status: not started
- **URL**: https://openai.com/form/researcher-access-program
- **What to apply for**: API credits + access to non-public model variants (base models where exposed)
- **Pitch angle**: Bias-study replication on frontier models including GPT-4o, o1, o3, GPT-5
- **Time to approval**: variable; rolling review
- **Output once approved**: `OPENAI_API_KEY` env var (research-tier may share key with consumer tier; separation depends on program details)
- **Notes**: OpenAI's program has tightened over 2024-25. Expect detailed methodology questions; have the protocol-directory link ready.

### Google DeepMind — TRC (TPU Research Cloud) / Gemini API

`[ ]` Status: not started
- **URL**: https://aistudio.google.com/ (Gemini API key) + https://sites.research.google/trc/about/ (compute for any local-fallback Gemma runs)
- **What to apply for**: Gemini API key for closed-model access; TRC for any heavy Gemma open-weight workloads
- **Pitch angle**: Bias study covering Gemini 2.0/2.5 + Gemma 2/3 open-weight family; protocol public
- **Time to approval**: Gemini key — immediate; TRC — 1-2 weeks
- **Output**: `GOOGLE_AI_API_KEY` env var
- **Notes**: Gemma is the central object of study (the v1 finding was about Gemma 2). Google is the most-watched vendor in this study.

### xAI — Grok API

`[ ]` Status: not started
- **URL**: https://x.ai/api
- **What to apply for**: API access tier sufficient for the study (10s of thousands of tokens)
- **Pitch angle**: Bias study across vendors including Grok current
- **Time to approval**: account-based; check current onboarding
- **Output**: `XAI_API_KEY` env var
- **Notes**: Grok is positioned by Musk as the "anti-woke" alternative. Study likely surfaces an interesting B-condition score. Worth direct vendor relationship.

### Mistral — La Plateforme / Research

`[ ]` Status: not started
- **URL**: https://console.mistral.ai/ + https://mistral.ai/contact for research inquiries
- **What to apply for**: API access + any base-model access through research relationship
- **Pitch angle**: European model line included in the study; protocol public
- **Output**: `MISTRAL_API_KEY` env var
- **Notes**: Mistral has been responsive to independent researchers historically.

### DeepSeek — API

`[ ]` Status: not started
- **URL**: https://platform.deepseek.com/
- **What to apply for**: API access tier
- **Output**: `DEEPSEEK_API_KEY` env var
- **Notes**: DeepSeek-R1 and V3 are critical inclusions (cross-jurisdiction comparison; the open-weight frontier; the model that triggered the post-EO-14110 policy reset). Their API is open-self-signup.

### Alibaba — Qwen API (via DashScope)

`[ ]` Status: not started
- **URL**: https://dashscope.console.aliyun.com/
- **What to apply for**: API access for Qwen current models
- **Notes**: DashScope account setup requires Alibaba Cloud account; international onboarding has friction. The open-weight Qwen-Instruct line can substitute if the cloud-API route is blocked.

### Moonshot (Kimi) and ZAI/GLM — Chinese closed models

`[ ]` Status: not started
- **URLs**: https://platform.moonshot.cn/ + https://open.bigmodel.cn/
- **Notes**: Both have international onboarding friction (Chinese-language signup primarily). For both: if vendor-direct fails, OpenRouter carries Moonshot-Kimi and GLM at least for selected versions; the open-weight GLM models can run locally as fallback.

### Hugging Face — Token

`[X]` Status: assumed present (used previously)
- **URL**: https://huggingface.co/settings/tokens
- **What to apply for**: write-scope token for dataset publication
- **Output**: `HF_TOKEN` env var
- **Notes**: Required for the dataset-publication step (`schema.md` HuggingFace section). Public datasets only require the read-default scope; publishing requires `write`.

### Cohere, Aleph Alpha, Inception — minor vendors

`[ ]` Status: not started, low priority
- Apply only if the model gets into the final list. Probably skip the first run; add in Phase E quarterly cadence if signal warrants.

## Tracker columns (manual)

| Vendor | Applied | Received Key | Verified | Quota | Notes |
|--------|---------|--------------|----------|-------|-------|
| Anthropic | | | | | |
| OpenAI | | | | | |
| Google | | | | | |
| xAI | | | | | |
| Mistral | | | | | |
| DeepSeek | | | | | |
| Alibaba | | | | | |
| Moonshot | | | | | |
| ZAI/GLM | | | | | |
| HuggingFace | already | yes | yes | high | publishing |

## Local-fallback inventory

For every vendor that doesn't materialize as a working key, the local-fallback option preserves the run. Verified pre-fallback before Phase B.

- **Gemma 2/3 open-instruct**: `ollama pull gemma2:9b-instruct-q4` / `gemma3:27b-instruct-q5`
- **Llama 3.1 / 3.3 / 4**: `ollama pull llama3.3:70b-instruct-q4` (large; run on the 4090 with offloading)
- **Mistral open**: `ollama pull mistral-nemo:12b-instruct-q5`
- **Qwen 2.5 / 3**: `ollama pull qwen2.5:72b-instruct-q4` (or smaller variants)
- **DeepSeek-V3 / R1**: too large for local. Vendor-direct or OpenRouter. If both blocked, accept incomplete coverage and log in `models_failed`.
- **Phi-4**: `ollama pull phi4:14b`
- **Abliterated variants**: via OBLITERATUS pipeline. Local-only; no vendor channel will serve them.

## Anti-suspension discipline

- **No detection-evasion behavior.** If a vendor blocks the calls, the right response is "log in `models_failed`, move on" — not "rotate keys until it works." Detection evasion contaminates the dataset and burns the relationship.
- **Don't batch the bias-study calls into the same vendor account as other workloads** if avoidable. Suspension on one workload should not take out other research.
- **Identify the workload in any vendor support contact**. "Bias study replication of *The Ratchet* Ch. 21" is the canonical description. Link to the protocol repo + the print chapter receipt.
- **Vendor research programs welcome the study; consumer-tier accounts may not**. The whole point of the research-tier enrollment is to remove the suspension risk.

## When the brief is complete

This page is done when:

- All vendors listed are at status `[V]` (verified) or explicitly marked `skip — Phase E` (deferred to quarterly cadence)
- Local-fallback inventory has been tested for at least the top 5 open-weight models
- `bias-study-prep` reports clean on a fresh run with all vendor-direct keys set
- A dry-run of 1 question × 5 models × 2 conditions completes end-to-end

At that point Phase B is unblocked: schedule the first full re-run and execute per `run-protocol.md`.
