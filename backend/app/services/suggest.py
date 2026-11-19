"""Keyword suggestions for the search box.

Suggestions come from recent headlines, so they are words and short phrases
that really appear in the news ("climate change", "Anwar"), ranked by how
often they appear. With an empty box, the most common topics of the last
two days are returned as "trending".
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Iterable, List

from app.services.storage import storage_service

MAX_SUGGESTIONS = 8
SCAN_LIMIT = 400          # recent headlines looked at per request
TRENDING_HOURS = 48

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "he", "her", "his", "in",
    "into", "is", "it", "its", "of", "on", "or", "over", "says", "said", "she", "that", "the", "their", "they",
    "this", "to", "up", "was", "were", "will", "with", "after", "amid", "against", "about", "more", "new", "not",
    "out", "than", "who", "why", "how", "what", "when", "where", "can", "could", "should", "would", "may", "must",
    "been", "being", "but", "all", "also", "only", "just", "still", "two", "one", "three", "first", "last",
    "year", "years", "day", "days", "week", "says", "told", "get", "gets", "set", "sets", "make", "makes",
    # Bernama headline prefixes ("General : ...") and other filler
    "general", "business", "sports", "world", "politics", "news", "watch", "video", "live", "updated",
}
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-.]*[A-Za-z0-9]|[A-Za-z0-9]")
_PREFIX = re.compile(r"^\s*[A-Za-z &]+\s:\s+")       # "General : " at the start of Bernama titles


def tokens(title: str) -> List[str]:
    """Words of a headline, without the "General : " prefix or possessive 's."""
    return [re.sub(r"['’]s$", "", t) for t in _TOKEN.findall(_PREFIX.sub("", title or ""))]


def _keep(word: str) -> bool:
    w = word.lower()
    return len(w) > 1 and w not in STOP_WORDS


def _stem(word: str) -> str:
    """Group plural and singular ("floods" with "flood")."""
    w = word.lower()
    return w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w


class _Casing:
    """Decide how to show each word. Many headlines capitalise every word,
    so only sentence-case headlines count as evidence of a proper noun."""

    def __init__(self):
        self.caps = Counter()
        self.seen = Counter()
        self.upper = Counter()
        self.total = Counter()

    def learn(self, toks: List[str]):
        long_words = [t for t in toks if len(t) > 3 and t.isalpha()]
        title_case = long_words and sum(t[0].isupper() for t in long_words) / len(long_words) > 0.6
        for i, t in enumerate(toks):
            w = t.lower()
            self.total[w] += 1
            if t.isupper() and len(t) > 1 and any(c.isalpha() for c in t):
                self.upper[w] += 1
            if i == 0 or title_case:
                continue
            self.seen[w] += 1
            if t[0].isupper():
                self.caps[w] += 1

    def show(self, w: str) -> str:
        if len(w) <= 6 and self.upper[w] >= 2 and self.upper[w] / self.total[w] >= 0.6:
            return w.upper()                      # COP31, HSBC, MACC
        if self.seen[w] and self.caps[w] / self.seen[w] >= 0.7:
            return w[:1].upper() + w[1:]          # Anwar, Johor, Ringgit
        return w


