"""Groups one story's versions from different publishers.

When the same news is reported by several publishers, each article gets the
same story_id, so the feed can show one card per story and the article page
can compare the versions. Two articles belong to the same story when they
come from different publishers, were published within STORY_WINDOW of each
other and have matching headlines (trust_scorer.related_title, the same rule
used for related coverage in the trust score).

Grouping happens once, when an article is saved, so reading the feed stays
fast. A story's id is the id of one of its articles.
"""
import logging
import re
from datetime import timedelta
from typing import Dict, Iterable, List

from app.services.content_analyzer import _NUMBER, _PHOTO_CREDIT, _QUOTE, _body
from app.services.storage import storage_service
from app.services.trust_scorer import publisher_domain, related_title

logger = logging.getLogger(__name__)

STORY_WINDOW = timedelta(hours=48)
BACKFILL_MIGRATION = "story-groups-v1"
MAX_DETAILS_PER_VERSION = 4


def same_story(first, second) -> bool:
    """True when two articles (objects with title/url/published_date) are one story."""
    if publisher_domain(first.url) == publisher_domain(second.url):
        return False
    if abs(first.published_date - second.published_date) > STORY_WINDOW:
        return False
    return related_title(first.title, second.title)


def can_join(article, members: List) -> int:
    """How strongly `article` fits an existing story (0 = it does not).

    Stricter than "matches one version", so an ongoing story's updates do not
    chain into one huge group (Monday's flood figures, Tuesday's, ...):
      - it matches at least half of the story's versions,
      - the whole story stays within STORY_WINDOW,
      - a version from the same publisher must have a closely matching headline
        (a re-post is fine; two different stories from one publisher are not).
    """
    dates = [m.published_date for m in members] + [article.published_date]
    if max(dates) - min(dates) > STORY_WINDOW:
        return 0
    domain = publisher_domain(article.url)
    for member in members:
        if publisher_domain(member.url) == domain and not related_title(article.title, member.title):
            return 0
    matched = sum(1 for m in members if same_story(article, m))
    return matched if matched * 2 >= len(members) else 0


async def assign_story(article) -> str:
    """Give `article` (ArticleInDB) a story id: the best-fitting existing story
    among its matches, or a new story of its own."""
    if article.story_id and article.story_id != article.id:
        return article.story_id
    candidates = await storage_service.find_story_candidates(
        article.keywords, article.url, article.published_date, STORY_WINDOW)
    matches = [c for c in candidates if same_story(article, c)]
    best, best_fit = None, 0
    for story_id in dict.fromkeys(m.story_id or m.id for m in matches):
        members = await storage_service.get_articles_by_story(story_id)
        if not members:                       # a matching article not grouped yet
            members = [m for m in matches if m.id == story_id]
        fit = can_join(article, [m for m in members if m.id != article.id])
        if fit > best_fit:
            best, best_fit = story_id, fit
    target = best or article.id
    ids = [article.id]
    if best:                                   # give an ungrouped matching article the story id too
        ids += [m.id for m in matches if (m.story_id or m.id) == best and not m.story_id]
    await storage_service.merge_story(target, ids, [])
    return target


async def backfill_once() -> int:
    """One time: group every stored article, oldest first. Returns how many
    articles belong to a story with more than one version afterwards."""
    if await storage_service.migration_done(BACKFILL_MIGRATION):
        return 0
    articles = await storage_service.get_all_articles_oldest_first()
    for article in articles:
        fresh = await storage_service.get_article_by_id(article.id)   # story_id may have changed meanwhile
        if fresh:
            await assign_story(fresh)
    shared = await storage_service.count_articles_in_shared_stories()
    await storage_service.mark_migration_done(BACKFILL_MIGRATION, {"articles": len(articles), "in_shared_stories": shared})
    logger.info(f"Grouped {len(articles)} stored articles into stories ({shared} in stories with several versions).")
    return shared


def combine_by_story(articles: Iterable) -> List[Dict]:
    """One entry per story (or per developing story), in the order they first
    appear. For a developing story the entry is its latest update. The entry
    is that story's version with the highest trust score (earliest on a tie),
    with the other versions' publishers in `also_reported_by` and the number
    of updates in `updates`."""
    groups: Dict[str, List] = {}
    for article in articles:
        key = getattr(article, "thread_id", None) or article.story_id or article.id
        groups.setdefault(key, []).append(article)
    combined = []
    for members in groups.values():
        stories: Dict[str, List] = {}
        for member in members:
            stories.setdefault(member.story_id or member.id, []).append(member)
        latest = max(stories.values(), key=lambda versions: min(v.published_date for v in versions))
        lead = max(latest, key=lambda a: (a.trust_score or 0, -a.published_date.timestamp()))
        others = []
        for version in latest:
            if version is not lead and version.source not in others and version.source != lead.source:
                others.append(version.source)
        combined.append({"article": lead, "also_reported_by": others, "updates": len(stories)})
    return combined


# --- comparing versions ------------------------------------------------------

def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _number_key(value: str) -> str:
    return re.sub(r"[^0-9.]", "", value).strip(".")


