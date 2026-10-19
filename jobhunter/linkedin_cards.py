"""Read hiring-post cards out of a rendered LinkedIn search page, without relying on LinkedIn's class names.

LinkedIn changes its page markup often, so nothing here uses a CSS class. A post is recognised by its identifier
(`urn:li:activity:<id>` and the `/feed/update/...` or `/posts/...-activity-<id>-xxxx` links), the card is the largest
block that holds exactly one post id and no page furniture (navigation, search form, filters, headings), and the date
comes from the id itself (LinkedIn's ids start with a millisecond timestamp). Ids found in side panels, headers,
footers, scripts or the page head are ignored; a post nested inside another card is left out of the outer card's text.
Whatever cannot be read is counted, not guessed. Pure Python on an HTML string: no browser, no network.
"""

from datetime import datetime, timezone
from statistics import median
import re
from urllib.parse import parse_qs, unquote, urlsplit

from bs4 import BeautifulSoup, NavigableString

URN = re.compile(r'urn:li:(activity|ugcPost|share):(\d{5,25})')
POSTS_PATH = re.compile(r'/posts/[A-Za-z0-9_%.\-]+-(activity|ugcPost|share)-(\d{5,25})-[A-Za-z0-9_]{1,10}')
PROFILE = re.compile(r'^/(?:in|company)/([A-Za-z0-9_%.\-]{1,100})/?$')
BLOCK_STOP = {'ul', 'ol', 'main', 'body', 'html', 'nav', 'header', 'aside'}  # a card never grows past these
IGNORED = {'head', 'script', 'style', 'template', 'noscript', 'aside', 'nav', 'header', 'footer'}  # ids here are not results
SKIPPED_TEXT = {'script', 'style', 'template', 'noscript'}
CHROME = ['nav', 'form', 'input', 'select', 'h1']  # page furniture: a card never grows to hold any of these
MAX_CARD_CHARS = 6000
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


def is_linkedin_host(host):
    host = (host or 'www.linkedin.com').casefold()
    return host == 'linkedin.com' or host.endswith(('.linkedin.com', '.licdn.com'))


def _values(tag):
    for name, value in tag.attrs.items():
        for text in (value if isinstance(value, list) else [value]):
            if isinstance(text, str) and len(text) <= 2000:
                yield name, unquote(text)


def _post_refs(tag):
    """(id, kind) pairs named by one element's attributes (links and data attributes)."""
    refs = []
    for name, text in _values(tag):
        if name == 'href':
            path = urlsplit(text).path
            found = URN.search(path) or POSTS_PATH.search(path)
            if found:
                refs.append((found[2], found[1]))
        else:
            found = URN.search(text)
            if found:
                refs.append((found[2], found[1]))
    return refs


def _ignored(tag):
    return tag.name in IGNORED or any(parent.name in IGNORED for parent in tag.parents)


def scan(soup, refs):
    """({id: [(kind, element)]}, {element id: ids inside it}); ids under page furniture are not results."""
    occurrences, under = {}, {}
    for tag in soup.find_all(True):
        if _ignored(tag):
            continue
        for item_id, kind in refs(tag):
            occurrences.setdefault(item_id, []).append((kind, tag))
            for node in [tag, *tag.parents]:
                under.setdefault(id(node), set()).add(item_id)
    return occurrences, under


def grow(places, item_id, under):
    """The card: from the outermost element naming the id, up to the largest block holding that id alone, no furniture."""
    card = min((tag for _, tag in places), key=lambda tag: len(list(tag.parents)))
    for parent in card.parents:
        if (parent.name in BLOCK_STOP or under.get(id(parent)) != {item_id} or parent.find(CHROME)
                or len(parent.get_text()) > MAX_CARD_CHARS):
            break
        card = parent
    return card


def walk(node, item_id, under):
    """Descendants in order, leaving out anything that belongs to a different item (a nested suggested post)."""
    for child in node.children:
        if isinstance(child, NavigableString):
            if type(child) is NavigableString:
                yield child
        elif child.name not in SKIPPED_TEXT:
            ids = under.get(id(child))
            if ids and item_id not in ids:
                continue
            yield child
            yield from walk(child, item_id, under)


def card_lines(card, item_id, under):
    lines = []
    for node in walk(card, item_id, under):
        if not isinstance(node, NavigableString):
            continue
        line = ' '.join(str(node).split())
        if not line or line.casefold() in INTERFACE_LINES or (lines and lines[-1] == line):
            continue
        lines.append(line)
    return lines


def shape(cards, stats):
    """Numbers that tell a healthy page from a misread one: how many cards are very short, and their typical size."""
    stats['short_cards'] = sum(len(card['text'].splitlines()) < 3 for card in cards)
    stats['median_chars'] = int(median(len(card['text']) for card in cards)) if cards else 0
    return stats


def page_facts(soup):
    scripts = ' '.join(t.string or '' for t in soup.find_all(['script', 'code']))
    return {'no_results': bool(NO_RESULTS.search(soup.get_text(' '))), 'script_ids': len(set(URN.findall(scripts))),
            'login_form': soup.find('input', attrs={'type': 'password'}) is not None}


def _person(anchor):
    text = ' '.join(anchor.get_text(' ').split()).split(' • ')[0][:100]
    words = text.split()
    half = len(words) // 2
    return ' '.join(words[:half]) if half and len(words) % 2 == 0 and words[:half] == words[half:] else text


def extract_post_cards(html):
    """(cards, stats). Each card: kind, id, url, text, links (outside LinkedIn), author, created_at (UTC datetime).

    stats: post_ids (distinct ids on the page), cards (kept), undated (id without a believable date), empty (card
    without text), short_cards, median_chars, no_results, script_ids (ids only in scripts: not used), login_form.
    """
    soup = BeautifulSoup(html, 'html.parser')
    facts = page_facts(soup)
    occurrences, under = scan(soup, _post_refs)
    stats = {'post_ids': len(occurrences), 'cards': 0, 'undated': 0, 'empty': 0, **facts}
    cards = []
    for post_id, places in ([] if facts['no_results'] else occurrences.items()):  # a page that says "no results" has none
        created = post_moment(post_id)
        if created is None:
            stats['undated'] += 1
            continue
        card = grow(places, post_id, under)
        lines = card_lines(card, post_id, under)
        if not lines:
            stats['empty'] += 1
            continue
        author, links = '', []
        for node in walk(card, post_id, under):
            if isinstance(node, NavigableString) or node.name != 'a' or not node.get('href'):
                continue
            parts = urlsplit(node['href'])
            if is_linkedin_host(parts.hostname):
                if parts.path.startswith('/redir/redirect'):  # LinkedIn's wrapper around an outside link
                    target = (parse_qs(parts.query).get('url') or [''])[0]
                    if urlsplit(target).scheme == 'https' and not is_linkedin_host(urlsplit(target).hostname):
                        links.append(target)
                elif not author and PROFILE.match(parts.path):
                    author = _person(node)  # only a real name; a bare slug or an avatar link is not one
            elif parts.scheme == 'https' and parts.hostname:
                links.append(node['href'])
        kind = places[0][0]
        cards.append({'kind': kind, 'id': post_id, 'url': f'https://www.linkedin.com/feed/update/urn:li:{kind}:{post_id}/',
                      'text': '\n'.join(lines), 'links': list(dict.fromkeys(links)), 'author': author,
                      'created_at': created})
    stats['cards'] = len(cards)
    return cards, shape(cards, stats)
