from urllib.robotparser import RobotFileParser
import urllib.request

import requests

import json
import pprint
import os
import time
from datetime import datetime

from urllib.parse import urlparse

with open("data/news_2026-07-15_2026-07-22.json", "r", encoding="utf-8") as f:
    news_items = json.load(f)


#create the folder where full articles are saved
os.makedirs("data/html/",exist_ok=True)

headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language":"en-US,en;q=0.9"}
session = requests.Session()
session.headers.update(headers)



opener =  urllib.request.build_opener()
opener.addheaders = [("User-agent", headers["User-Agent"])]
urllib.request.install_opener(opener)

robot_cache = {}
index = []


# Previous index.json -> {number: entry}, used to skip re-downloads.
if os.path.exists("data/html/index.json"):
    old_by_number = {}

    with open("data/html/index.json", "r", encoding="utf-8") as f:
        old_list = json.load(f)
    for wpis in old_list:
        
        old_by_number[wpis["number"]] = wpis


else:
    old_by_number = {} #First run: no index on disk yet


for number, news in enumerate(news_items[:90], start=1):
    url = news["url"]

    old = old_by_number.get(number)


    # Reuse the previous index entry (keeps real status/url_final).
    # Skip download + sleep — otherwise a second run would wipe metadata.
    if old is not None:
       
        index.append(old)
            
        continue          #continue here, because otherwise time.sleep(4) at the bottom would run
    

    else:
        print(number)
        print("no previous index entry, downloading")

        try:
            r = session.get(url, timeout = 15)
            print(r)

            host = urlparse(r.url).netloc
            print(host)

            #robot_cache[host] = robot_parser

            ### robot parser
            if host not in robot_cache:
                robot_parser = RobotFileParser()
                print(f"FETCHING ROBOTS.TXT FOR {host} (first time)")
                robot_parser.set_url(f"https://{host}/robots.txt")
                robot_parser.read()

                robot_cache[host] = robot_parser 
            else:
                robot_parser = robot_cache[host]

            allowed = robot_parser.can_fetch(headers["User-Agent"], r.url)

            if allowed == False:
                print("ROBOTS.TXT DISALLOWS THIS URL")
                entry = {
                    "number":number, 
                    "ticker":news["ticker"],
                    "headline":news["headline"],
                    "source":news["source"],
                    "url_finnhub":url,
                    "status":None,
                    }
                index.append(entry)            
            else:
                print("ALLOWED BY ROBOTS.TXT")
                
                file_name = f"{number:03d}_{host}.html"

                with open(f"data/html/{file_name}", "w", encoding="utf-8") as f:
                    f.write(r.text)

                entry = {
                    "number":number, 
                    "ticker":news["ticker"],
                    "headline":news["headline"],
                    "source":news["source"],
                    "url_finnhub":url,
                    "url_final":r.url,
                    "host":host,
                    "status":r.status_code,
                    "html_file":file_name,
                    "fetched_at":datetime.now().isoformat()}

                index.append(entry)


        except requests.exceptions.RequestException as e:
            print("REQUEST FAILED")
            entry = {
                "number":number, 
                "ticker":news["ticker"],
                "headline":news["headline"],
                "source":news["source"],
                "url_finnhub":url,
                "status":None,
                "error":str(e)
                }
            index.append(entry)
            
                
    time.sleep(4)


with open(f"data/html/index.json", "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent = 2)




#pprint.pprint(index)