# "KUALA LUMPUR, Nov 21 (Bernama) --" or "LIMA:" at the start of the story text.
# Bernama also puts a byline first: "From Nabilah Saleh and Linda Khoo MANILA, Nov 18 (Bernama) --".
_LEADING_DATELINE = re.compile(
    r"^\s*(From [^()]{0,80}?\s)?[A-Z][A-Z .'-]{2,40}(,\s*[A-Z][a-z]{2,8}\.? \d{1,2})?\s*(\([A-Za-z]+\))?\s*(:|--|—)\s*")
_NEXT_WORD = re.compile(r"[ -]*([a-z][a-z-]*)")
_UNITS = re.compile(r"%|per cent|percent|million|billion|km|kg|sen|bil|mil", re.I)
_NOT_A_UNIT_WORD = {"a", "an", "the", "and", "or", "to", "of", "in", "at", "on", "for", "with", "by", "under",
                    "over", "from", "as", "is", "was", "were", "are", "has", "had", "have", "after", "before"}
MAX_QUOTE_CHARS = 110
# Runs of two or more capitalised words (people, places, organisations), also at a sentence start.
_NAME = re.compile(r"\b[A-Z][a-zA-Z'’-]+(?:\s+(?:bin|binti|of|de|al)?\s*[A-Z][a-zA-Z'’-]+)+")
_NOT_NAME_START = {"The", "A", "An", "In", "On", "At", "But", "And", "He", "She", "It", "They", "This", "That",
                   "His", "Her", "Their", "Its", "When", "While", "After", "Before", "As", "For", "From"}


def _clean_body(body: str) -> str:
    body = _PHOTO_CREDIT.sub(" ", body or "")
    # Text after a photo caption often starts with the dateline: "... (AFP pic) LIMA: ..."
    return _LEADING_DATELINE.sub("", body)


def _number_detail(text: str, match) -> str:
    """A number with enough words to make sense ("18 months", "RM50 million", "11 killed"),
    or "" when it would not mean anything on its own (a ranking, a stray figure)."""
    item = match.group(0).strip()
    if _UNITS.search(item) or item.upper().startswith(("RM", "US", "S$", "$")):
        return item
    # A precise figure (6.8, 1,884) is informative alone.
    if re.search(r"[.,]\d|\d{3,}", item):
        return item
    following = _NEXT_WORD.match(text, match.end())
    if following and following.group(1) not in _NOT_A_UNIT_WORD:
        return f"{item} {following.group(1)}"
    return ""   # a bare small number (a ranking, a stray figure) means nothing on its own


def _details(body: str) -> List[str]:
    """Checkable details in a version's story text: numbers and amounts, quotes, names."""
    found, seen = [], set()

    def add(item: str):
        item = re.sub(r"[’']s$", "", item.strip(" ,.;:"))
        key = item.lower()
        if len(item) >= 2 and key not in seen:
            seen.add(key)
            found.append(item)

    for match in _NUMBER.finditer(body):
        if any(ch.isdigit() for ch in match.group(0)):
            detail = _number_detail(body, match)
            if detail:
                add(detail)
    for match in _QUOTE.finditer(body):
        quote = match.group(1).strip()
        if len(quote) > MAX_QUOTE_CHARS:
            quote = quote[:MAX_QUOTE_CHARS].rsplit(" ", 1)[0] + "…"
        add("“" + quote + "”")
    for match in _NAME.finditer(body):
        words = match.group(0).split()
        while words and words[0] in _NOT_NAME_START:
            words = words[1:]
        name = " ".join(words)
        # Multi-word names are the informative ones; all-capitals words are datelines, not names.
        if len(words) >= 2 and not re.search(r"\b[A-Z]{3,}\b", name):
            add(name)
    return found


def distinctive_details(versions: Dict[str, tuple]) -> Dict[str, List[str]]:
    """For each version (id -> (headline, story text)), the details from its story
    text that no other version mentions in its headline or text."""
    bodies = {key: _clean_body(body) for key, (_, body) in versions.items()}
    full = {key: f"{title} {bodies[key]}" for key, (title, _) in versions.items()}
    normalised = {key: _normalise(text) for key, text in full.items()}
    numbers = {key: {_number_key(m.group(0)) for m in _NUMBER.finditer(text) if any(c.isdigit() for c in m.group(0))}
               for key, text in full.items()}
    result = {}
    for key in versions:
        others = [normalised[k] for k in versions if k != key]
        other_numbers = set().union(*(numbers[k] for k in versions if k != key)) if len(versions) > 1 else set()
        unique = []
        for item in _details(bodies[key]):
            is_number = item[:1].isdigit() or item.upper().startswith(("RM", "US", "S$", "$"))
            if is_number:
                if _number_key(item.split()[0]) in other_numbers:
                    continue
            elif any(_normalise(item) in other for other in others):
                continue
            unique.append(item)
            if len(unique) >= MAX_DETAILS_PER_VERSION:
                break
        result[key] = unique
    return result


def version_text(article) -> tuple:
    """(headline, story text) of a version, as stored."""
    return article.title or "", _body(article.description or "", article.content_excerpt or "")
