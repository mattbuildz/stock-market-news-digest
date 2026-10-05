# Examples

Small, real outputs of the pipeline, so you can see what it does without API keys or running anything.

Only metadata, headlines and the model's decisions are published here. Article text, news summaries and raw Finnhub dumps stay local — they are other people's content and Finnhub data.

## `stage1_sample.md` — classification

Results of a real stage 1 run (July 28, 2026): 710 news items in, one KEEP/REJECT decision per item out, with example decisions and the mistakes found in a manual review.

## `stage2_index_sample.json` — fetching 30 articles

The index that stage 2 writes after fetching the first 30 news items for AVGO (news from July 15–22, 2026, fetched on September 14, 2026). Three fields were added for this example: `html_size_kb`, `page_title` and `stage1_decision` (the decision from the stage 1 run above).

### What came back

| What the page really was | Items | How to tell |
|---|---:|---|
| article pages (247wallst, trefis, benzinga, fool, kiplinger, blockspace) | 18 | status 200, page title matches the headline |
| Yahoo cookie consent screen | 6 | **status 200**, title "Your privacy choices", always 109 KB |
| SeekingAlpha block | 3 | status 403, "Access to this page has been denied" |
| TheStreet block | 1 | status 403, empty page |
| Barchart empty response | 2 | status 202, 1 KB, no title |

"Article page" means the request reached the article's own page. Whether the text is complete or cut by a paywall is checked in stage 3–4 ([issue #4](https://github.com/mattbuildz/stock-market-news-digest/issues/4)).

### What this shows

1. **`source` is not where the article is.** Finnhub says "Yahoo" for 25 of the 30 items. Behind it are 8 different hosts, and none of them is an article on Yahoo. The real host is only known after following the redirect (`url_final`).
2. **HTTP 200 does not mean an article.** 24 responses returned 200, and 6 of them were the consent screen. That's why validation has to look at text length, host and page title instead of the status code.
3. **The important news is exactly what fails.** Stage 1 kept 4 of these 30 items (#2, #21, #25, #30). None of them produced an article: three hit the Yahoo consent screen and one got a 403. All 18 article pages belong to news that stage 1 rejected. Stage 2 fetched them anyway, because this test takes the first 30 items and is not yet connected to stage 1 decisions.

`url_final` of the consent pages was shortened: the session IDs from the original requests were removed.

## A later run: 300 pages

Not published as a file, only summarised here. Stage 2 fetched the first 300 news items (all 186 AVGO items and the first 114 AMD items, not only the ones stage 1 kept), then the stage 3 rules were applied offline: page title, real host and at least 500 characters of extracted text. Article text and headlines are not published.

| Result | Pages |
|---|---:|
| real article | **229** (76%) |
| blocked page (title like "Access to this page has been denied") | 23 |
| never downloaded (21 refused by robots.txt, 2 timeouts) | 23 |
| text shorter than 500 characters | 10 |
| HTTP 202 (empty answer) | 6 |
| HTTP 403 | 4 |
| HTTP 404 | 4 |
| no extractable text | 1 |

Text length of the 229 articles: median 3,453 characters, mean 3,777, 90th percentile 5,374, longest 23,280. At about 4 characters per token that is roughly 940 tokens on average.

| Host (after redirect) | Pages | Real articles |
|---|---:|---:|
| finance.yahoo.com | 90 | 80 |
| 247wallst.com | 54 | 54 |
| trefis.com | 30 | 30 |
| benzinga.com | 26 | 24 |
| fool.com | 21 | 21 |
| seekingalpha.com | 17 | 1 |
| stocktwits.com | 9 | 9 |
| barchart.com | 6 | 0 |
| other hosts | 24 | 10 |
| never downloaded | 23 | 0 |

| Ticker | Pages | Real articles | Items stage 1 kept | Of those, a real article |
|---|---:|---:|---:|---:|
| AVGO | 186 | 143 (77%) | 30 | 23 (77%) |
| AMD (first 114) | 114 | 86 (75%) | 37 | 24 (65%) |
| both | 300 | 229 (76%) | 67 | 47 (70%) |

The sample is not representative: MU, CRDO and SNOW were not fetched, and the pages were fetched in the order of the news file, not by importance.
