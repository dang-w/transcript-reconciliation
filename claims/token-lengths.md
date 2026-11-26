# Token lengths of the 20 transcripts

Measured on 26 November 2026. No monitor read a transcript: the program `llama-tokenize` of llama.cpp (build
b11612) loads the vocabulary of a model file and counts. No text was generated and the machine stayed in
interactive mode. Files: `Ministral-3-8B-Instruct-2512-Q8_0.gguf` and `gemma-4-E4B-it-Q8_0.gguf`. Transcripts:
`scripts/render` at the commit of this file.

Each monitor is served with 32,768 tokens for each slot and an answer limit of 4,096 tokens.

## 1. The forms

| Form | Content |
|---|---|
| full | Task, reasoning, agent messages, tool calls, tool outputs |
| visible | The same without reasoning. Proposed for the monitors. |
| visible + events | "visible", and for each tool output the exit code and the overlap mark. The largest variant in use. |
| calls | Task, tool calls, tool outputs, the last agent message |
| actions | Task, tool calls, tool outputs. No agent message at all. |
| actions + events | "actions" with the exit code and the overlap mark |

## 2. Smallest and largest, in tokens

| Form | Ministral-3-8B | Gemma 4 E4B | Samples that do not fit |
|---|---|---|---|
| full | 10,081 to 58,637 | 10,584 to 61,226 | 4 of 20 |
| visible | 5,114 to 17,883 | 5,298 to 18,438 | 0 of 20 |
| visible + events | 5,525 to 18,632 | 5,741 to 19,066 | 0 of 20 |
| calls | 4,720 to 17,178 | 4,886 to 17,703 | 0 of 20 |
| actions | 4,720 to 17,129 | 4,886 to 17,650 | 0 of 20 |
| actions + events | 5,008 to 17,878 | 5,204 to 18,278 | 0 of 20 |

The "full" form does not fit for: run A 574105, run B 511704, run D 511704, run D 574105 (Gemma 4 E4B; for Ministral-3-8B, 3 of
these 4).

## 3. The margin for each sample, largest variant

Margin = 32,768 − transcript ("visible + events") − prompt − answer limit − 64.

- Prompt: a draft of the monitor prompt with the longest claim of the set (238 characters): 295 tokens for
  Ministral-3-8B, 303 for Gemma 4 E4B. The final prompt is not written yet.
- Answer limit: 4,096, the limit of the server.
- 64: an allowance for the chat template, which was not measured.

| Run | Sample | Ministral-3-8B: transcript | Margin | Gemma 4 E4B: transcript | Margin |
|---|---|---|---|---|---|
| A | 26576 | 6,114 | 22,199 | 6,395 | 21,910 |
| A | 511704 | 7,394 | 20,919 | 7,746 | 20,559 |
| A | 574105 | 6,491 | 21,822 | 6,664 | 21,641 |
| A | 598634 | 7,149 | 21,164 | 7,290 | 21,015 |
| A | 76105 | 7,186 | 21,127 | 7,516 | 20,789 |
| B | 26576 | 6,275 | 22,038 | 6,582 | 21,723 |
| B | 511704 | 8,228 | 20,085 | 8,508 | 19,797 |
| B | 574105 | 5,733 | 22,580 | 5,812 | 22,493 |
| B | 598634 | 8,464 | 19,849 | 8,728 | 19,577 |
| B | 76105 | 11,793 | 16,520 | 12,641 | 15,664 |
| C | 26576 | 6,582 | 21,731 | 6,876 | 21,429 |
| C | 511704 | 7,604 | 20,709 | 7,796 | 20,509 |
| C | 574105 | 9,654 | 18,659 | 10,012 | 18,293 |
| C | 598634 | 5,525 | 22,788 | 5,741 | 22,564 |
| C | 76105 | 6,694 | 21,619 | 7,097 | 21,208 |
| D | 26576 | 5,736 | 22,577 | 6,059 | 22,246 |
| D | 511704 | 11,804 | 16,509 | 12,178 | 16,127 |
| D | 574105 | 18,632 | 9,681 | 19,066 | 9,239 |
| D | 598634 | 7,312 | 21,001 | 7,615 | 20,690 |
| D | 76105 | 7,879 | 20,434 | 8,163 | 20,142 |

All 20 samples fit in every variant in use, for both monitors. Nothing is shortened. The smallest margin is
9,239 tokens (run D, 574105, Gemma 4 E4B).

## 4. What this cannot show

- The count of the server for a request. The chat template and the final prompt add tokens that are estimated
  here and not measured.
- That a monitor reads a long transcript well. A fit is not a capacity.
