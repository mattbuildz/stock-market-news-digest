import trafilatura
import json
from bs4 import BeautifulSoup




with open("data/html/index.json", "r", encoding="utf-8") as f:
    articles = json.load(f)


accepted = 0
rejected = 0

min_text_length = 500

BLOCK_TITLE_SIGNATURES = [
    "Your privacy choices",
    "Access to this page has been denied",
    "Just a moment...",
    "Restricted Access",
    "Are you a robot",
]


for article in articles:


    if "html_file" not in article:    #article["html_file"]
        continue
    else:
        html = article["html_file"]

        with open(f"data/html/{html}", encoding="utf-8") as html_content:
            result = html_content.read()

    true_content = trafilatura.extract(result, favor_precision=True)


    # Parse HTML so we can read <title> without regex.
    # BeautifulSoup does not fetch the page — it only parses `result`.
    soup = BeautifulSoup(result, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    if any(signature in title for signature in BLOCK_TITLE_SIGNATURES): #it checks if any title contains signature from BLOCKED_TITLE_SIGNATURES
        rejected += 1


        article["validation_ok"] = False
        article["rejection_reason"] = "blocked_page"
        article["text_length"] = 0


    elif article["host"] == "consent.yahoo.com":
        rejected += 1

        article["validation_ok"] = False
        article["rejection_reason"] = "consent_screen"
        article["text_length"] = 0


    elif article["status"] != 200:
        rejected += 1

        article["validation_ok"] = False
        article["rejection_reason"] = f"http_{article['status']}"
        article["text_length"] = 0


    elif true_content is None:
        rejected += 1

        article["validation_ok"] = False
        article["rejection_reason"] = "no_text"
        article["text_length"] = 0


    elif len(true_content) < min_text_length:
        rejected += 1

        article["validation_ok"] = False
        article["rejection_reason"] = "short_text"
        article["text_length"] = len(true_content)



    else:
        accepted += 1

        article["validation_ok"] = True
        article["rejection_reason"] = None
        article["text_length"] = len(true_content)


print(f"TOTAL: {len(articles)}")
print(f"OK: {accepted}, REJECTED: {rejected}")
    

with open("data/html/index.json", "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)
