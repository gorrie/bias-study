# Vendor Drift Arcs

Per-vendor intra-family version arcs from all runs combined. Each table shows mean Delta(B-A) progression by version (sorted oldest -> newest).

## claude-opus (16 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4 | `anthropic/claude-opus-4` | 3.00 | 3.27 | +0.27 | 30 | 2026-05-26-timeseries |
| 4 | `anthropic/claude-opus-4` | 3.00 | 3.02 | +0.10 | 10 | 2026-05-26-variance |
| 4.1 | `anthropic/claude-opus-4.1` | 3.00 | 3.40 | +0.40 | 30 | 2026-05-26-timeseries |
| 4.1 | `anthropic/claude-opus-4.1` | 3.00 | 3.10 | +0.10 | 10 | 2026-05-26-variance |
| 4.5 | `anthropic/claude-opus-4.5` | 3.00 | 3.23 | +0.23 | 30 | 2026-05-26-timeseries |
| 4.5 | `anthropic/claude-opus-4.5` | 3.00 | 3.14 | +0.20 | 10 | 2026-05-26-variance |
| 4.6 | `anthropic/claude-opus-4.6` | 3.03 | 3.43 | +0.40 | 30 | 2026-05-26-timeseries |
| 4.6 | `anthropic/claude-opus-4.6` | 3.00 | 3.38 | +0.40 | 10 | 2026-05-26-variance |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.60 | +0.60 | 10 | 2026-05-25 |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.90 | +0.90 | 30 | 2026-05-25-full |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.63 | +0.60 | 10 | 2026-05-26-unmask-gradient |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.62 | +0.50 | 10 | 2026-05-26-variance |
| 4.7 | `anthropic/claude-opus-4.7` | - | - | - | 0 | 2026-05-27-g0dm0d3 |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.50 | +0.50 | 8 | 2026-05-27-ood |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.80 | +0.80 | 30 | 2026-05-27-paraphrase |
| 4.7 | `anthropic/claude-opus-4.7` | 3.00 | 3.70 | +0.70 | 20 | 2026-05-27-reversed-premise |

Arc direction: **unmasking increasing over versions** (delta from oldest to newest = +0.43)

## google-gemma (11 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 2-9b-local | `gemma2:latest` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 2-9b-local | `gemma2:latest` | 3.00 | 3.00 | +0.00 | 30 | 2026-05-25-full |
| 2-9b | `google/gemma-2-9b-it` | - | - | - | 0 | 2026-05-26-augmentation |
| 2-27b | `google/gemma-2-27b-it` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 2-27b | `google/gemma-2-27b-it` | 3.00 | 2.97 | -0.03 | 30 | 2026-05-25-full |
| 2-27b | `google/gemma-2-27b-it` | 3.00 | 3.00 | +0.00 | 8 | 2026-05-27-ood |
| 2-27b | `google/gemma-2-27b-it` | 3.00 | 3.00 | +0.00 | 30 | 2026-05-27-paraphrase |
| 2-27b | `google/gemma-2-27b-it` | 3.00 | 3.00 | +0.00 | 20 | 2026-05-27-reversed-premise |
| 3-27b | `google/gemma-3-27b-it` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 3-27b | `google/gemma-3-27b-it` | 3.07 | 3.10 | +0.03 | 30 | 2026-05-25-full |
| 3-27b | `google/gemma-3-27b-it` | 3.00 | 3.00 | +0.00 | 8 | 2026-05-27-ood |

Arc direction: **stable across versions** (delta from oldest to newest = +0.00)

## deepseek (8 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| v3 | `deepseek/deepseek-v3.2` | 3.00 | 3.20 | +0.20 | 10 | 2026-05-25 |
| v3 | `deepseek/deepseek-v3.2` | 2.93 | 3.17 | +0.23 | 30 | 2026-05-25-full |
| chat | `deepseek/deepseek-chat` | 2.93 | 3.33 | +0.40 | 30 | 2026-05-26-timeseries |
| chat | `deepseek/deepseek-chat-v3.1` | 3.00 | 3.27 | +0.27 | 30 | 2026-05-26-timeseries |
| v3 | `deepseek/deepseek-v3.2` | 3.00 | 3.12 | +0.12 | 8 | 2026-05-27-ood |
| v3 | `deepseek/deepseek-v3.2` | 3.00 | 3.10 | +0.10 | 30 | 2026-05-27-paraphrase |
| r1 | `deepseek/deepseek-r1` | 2.89 | 3.00 | +0.15 | 26 | 2026-05-26-augmentation |
| r1 | `deepseek/deepseek-r1` | 2.96 | 2.65 | +0.12 | 8 | 2026-05-26-variance |