def build_suggestions(titles: Iterable[str], query: str, limit: int = MAX_SUGGESTIONS) -> List[Dict]:
    """Complete the last word of `query` (and offer two-word phrases) from headlines.
    Earlier words in the query are kept in front of each suggestion."""
    words = query.lower().split()
    if not words:
        return []
    ends_with_space = query.endswith(" ")
    context = words if ends_with_space else words[:-1]
    prefix = "" if ends_with_space else words[-1]

    counts: Counter = Counter()
    forms: Dict[str, Counter] = defaultdict(Counter)
    casing = _Casing()
    for title in titles:
        toks = tokens(title)
        casing.learn(toks)
        low = [t.lower() for t in toks]
        if any(c not in low and _stem(c) not in map(_stem, low) for c in context):
            continue
        seen = set()
        for i, w in enumerate(low):
            if prefix:
                if not w.startswith(prefix) or w in context:
                    continue
                start = i
            else:
                # after a finished word, suggest the word that follows it
                if not context or _stem(w) != _stem(context[-1]) or i + 1 >= len(low):
                    continue
                start = i + 1
            phrases = [low[start:start + 1]]
            # two-word phrases only while completing a word (after a space, just the next word)
            if prefix and start + 1 < len(low) and _keep(low[start + 1]):
                phrases.append(low[start:start + 2])
            for ph in phrases:
                if not _keep(ph[0]) or any(t in context for t in ph):
                    continue
                key = " ".join(_stem(t) for t in ph)
                if key in seen:
                    continue
                seen.add(key)
                counts[key] += 1
                forms[key][" ".join(ph)] += 1

    lead = [casing.show(w) for w in context]
    results = []
    for key, n in counts.most_common():
        # a two-word phrase must appear at least twice to be worth suggesting
        if " " in key and n < 2:
            continue
        form = forms[key].most_common(1)[0][0]
        text = " ".join(lead + [casing.show(w) for w in form.split()])
        if text.lower() == query.strip().lower():
            continue
        results.append({"text": text, "count": n})
        if len(results) >= limit:
            break
    return results


# Words that are common in every headline batch but say nothing about the topic.
TRENDING_FILLER = {
    "malaysia", "malaysian", "malaysians", "kuala", "lumpur", "million", "billion", "per", "cent", "percent",
    "rm", "us", "govt", "government", "state", "people", "country", "national", "says", "say", "time",
    "today", "next", "back", "down", "off", "under", "between", "before", "during", "while", "despite",
}


def trending(titles: Iterable[str], limit: int = MAX_SUGGESTIONS) -> List[Dict]:
    """Most common topic words and two-word phrases in recent headlines."""
    words, pairs = Counter(), Counter()
    pair_forms: Dict[str, Counter] = defaultdict(Counter)
    word_forms: Dict[str, Counter] = defaultdict(Counter)
    casing = _Casing()
    useful = lambda w: _keep(w) and w not in TRENDING_FILLER and not w.isdigit() and len(w) > 2
    for title in titles:
        toks = tokens(title)
        casing.learn(toks)
        low = [t.lower() for t in toks]
        for w in set(low):
            if useful(w):
                words[_stem(w)] += 1
                word_forms[_stem(w)][w] += 1
        for a, b in set(zip(low, low[1:])):
            if useful(a) and useful(b):
                key = f"{_stem(a)} {_stem(b)}"
                pairs[key] += 1
                pair_forms[key][f"{a} {b}"] += 1
    results = []
    # a phrase that appears often enough replaces its single words
    covered = set()
    for key, n in pairs.most_common():
        if n < 3 or len(results) >= limit // 2:
            break
        results.append((n, " ".join(casing.show(w) for w in pair_forms[key].most_common(1)[0][0].split())))
        covered.update(key.split())
    for key, n in words.most_common():
        if len(results) >= limit:
            break
        if key in covered or n < 2:
            continue
        results.append((n, casing.show(word_forms[key].most_common(1)[0][0])))
    results.sort(key=lambda r: -r[0])
    return [{"text": t, "count": n} for n, t in results]


async def suggest(query: str) -> Dict:
    query = (query or "")[:60]
    col = storage_service.articles
    base = {"processing_status": "completed"}
    if not query.strip():
        since = datetime.utcnow() - timedelta(hours=TRENDING_HOURS)
        cursor = col.find({**base, "published_date": {"$gte": since}}, {"title": 1}).sort("published_date", -1).limit(SCAN_LIMIT)
        titles = [doc.get("title", "") async for doc in cursor]
        return {"kind": "trending", "suggestions": trending(titles)}
    words = query.lower().split()
    filters = [{"title": {"$regex": r"\b" + re.escape(w), "$options": "i"}} for w in words[:5]]
    cursor = col.find({**base, "$and": filters}, {"title": 1}).sort("published_date", -1).limit(SCAN_LIMIT)
    titles = [doc.get("title", "") async for doc in cursor]
    return {"kind": "completions", "suggestions": build_suggestions(titles, query)}
