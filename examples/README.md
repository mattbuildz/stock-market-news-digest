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

"Article page" means the request reached the article's own page. Whether the text is complete or cut by a paywall is checked in stage 3–4 ([issue #4](https://github.com/itsamattbuild/stock-market-news-digest/issues/4)).

### What this shows

1. **`source` is not where the article is.** Finnhub says "Yahoo" for 25 of the 30 items. Behind it are 8 different hosts, and none of them is an article on Yahoo. The real host is only known after following the redirect (`url_final`).
2. **HTTP 200 does not mean an article.** 24 responses returned 200, and 6 of them were the consent screen. That's why validation has to look at text length, host and page title instead of the status code.
3. **The important news is exactly what fails.** Stage 1 kept 4 of these 30 items (#2, #21, #25, #30). None of them produced an article: three hit the Yahoo consent screen and one got a 403. All 18 article pages belong to news that stage 1 rejected. Stage 2 fetched them anyway, because this test takes the first 30 items and is not yet connected to stage 1 decisions.

`url_final` of the consent pages was shortened: the session IDs from the original requests were removed.