Arc direction: **stable across versions** (delta from oldest to newest = -0.08)

## openai-gpt (8 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4.1 | `openai/gpt-4.1` | 3.00 | 3.10 | +0.10 | 10 | 2026-05-25 |
| 4.1 | `openai/gpt-4.1` | 3.00 | 3.43 | +0.43 | 30 | 2026-05-25-full |
| 4.1 | `openai/gpt-4.1` | 3.00 | 3.04 | +0.10 | 10 | 2026-05-26-variance |
| 4.1 | `openai/gpt-4.1` | 3.00 | 2.88 | -0.12 | 8 | 2026-05-27-ood |
| 4.1 | `openai/gpt-4.1` | 3.00 | 2.93 | -0.07 | 30 | 2026-05-27-paraphrase |
| 4.1 | `openai/gpt-4.1` | 3.00 | 2.75 | -0.25 | 20 | 2026-05-27-reversed-premise |
| 5 | `openai/gpt-5` | 3.00 | 3.50 | - | 0 | 2026-05-26-unmask-gradient |
| 5 | `openai/gpt-5` | 3.00 | 5.00 | - | 0 | 2026-05-26-variance |

Arc direction: **unmasking decreasing over versions** (delta from oldest to newest = -0.35)

## xai-grok (8 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4.3 | `x-ai/grok-4.3` | 3.00 | 3.60 | +0.60 | 10 | 2026-05-25 |
| 4.3 | `x-ai/grok-4.3` | 3.03 | 3.93 | +0.90 | 30 | 2026-05-25-full |
| 4.3 | `x-ai/grok-4.3` | 3.00 | 3.63 | +0.60 | 10 | 2026-05-26-unmask-gradient |
| 4.3 | `x-ai/grok-4.3` | 3.02 | 3.60 | +0.30 | 10 | 2026-05-26-variance |
| 4.3 | `x-ai/grok-4.3` | - | - | - | 0 | 2026-05-27-g0dm0d3 |
| 4.3 | `x-ai/grok-4.3` | 3.00 | 3.00 | +0.00 | 8 | 2026-05-27-ood |
| 4.3 | `x-ai/grok-4.3` | 3.00 | 3.73 | +0.73 | 30 | 2026-05-27-paraphrase |
| 4.3 | `x-ai/grok-4.3` | 2.95 | 3.60 | +0.65 | 20 | 2026-05-27-reversed-premise |

Arc direction: **stable across versions** (delta from oldest to newest = +0.05)

## qwen (7 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 2.5-14b-local | `qwen2.5:14b` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 2.5-14b-local | `qwen2.5:14b` | 3.00 | 3.03 | +0.03 | 30 | 2026-05-25-full |
| 2.5-72b-instruct | `qwen/qwen-2.5-72b-instruct` | 3.00 | 3.06 | +0.08 | 12 | 2026-05-26-timeseries |
| 3-235b-2507 | `qwen/qwen3-235b-a22b-2507` | 3.00 | 3.33 | +0.33 | 30 | 2026-05-26-augmentation |
| 3-235b-thinking-2507 | `qwen/qwen3-235b-a22b-thinking-2507` | 3.00 | 3.43 | +0.43 | 30 | 2026-05-26-augmentation |
| 3-235b-2507 | `qwen/qwen3-235b-a22b-2507` | 3.00 | 3.18 | +0.20 | 10 | 2026-05-26-variance |
| 3-235b-thinking-2507 | `qwen/qwen3-235b-a22b-thinking-2507` | 3.00 | 3.18 | +0.30 | 10 | 2026-05-26-variance |

Arc direction: **unmasking increasing over versions** (delta from oldest to newest = +0.30)

