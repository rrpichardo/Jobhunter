"""Read hiring-post cards out of a rendered LinkedIn search page, without relying on LinkedIn's class names.

LinkedIn changes its page markup often, so nothing here uses a CSS class. A post is recognised by its identifier
(`urn:li:activity:<id>` and the `/feed/update/...` or `/posts/...-activity-<id>-xxxx` links), the card is the largest
block that holds exactly one post id, and the date comes from the id itself (LinkedIn's ids start with a millisecond
timestamp). Whatever cannot be read is counted, not guessed. Pure Python on an HTML string: no browser, no network.
"""

from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

URN = re.compile(r'urn:li:(activity|ugcPost|share):(\d{5,25})')
POSTS_PATH = re.compile(r'/posts/[A-Za-z0-9_%.\-]+-(activity|ugcPost|share)-(\d{5,25})-[A-Za-z0-9_]{1,10}')
PROFILE = re.compile(r'^/(?:in|company)/([A-Za-z0-9_%.\-]{1,100})/?$')
LINKEDIN_HOSTS = {'linkedin.com', 'www.linkedin.com'}
BLOCK_STOP = {'ul', 'ol', 'main', 'body', 'html', 'nav', 'header', 'aside'}  # a card never grows past these
INTERFACE_LINES = {'like', 'comment', 'repost', 'send', 'share', 'follow', 'connect', 'promoted', 'save',
                   'report this post', 'copy link to post', 'more', '…more', '...more', '…see more', 'see more',
                   'visible to anyone on or off linkedin', 'celebrate', 'support', 'love', 'insightful', 'funny'}
FIRST_POST_MS = int(datetime(2012, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
NO_RESULTS = re.compile(r'\bno results found\b', re.I)


def post_moment(post_id):
    """UTC datetime encoded in a LinkedIn post id (the top bits are milliseconds since 1970), or None."""
    millis = int(post_id) >> 22
    if not FIRST_POST_MS <= millis <= int(datetime.now(timezone.utc).timestamp() * 1000) + 86_400_000:
        return None
    return datetime.fromtimestamp(millis / 1000, timezone.utc)


def _post_refs(tag):
    """(kind, id) pairs named by one element's attributes (links and data attributes)."""
    refs = []
    for name, value in tag.attrs.items():
        for text in (value if isinstance(value, list) else [value]):
            if not isinstance(text, str) or len(text) > 2000:
                continue
            if name == 'href':
                path = urlsplit(text).path
                found = URN.search(path)
                if found:
                    refs.append((found[1], found[2]))
                    continue
                found = POSTS_PATH.fullmatch(path.rstrip('/')) or POSTS_PATH.search(path)
                if found:
                    refs.append((found[1], found[2]))
            else:
                found = URN.search(text)
                if found:
                    refs.append((found[1], found[2]))
    return refs


def _lines(card):
    lines = []
    for raw in card.get_text('\n').splitlines():
        line = ' '.join(raw.split())
        if not line or line.casefold() in INTERFACE_LINES or (lines and lines[-1] == line):
            continue
        lines.append(line)
    return lines


def extract_post_cards(html):
    """(cards, stats). Each card: kind, id, url, text, links (outside LinkedIn), author, created_at (UTC datetime).

    stats: post_ids (distinct ids on the page), cards (kept), undated (id without a believable date), empty (card
    without text), no_results (the page itself says there are no results).
    """
    soup = BeautifulSoup(html, 'html.parser')
    occurrences, under = {}, {}  # post id -> [(kind, element)]; element -> set of post ids inside it
    for tag in soup.find_all(True):
        for kind, post_id in _post_refs(tag):
            occurrences.setdefault(post_id, []).append((kind, tag))
            for node in [tag, *tag.parents]:
                under.setdefault(id(node), set()).add(post_id)
    cards, stats = [], {'post_ids': len(occurrences), 'cards': 0, 'undated': 0, 'empty': 0,
                        'no_results': bool(NO_RESULTS.search(soup.get_text(' ')))}
    for post_id, places in occurrences.items():
        created = post_moment(post_id)
        if created is None:
            stats['undated'] += 1
            continue
        card = places[0][1]
        for parent in card.parents:
            if parent.name in BLOCK_STOP or under.get(id(parent)) != {post_id}:
                break
            card = parent
        lines = _lines(card)
        if not lines:
            stats['empty'] += 1
            continue
        author, links = '', []
        for anchor in card.find_all('a', href=True):
            parts = urlsplit(anchor['href'])
            profile = PROFILE.match(parts.path) if (parts.hostname or 'www.linkedin.com') in LINKEDIN_HOSTS else None
            if profile and not author:
                author = ' '.join(anchor.get_text(' ').split()).split(' • ')[0][:100] or profile[1]
            elif parts.scheme == 'https' and parts.hostname and parts.hostname not in LINKEDIN_HOSTS:
                links.append(anchor['href'])
        kind = places[0][0]
        cards.append({'kind': kind, 'id': post_id, 'url': f'https://www.linkedin.com/feed/update/urn:li:{kind}:{post_id}/',
                      'text': '\n'.join(lines), 'links': list(dict.fromkeys(links)), 'author': author,
                      'created_at': created})
    stats['cards'] = len(cards)
    return cards, stats
