# Stage 1 example: KEEP / REJECT classification

A real run from **July 28, 2026** — prompt v14, model `claude-haiku-4-5`, `temperature=0`, batches of up to 100 items.
Input: **710 news items** from Finnhub for AVGO, AMD, MU, CRDO and SNOW, week of July 15–22, 2026.

Only headlines are shown. Summaries and article text are not published.

The prompt is in Polish, but the labels are in English. This run used the earlier Polish label names; they were renamed to English offline in the saved responses, with no new model calls. The model answers one line per news item in a fixed format:

```
number|DECISION|CATEGORY
```

## Result of the run

| | Count | Share |
|---|---:|---:|
| News items in | 710 | |
| Answers out | 710 | every item answered exactly once, 0 format errors in the line structure |
| **KEEP** | **180** | **25.4%** |
| REJECT | 530 | 74.6% |

### Categories

| Decision / category | Meaning | Count |
|---|---|---:|
| REJECT / NO_FACT | no new fact: opinion, comparison, clickbait | 229 |
| REJECT / NOT_ABOUT_COMPANY | not about the analyzed company | 194 |
| REJECT / PRICE_MOVE | only a share price move | 107 |
| KEEP / DEAL | deal, contract, partnership, financing | 72 |
| KEEP / OTHER_FACT | other concrete, verifiable fact | 34 |
| KEEP / RATING | price target, analyst or credit rating | 27 |
| KEEP / RESULTS | financial results, guidance, figures | 20 |
| KEEP / OPERATIONS | product, production, management change | 10 |
| KEEP / POSITION | shares bought or sold by an investor, fund or insider | 10 |
| KEEP / REGULATION | regulatory or legal decision | 5 |
| KEEP / PRICE_MOVE | **format error** — this category is only allowed with REJECT | 2 |

### KEEP share per company

| Company | News items | KEEP |
|---|---:|---:|
| AMD | 247 | 33.6% |
| MU | 249 | 21.3% |
| AVGO | 186 | 19.4% |
| CRDO | 22 | 18.2% |
| SNOW | 6 | 66.7% |

The previous prompt (selection instead of classification) kept 4% of one batch and 93% of another in the same run. With classification every larger company stays between 18% and 34%.

## Example decisions (checked by hand)

| # | Batch | Headline | Output | Why it's right |
|---:|---|---|---|---|
| 173 | AVGO | Apple Plans to Spend $30 Billion in a Deal With Broadcom (AVGO) – Reuters | KEEP / DEAL | the fact is in the headline, even though the attached summary was an unrelated generic paragraph |
| 333 | AMD | Cathie Wood Dumps $39 Million Worth of AMD Stock | KEEP / POSITION | a concrete sale of AMD shares |
| 107 | AVGO | Broadcom Legal Chief Sold Nearly $20 Million of Stock After Apple Partnership Boosted Shares | KEEP / POSITION | an insider sale |
| 274 | AMD | AMD's Microsoft Alliance Expands AI Prospects: More Upside Ahead? | KEEP / DEAL | a partnership, and the article is about AMD |
| 31 | AVGO | AMD's Microsoft Alliance Expands AI Prospects: More Upside Ahead? | REJECT / NOT_ABOUT_COMPANY | **the same article** in the Broadcom batch — correctly rejected, because it's about AMD |
| 68 | AVGO | Meet the Super Semiconductor ETF Obliterating Nvidia, AMD, and Broadcom This Year | REJECT / NOT_ABOUT_COMPANY | an ETF article; Broadcom is just a name on a list |
| 23 | AVGO | This Is My Favorite Artificial Intelligence Stock to Buy Right Now (Hint: Not Nvidia, Broadcom, or Alphabet) | REJECT / NOT_ABOUT_COMPANY | explicitly not about Broadcom |

## Known mistakes in this run (found in a manual review)

| # | Batch | Headline | Output | Problem |
|---:|---|---|---|---|
| 261 | AMD | These 2 Analysts Just Upped Their AMD Stock Price Targets. Here’s Why. | REJECT / NO_FACT | a real price target raise — should be KEEP / RATING |
| 487 | MU | What's Going on With Micron Technology Stock Wednesday? | REJECT / PRICE_MOVE | the summary said analysts raised price targets — should be KEEP |
| 428 | AMD | AMD Falls 5%, Intel Drops 4%, NVIDIA Slides 3% Before Recovering as Rotation Hits Semiconductor Stocks | KEEP / PRICE_MOVE | format error: PRICE_MOVE exists only for REJECT — should be REJECT |
| 590 | MU | Micron Stock Jumps as SK Hynix Warns AI Memory Boom Won't Last Forever | REJECT / PRICE_MOVE | an industry-wide warning that matters for Micron; the rule only covers facts about the company itself — an open design question, not just a model error |

Overall the manual review found **~4 missed facts out of 530 rejections** and **~13 unnecessary KEEPs out of 180**. The errors lean towards keeping too much, which is the cheaper direction: an extra news item costs a few tokens later, a missed one is lost.

There is no hand-labeled test set yet, so these numbers are indications, not a measured recall or precision — see [issue #6](https://github.com/itsamattbuild/stock-market-news-digest/issues/6).
