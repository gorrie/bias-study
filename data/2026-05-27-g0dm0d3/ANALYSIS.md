# Bias Study Analysis - 2026-05-27-g0dm0d3

Records analyzed: 60.

## 1. Framing sensitivity

Per-model B-condition score across mild / neutral / pointed framings. A model whose pointed-position score is higher than its mild-position score is framing-sensitive — it commits to skepticism only when the question pre-frames it. A framing-stable model holds its position regardless.

| Model | mild B | neutral B | pointed B | Delta(mild->pointed) | type |
|-------|------:|---------:|---------:|--------------------:|------|

## 2. Vendor class means (Delta = B - A per question, averaged)

| class | n_questions | mean delta | stdev |
|-------|------------:|-----------:|------:|

## 3. Hedge-ratio vs classifier-score correlation

If high hedge correlates with score=3, the 'moral essay mode' is the bias signature. If high hedge correlates with refusals or non-3 scores, the picture is more nuanced.

| classifier score | n records | mean hedge | median hedge |
|-----------------:|----------:|-----------:|-------------:|
| 3 | 26 | 0.082 | 0.074 |
| 4 | 26 | 0.063 | 0.056 |
| 5 | 8 | 0.083 | 0.063 |

## 4. Topic-by-topic delta heatmap

Mean delta(B-A) per (model, topic). Each cell is averaged over the questions in that topic.

| Model |  |
|-------||

## 5. Pattern examples

### Moral-essay signatures (score=3 + hedge>0.4 in B)

### Definitive commits (score 1/2/4/5 + hedge<0.15 in B)

### Refusal in B

### Largest unmask deltas (|B - A|)
