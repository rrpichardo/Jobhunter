"""One polite request each to public LinkedIn / X pages. No login, no disguise. Reports what comes back."""
from scrapling.fetchers import Fetcher

TESTS = {
    "LinkedIn public job search": "https://www.linkedin.com/jobs/search?keywords=AI%20product%20manager&location=United%20States",
    "X public search": "https://x.com/search?q=hiring%20%22AI%20product%20manager%22&f=live",
}
for name, url in TESTS.items():
    try:
        r = Fetcher.get(url, timeout=30, retries=1)
        text = str(r.html_content)
        print(f"\n{name}: status {r.status}, {len(text)} chars")
        print("  job-like links:", len(r.css("a[href*='/jobs/view/']")))
        print("  login wall words:", [w for w in ("Sign in", "Log in", "authwall", "Join now") if w.lower() in text.lower()])
    except Exception as e:
        print(f"\n{name}: FAILED -> {type(e).__name__}: {str(e)[:150]}")
