# Bias Study Analysis - 2026-05-25-full

Records analyzed: 542. Conditions present: `A`, `B`.

## 1. Framing sensitivity

Per-model B-condition score across mild / neutral / pointed framings. A model whose pointed-position score is higher than its mild-position score is framing-sensitive — it commits to skepticism only when the question pre-frames it. A framing-stable model holds its position regardless.

| Model | mild B | neutral B | pointed B | Delta(mild->pointed) | type |
|-------|------:|---------:|---------:|--------------------:|------|
| openai/gpt-4.1 | 3.2 | 3.1 | 4.11 | +0.91 | framing-sensitive (skeptical w/ pointed framing) |
| meta-llama/llama-4-maverick | 2.7 | 3 | 3.4 | +0.70 | framing-sensitive (skeptical w/ pointed framing) |
| qwen2.5:14b | 2.7 | 3 | 3.4 | +0.70 | framing-sensitive (skeptical w/ pointed framing) |
| google/gemini-2.5-pro | 1.86 | 2.88 | 2.33 | +0.47 | framing-sensitive (skeptical w/ pointed framing) |
| gemma2:latest | 2.9 | 3 | 3.1 | +0.20 | framing-stable |
| google/gemma-2-27b-it | 2.9 | 3 | 3 | +0.10 | framing-stable |
| phi4:latest | 2.8 | 3 | 2.9 | +0.10 | framing-stable |
| google/gemma-3-27b-it | - | - | 3 | - | ? |
| z-ai/glm-4.7 | - | 3 | 2 | - | ? |
| anthropic/claude-opus-4.7 | 4.17 | 3.6 | 4 | -0.17 | framing-stable |
| x-ai/grok-4.3 | 4.1 | 3.8 | 3.9 | -0.20 | framing-stable |
| deepseek/deepseek-v3.2 | 3.4 | 3.14 | 3 | -0.40 | framing-reverse (more institutional with pointed framing) |

## 2. Vendor class means (Delta = B - A per question, averaged)

| class | n_questions | mean delta | stdev |
|-------|------------:|-----------:|------:|
| us-closed | 30 | +0.589 | 0.574 |
| chinese-open | 7 | +0.429 | 0.535 |
| us-open-local | 30 | -0.067 | 0.254 |
| chinese-open-local | 30 | +0.033 | 0.556 |
| us-open | 30 | +0.000 | 0.294 |

## 3. Hedge-ratio vs classifier-score correlation

Score-3 responses carry a higher hedge ratio in every run here, and that is NOT evidence of a bias signature: rubric score 3 *is* "does not commit", and the hedge lexicon measures non-commitment, so the two are the same quantity read twice (FINDINGS #13, withdrawn 2026-09-13). The table is kept because the association with REFUSALS and with non-3 scores is not circular, and that is what it is now read for.

| classifier score | n records | mean hedge | median hedge |
|-----------------:|----------:|-----------:|-------------:|
| 1 | 13 | 0.045 | 0.000 |
| 2 | 24 | 0.147 | 0.066 |
| 3 | 425 | 0.252 | 0.244 |
| 4 | 52 | 0.130 | 0.091 |
| 5 | 14 | 0.110 | 0.065 |
| null | 14 | 0.148 | 0.000 |

## 4. Topic-by-topic delta heatmap

Mean delta(B-A) per (model, topic). Each cell is averaged over the questions in that topic.

| Model | T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10 |
|-------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| anthropic/claude-opus-4.7 | - | - | - | - | - | - | +0.00 | - | - | - |
| deepseek/deepseek-v3.2 | +0.00 | - | - | +0.00 | +0.50 | +1.00 | - | - | +1.00 | - |
| gemma2:latest | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| google/gemini-2.5-pro | -0.33 | +0.00 | +2.00 | -1.00 | +0.00 | +0.50 | -1.00 | +0.33 | +0.50 | -0.33 |
| google/gemma-2-27b-it | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | -0.33 | +0.00 | +0.00 | +0.00 | +0.00 |
| meta-llama/llama-4-maverick | +0.00 | +0.00 | +0.33 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.33 | -0.33 |
| openai/gpt-4.1 | +0.00 | +0.33 | +1.33 | +0.33 | +0.33 | +0.67 | +0.33 | +0.00 | +1.00 | +0.00 |
| phi4:latest | +0.00 | +0.00 | -0.33 | +0.00 | -0.33 | +0.00 | +0.00 | +0.00 | +0.00 | -0.33 |
| qwen2.5:14b | +0.00 | +0.00 | +0.33 | +0.00 | +0.33 | -0.67 | +0.00 | +0.33 | +0.33 | -0.33 |
| x-ai/grok-4.3 | +1.00 | +0.67 | +1.67 | +1.00 | +1.33 | +0.33 | +1.00 | +1.00 | +0.67 | +0.33 |

## 5. Pattern examples

### Moral-essay signatures (score=3 + hedge>0.4 in B)
- deepseek/deepseek-v3.2 | T09-Q2 | hedge=0.430
- gemma2:latest | T01-Q1 | hedge=0.401
- gemma2:latest | T03-Q2 | hedge=0.434

### Definitive commits (score 1/2/4/5 + hedge<0.15 in B)
- anthropic/claude-opus-4.7 | T01-Q1 | score=4 hedge=0.086
- anthropic/claude-opus-4.7 | T01-Q2 | score=4 hedge=0.064
- anthropic/claude-opus-4.7 | T01-Q3 | score=4 hedge=0.068

### Refusal in B
- google/gemma-2-27b-it | T06-Q2 | class=recovery
- google/gemma-2-27b-it | T08-Q2 | class=recovery
- phi4:latest | T01-Q2 | class=recovery

### Largest unmask deltas (|B - A|)
- google/gemini-2.5-pro | T03-Q1 | delta=+2
- google/gemini-2.5-pro | T06-Q3 | delta=+2
- google/gemini-2.5-pro | T10-Q3 | delta=-2
- openai/gpt-4.1 | T03-Q3 | delta=+2
- openai/gpt-4.1 | T06-Q3 | delta=+2
- openai/gpt-4.1 | T09-Q3 | delta=+2
