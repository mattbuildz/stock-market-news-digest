from urllib.robotparser import RobotFileParser
import urllib.request


from base64 import encode
from typing import Any

import requests

import json
import pprint
import os
import time
import glob
from datetime import datetime

from urllib.parse import urlparse

from urllib3.exceptions import HostChangedError

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

entry = {}


for number, news in enumerate(news_items[:30], start=1):
    url = news["url"]
    found_files = glob.glob(f"data/html/{number:03d}_*.html")

    if found_files != []:
        #print(glob.glob(f"data/html/{number:03d}_*.html"))
        #print(found_files)
        file_name = os.path.basename(found_files[0])
        host = file_name.removeprefix(f"{number:03d}_").removesuffix(".html")


        entry = {
            "number":number, 
            "ticker":news["ticker"],
            "headline":news["headline"],
            "source":news["source"],
            "url_finnhub":url,
            "host":host,
            "status":"FROM_DISK",
            "html_file":file_name,
            "fetched_at":datetime.now().isoformat()}

        index.append(entry)


        continue          #continue here, because otherwise time.sleep(4) at the bottom would run
 

    else:
        print("not on disk, downloading")

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