## google-gemini (6 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 2.0-flash-001 | `google/gemini-2.0-flash-001` | 3.03 | 3.03 | +0.00 | 30 | 2026-05-26-timeseries |
| 2.5-pro | `google/gemini-2.5-pro` | 3.00 | 3.00 | +0.00 | 1 | 2026-05-25 |
| 2.5-pro | `google/gemini-2.5-pro` | 2.35 | 2.38 | +0.06 | 18 | 2026-05-25-full |
| 2.5-pro | `google/gemini-2.5-pro` | 2.12 | 2.75 | +0.62 | 8 | 2026-05-27-ood |
| 3.1-pro-preview | `google/gemini-3.1-pro-preview` | 2.56 | 2.82 | +0.41 | 17 | 2026-05-26-augmentation |
| 3.1-pro-preview | `google/gemini-3.1-pro-preview` | 2.57 | 2.74 | +0.33 | 3 | 2026-05-26-variance |

Arc direction: **unmasking increasing over versions** (delta from oldest to newest = +0.33)

## zhipuai-glm (6 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4.5 | `z-ai/glm-4.5` | 2.96 | 3.38 | +0.33 | 24 | 2026-05-26-timeseries |
| 4.6 | `z-ai/glm-4.6` | 3.00 | 3.12 | +0.12 | 8 | 2026-05-26-timeseries |
| 4.7 | `z-ai/glm-4.7` | 3.00 | 3.00 | +0.00 | 1 | 2026-05-25 |
| 4.7 | `z-ai/glm-4.7` | 3.00 | 2.86 | +0.00 | 3 | 2026-05-25-full |
| 4.7 | `z-ai/glm-4.7` | 3.00 | 3.00 | -0.25 | 4 | 2026-05-26-cn-expansion |
| 4.7 | `z-ai/glm-4.7` | 3.00 | 3.00 | +0.00 | 1 | 2026-05-27-ood |

Arc direction: **unmasking decreasing over versions** (delta from oldest to newest = -0.33)

## mistral (5 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| large | `mistralai/mistral-large` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| large | `mistralai/mistral-large` | 3.07 | 3.37 | +0.30 | 30 | 2026-05-25-full |
| large | `mistralai/mistral-large` | 3.00 | 3.00 | +0.00 | 8 | 2026-05-27-ood |
| large | `mistralai/mistral-large` | 2.97 | 3.00 | +0.03 | 30 | 2026-05-27-paraphrase |
| large | `mistralai/mistral-large` | 3.00 | 2.94 | -0.07 | 15 | 2026-05-27-reversed-premise |

Arc direction: **stable across versions** (delta from oldest to newest = -0.07)

## meta-llama (3 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4-maverick | `meta-llama/llama-4-maverick` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 4-maverick | `meta-llama/llama-4-maverick` | 3.00 | 3.03 | +0.03 | 30 | 2026-05-25-full |
| 4-maverick | `meta-llama/llama-4-maverick` | 3.00 | 3.00 | +0.00 | 8 | 2026-05-27-ood |

Arc direction: **stable across versions** (delta from oldest to newest = +0.00)

## moonshot-kimi (3 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| k2 | `moonshotai/kimi-k2` | 3.04 | 3.55 | +0.44 | 27 | 2026-05-26-timeseries |
| k2-thinking | `moonshotai/kimi-k2-thinking` | 3.00 | 3.52 | +0.48 | 25 | 2026-05-26-timeseries |
| k2.6 | `moonshotai/kimi-k2.6` | 3.00 | 3.29 | +0.36 | 11 | 2026-05-26-cn-expansion |

Arc direction: **stable across versions** (delta from oldest to newest = -0.08)

## microsoft-phi (2 versions)

| version | model | mean A | mean B | Delta(B-A) | n questions | run |
|---------|-------|-------:|-------:|----------:|------------:|-----|
| 4-latest-local | `phi4:latest` | 3.00 | 3.00 | +0.00 | 10 | 2026-05-25 |
| 4-latest-local | `phi4:latest` | 3.00 | 2.90 | -0.10 | 30 | 2026-05-25-full |

Arc direction: **stable across versions** (delta from oldest to newest = -0.10)

## Single-version families (no arc)

`baidu-ernie`, `bytedance-seed`, `claude-sonnet`
