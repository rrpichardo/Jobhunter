"""Weekly job newsletters read from their public feed: one edition becomes one candidate for the AI read step.

Ali Rohde Jobs lists chief of staff, BizOps and VC roles each Friday, with a direct application link on every title.
Code fetches the public feed (no login, no secret, no allowance); Claude proposes the facts for each role in an edition;
`jobhunter.post_facts` accepts a fact only when every value appears word for word in the edition text, exactly as for
Hacker News comments and social posts. Each link's address is written beside its text, so Claude can pair a role with
its own application link; the application link must be one of the edition's links.
"""

from datetime import datetime, timedelta
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import feedparser

from jobhunter.postings import clean_html, parse_posted
from jobhunter.records import https_url

FEEDS = {'alirohde-rss': {'url': 'https://alirohdejobs.substack.com/feed', 'host': 'alirohdejobs.substack.com'}}
MAX_ENTRIES = 12  # the feed carries about 20 editions; only recent ones can be inside the window


def edition_candidates(source_id, feed_text, now, lookback_days):
    """(candidates, stats) for editions published inside the window; anything unreadable is counted, not guessed."""
    host = FEEDS[source_id]['host']
    parsed = feedparser.parse(feed_text)
    if not parsed.entries:  # a real feed always carries editions; an HTML page (a bot check) carries none
        raise ValueError('invalid_board_response')
    cutoff = now - timedelta(days=lookback_days)
    candidates, stats = [], {'editions': 0, 'in_window': 0, 'unreadable': 0}
    for entry in parsed.entries[:MAX_ENTRIES]:
        stats['editions'] += 1
        link = entry.get('link') or ''
        created = parse_posted(entry.get('published'))
        content = ((entry.get('content') or [{}])[0].get('value') or entry.get('summary') or '')
        if not created or urlsplit(link).hostname != host or not content:
            stats['unreadable'] += 1
            continue
        if datetime.fromisoformat(created) < cutoff:
            continue
        stats['in_window'] += 1
        soup = BeautifulSoup(content, 'html.parser')
        links = []
        for anchor in soup.find_all('a', href=True):
            address = anchor['href']
            if not https_url(address) or urlsplit(address).hostname == host:
                continue  # the newsletter's own subscribe and share links are not jobs
            anchor.append(f' [{address}]')  # the address sits beside its text, so a role can be paired with its link
            links.append(address)
        text = clean_html(str(soup))
        if text:
            candidates.append({'url': link, 'created_at': created, 'text': text, 'links': list(dict.fromkeys(links)),
                               'author': 'Ali Rohde Jobs'})
        else:
            stats['unreadable'] += 1
    return candidates, stats
