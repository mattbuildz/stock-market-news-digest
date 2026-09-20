import trafilatura
import json



with open("data/html/index.json", "r", encoding="utf-8") as f:
    articles = json.load(f)


for article in articles:
    if "html_file" not in article:    #article["html_file"]
        continue
    else:
        html = article["html_file"]

        # with open(f"data/html/{html}", "w", encoding="utf-8") as f:
        #     f.read()



        html_content = open(f"data/html/{html}", encoding="utf-8")
        result = html_content.read()

    true_content = trafilatura.extract(result, favor_precision=True)
    print(true_content)