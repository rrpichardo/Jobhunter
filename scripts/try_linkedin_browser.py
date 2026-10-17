"""One browser-mode visit to LinkedIn's public job search. No login, no stealth. Reports what is visible."""
from scrapling.fetchers import DynamicFetcher

URL = "https://www.linkedin.com/jobs/search?keywords=AI%20product%20manager&location=United%20States"
r = DynamicFetcher.fetch(URL, headless=True, network_idle=True, timeout=60000)
text = str(r.html_content)
cards = r.css("a[href*='/jobs/view/']")
print("status:", r.status, "| chars:", len(text), "| job links:", len(cards))
print("login wall words:", [w for w in ("authwall", "Sign in to view", "Join now") if w.lower() in text.lower()])
seen = set()
for a in cards:
    href = a.attrib["href"].split("?")[0]
    title = " ".join(a.text.split())
    if title and href not in seen:
        seen.add(href)
        print("-", title[:70], "|", href)
    if len(seen) >= 8:
        break
