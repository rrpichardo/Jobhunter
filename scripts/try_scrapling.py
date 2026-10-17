"""Tiny test: read the a16z job board with Scrapling and list AI product manager jobs."""
from scrapling.fetchers import Fetcher

URL = "https://jobs.a16z.com/jobs?q=AI%20product%20manager"
page = Fetcher.get(URL, timeout=30)

seen = {}
for a in page.css("a[href^='/jobs/']"):
    parts = a.attrib["href"].strip("/").split("/")
    if len(parts) == 3:  # /jobs/<company>/<id--title-slug>
        seen[a.attrib["href"]] = (parts[1], parts[2].split("--", 1)[-1].replace("-", " "))

pm = {h: v for h, v in seen.items() if "product" in v[1]}
print(f"Found {len(seen)} jobs on the page, {len(pm)} with 'product' in the title\n")
for href, (company, title) in list(pm.items())[:10]:
    print(f"- {title}  @ {company}\n    https://jobs.a16z.com{href}")
