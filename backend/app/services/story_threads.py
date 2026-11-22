"""Developing stories: links a story's later updates into one timeline.

story_grouper puts one event's versions from different publishers together
(the same story). This module goes one step further: when news develops over
hours or days ("Form Three student found dead" -> "PM orders probe" ->
"cause of death confirmed"), those stories share a thread_id, so the feed can
show one card for the whole developing story and the article page can show
its timeline.

A later article is an update of an earlier one when, within MAX_GAP:
  - they share a rare name (a person, place or organisation that appears in
    few recent articles), and
  - their headlines share rare words beyond that name: two names plus one
    word, or one name plus two words.
Common names ("Anwar Ibrahim", "Bank Negara Malaysia") and an outlet's
several pieces from one event published at the same time do not link. A
timeline with three or more articles is joined only by an article that links
to at least two of them, so loosely related stories do not chain together.
These rules were tuned on the stored articles (Nov 2026).
"""
import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from app.services.storage import storage_service
from app.services.story_grouper import _NAME, _NOT_NAME_START, _clean_body, version_text
from app.services.trust_scorer import _title_words, publisher_domain, related_title

logger = logging.getLogger(__name__)

MAX_GAP = timedelta(days=4)               # between an update and what it follows
TERMS_WINDOW = timedelta(days=7)          # articles used to decide which names/words are rare
RARE_NAME_SHARE = 0.015                   # a name in at most 1.5% of recent articles is rare
RARE_WORD_SHARE = 0.008                   # a headline word in at most 0.8% is rare
RARE_MIN_COUNT = 4                        # ...and anything in up to 4 articles (few stored articles)
SAME_OUTLET_GAP = timedelta(hours=1)      # one outlet's pieces published together are not updates
BACKFILL_MIGRATION = "story-threads-v1"


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def article_names(article) -> Set[str]:
    """Names of people, places and organisations in an article's story text."""
    _, body = version_text(article)
    names = set()
    for match in _NAME.finditer(_clean_body(body)):
        words = match.group(0).split()
        while words and words[0] in _NOT_NAME_START:
            words = words[1:]
        name = " ".join(words)
        if len(words) >= 2 and not re.search(r"\b[A-Z]{3,}\b", name):
            names.add(re.sub(r"[’']s?$", "", name.lower()))
    return names


class ThreadIndex:
    """Recent articles with their names and headline words, for finding updates."""

    def __init__(self, articles: List, thread_of: Optional[Dict[str, str]] = None):
        self.terms = {}
        self.names_df, self.words_df = Counter(), Counter()
        for article in articles:
            self._count(article)
        self.articles = []                   # articles that later ones can link to (oldest first)
        self.thread_of = dict(thread_of or {})
        self.thread_size = Counter(self.thread_of.values())

    def _count(self, article):
        if article.id in self.terms:
            return self.terms[article.id]
        terms = (article_names(article), _title_words(article.title))
        self.terms[article.id] = terms
        self.names_df.update(terms[0])
        self.words_df.update(terms[1])
        return terms

    def add(self, article, thread_id: str):
        self._count(article)
        self.articles.append(article)
        self.thread_of[article.id] = thread_id
        self.thread_size[thread_id] += 1

    def _rare(self, article):
        names, words = self._count(article)
        total = len(self.terms)
        name_limit = max(RARE_NAME_SHARE * total, RARE_MIN_COUNT)
        word_limit = max(RARE_WORD_SHARE * total, RARE_MIN_COUNT)
        return ({n for n in names if self.names_df[n] <= name_limit},
                {w for w in words if self.words_df[w] <= word_limit and not w.isdigit()})

    def is_update(self, earlier, later) -> bool:
        gap = later.published_date - earlier.published_date
        if gap < timedelta(0) or gap > MAX_GAP or related_title(earlier.title, later.title):
            return False                     # same event (story_grouper) or too far apart
        if publisher_domain(earlier.url) == publisher_domain(later.url) and gap < SAME_OUTLET_GAP:
            return False
        (names_a, words_a), (names_b, words_b) = self._rare(earlier), self._rare(later)
        names, words = names_a & names_b, words_a & words_b
        tokens = {_stem(t) for n in names for t in re.findall(r"[a-z0-9]+", n)}
        initials = {"".join(t[0] for t in re.findall(r"[a-z0-9]+", n)) for n in names}
        extra = {w for w in words if _stem(w) not in tokens and w not in initials}
        return (len(names) >= 2 and len(extra) >= 1) or (len(names) >= 1 and len(extra) >= 2)

    def best_thread(self, article) -> Optional[str]:
        counts = Counter()
        for earlier in self.articles:
            if earlier.id != article.id and earlier.id in self.thread_of and self.is_update(earlier, article):
                counts[self.thread_of[earlier.id]] += 1
        best, best_links = None, 0
        for thread_id, links in counts.items():
            needed = 1 if self.thread_size[thread_id] < 3 else 2
            if links >= needed and links > best_links:
                best, best_links = thread_id, links
        return best


async def build_index(now: Optional[datetime] = None) -> ThreadIndex:
    """Index of the last TERMS_WINDOW of articles (used during a collection run)."""
    since = (now or datetime.utcnow()) - TERMS_WINDOW
    recent = await storage_service.get_articles_since(since)
    index = ThreadIndex(recent)
    for article in recent:
        if article.thread_id:
            index.add(article, article.thread_id)
    return index


async def assign_thread(article, index: ThreadIndex) -> str:
    """Give `article` a thread id: its story's thread, the developing story it
    updates, or a new thread of its own."""
    peers = [p for p in await storage_service.get_articles_by_story(article.story_id or article.id) if p.id != article.id]
    thread_id = next((p.thread_id for p in peers if p.thread_id), None)   # one story, one thread
    if not thread_id:
        thread_id = index.best_thread(article) or article.story_id or article.id
    ids = [article.id] + [p.id for p in peers if p.thread_id != thread_id]
    await storage_service.set_thread(thread_id, ids)
    index.add(article, thread_id)
    return thread_id


async def backfill_once() -> int:
    """One time: put every stored article into a thread, oldest first.
    Returns how many articles belong to a developing story afterwards."""
    if await storage_service.migration_done(BACKFILL_MIGRATION):
        return 0
    articles = await storage_service.get_all_articles_oldest_first()
    index = ThreadIndex(articles)
    for article in articles:
        index.articles = [a for a in index.articles if article.published_date - a.published_date <= MAX_GAP]
        fresh = await storage_service.get_article_by_id(article.id)
        if fresh:
            await assign_thread(fresh, index)
    developing = await storage_service.count_articles_in_developing_stories()
    await storage_service.mark_migration_done(BACKFILL_MIGRATION, {"articles": len(articles), "in_developing": developing})
    logger.info(f"Linked stored articles into timelines ({developing} in developing stories).")
    return developing
