"""Rule-based checks on how an article itself is reported (part of the trust score).

Four checks, each scored 0-1 with a plain-language reason:
  attribution        35%  says where the information comes from
  specific_facts     25%  concrete, checkable details (numbers, dates, names)
  headline_honesty   20%  headline matches the story, no clickbait
  verified_language  20%  does not lean on rumour ("viral", "netizens claim")

Only the stored text is read (headline, feed description and content excerpt),
so re-scoring an article later always gives the same result. Feeds differ in
how much text they send (Bernama sends one sentence), so with little text the
attribution and fact checks move toward a neutral middle instead of treating a
short story as badly reported.

This judges how a story is reported, not whether it is true.
"""
import re
from typing import Dict, List

CHECK_WEIGHTS = {"attribution": .35, "specific_facts": .25,
                 "headline_honesty": .20, "verified_language": .20}
CHECK_LABELS = {"attribution": "Attribution", "specific_facts": "Specific facts",
                "headline_honesty": "Headline honesty", "verified_language": "Verified language"}

NEUTRAL = .6          # score used when there is too little text to judge
FULL_TEXT_WORDS = 60  # from this many words the text-based checks count in full

# --- attribution -----------------------------------------------------------
_REPORTING = re.compile(
    r"\b(said|says|told|stated|announced|confirmed|added|explained|noted|"
    r"urged|warned|denied|revealed|clarified|reported)\b", re.I)
_STATEMENT = re.compile(
    r"\b(according to|in a statement|in a press conference|at a press conference|"
    r"press release|in a post on|in a filing|official data|figures from)\b", re.I)
# A quotation of three or more words in straight or curly quotes.
_QUOTE = re.compile(r"[\"“]([^\"”]{12,}?)[\"”]")
# Wire credit or dateline at the start: "KUALA LUMPUR, Nov 17 (Bernama) --", "IPOH:", "(Reuters)".
# Also found after a photo caption: "Tankers ... (AFP pic) SINGAPORE: US officials ..."
_DATELINE = re.compile(r"(?:^|[.!?)\]]\s+|\s{2,})[A-Z][A-Z .'-]{2,40}(,\s*[A-Z][a-z]{2,8}\.? \d{1,2})?\s*(\([A-Za-z]+\))?\s*(:|--|—)")
_WIRE = re.compile(r"\((Bernama|Reuters|AFP|AP|Xinhua|Kyodo|Anadolu)\)(?!\s*pic)", re.I)
_PHOTO_CREDIT = re.compile(r"\([^()]{0,40}\bpics?\)", re.I)

# --- specific facts --------------------------------------------------------
_NUMBER = re.compile(r"\b(RM|USD|US\$|S\$|\$)?\s?\d[\d,.]*\s?(%|per cent|percent|million|billion|km|kg|sen)?", re.I)
_DATE_WORD = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|yesterday|today|"
    r"jan(uary)?|feb(ruary)?|march|apr(il)?|june?|july?|aug(ust)?|sept?(ember)?|"
    r"oct(ober)?|nov(ember)?|dec(ember)?)\b", re.I)
# Runs of capitalised words (names of people, places, organisations).
_PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-zA-Z'’-]+(?:\s+(?:bin|binti|of|de|al)?\s*[A-Z][a-zA-Z'’-]+)*")
FACTS_FOR_FULL_SCORE = 7  # details per 60 words that earn full marks

# --- headline --------------------------------------------------------------
_CLICKBAIT = re.compile(
    r"\b(shocking|shocked|you won'?t believe|jaw-?dropping|mind-?blowing|unbelievable|"
    r"what happens next|goes viral|this is why|the reason why|insane|epic fail|"
    r"must see|must watch|stunning truth|exposed)\b", re.I)
_CATEGORY_PREFIX = re.compile(r"^[A-Za-z &]{3,25}\s:\s")  # Bernama: "General : ..."
_STOP = set(("the a an and or but in on at to for of with by is are was were be been from that this "
             "these those it its as into over after amid says said say will has have had not than "
             "their they them his her who what when where why how new").split())

# --- verified language -----------------------------------------------------
_RUMOUR = re.compile(
    r"\b(viral|netizens?|rumou?rs?|unconfirmed|unverified|speculation|speculated|"
    r"it is believed|it is understood|sources said|a source said|purportedly|"
    r"reportedly|claimed online|social media users claim\w*)\b", re.I)


def _words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def _body(description: str, excerpt: str) -> str:
    """Description and excerpt often repeat each other; keep distinct text once."""
    description, excerpt = (description or "").strip(), (excerpt or "").strip()
    if description and excerpt and (description[:80] in excerpt or excerpt[:80] in description):
        return max(description, excerpt, key=len)
    return " ".join(part for part in (description, excerpt) if part)


def _toward_neutral(raw: float, words: int) -> float:
    """With little text, move a text-based score toward the neutral middle."""
    share = min(1., words / FULL_TEXT_WORDS)
    return NEUTRAL + (raw - NEUTRAL) * share


def check_attribution(body: str, words: int) -> Dict:
    text = _PHOTO_CREDIT.sub(" ", body)
    found = []
    if _REPORTING.search(text):
        found.append("a reporting verb (\"" + _REPORTING.search(text).group(0).lower() + "\")")
    if _STATEMENT.search(text):
        found.append("\"" + _STATEMENT.search(text).group(0).lower() + "\"")
    if _QUOTE.search(text):
        found.append("a direct quote")
    if _DATELINE.search(text.lstrip()[:300]) or _WIRE.search(text):
        found.append("a dateline or news-agency credit")
    raw = min(1., .25 + .3 * len(found))
    score = _toward_neutral(raw, words)
    reason = ("Sources shown: " + ", ".join(found) + "." if found
              else "No source is named for the information.")
    return {"score": score, "reason": reason}


def check_specific_facts(body: str, words: int) -> Dict:
    text = _PHOTO_CREDIT.sub(" ", body)
    numbers = [m.group(0).strip() for m in _NUMBER.finditer(text) if any(ch.isdigit() for ch in m.group(0))]
    dates = _DATE_WORD.findall(text)
    names = {m.group(0) for m in _PROPER.finditer(text)} - {"The", "A", "An", "In", "On", "He", "She", "It", "They"}
    count = len(numbers) + len(dates) + len(names)
    per_60 = count * FULL_TEXT_WORDS / max(words, 20)
    raw = min(1., .2 + .8 * per_60 / FACTS_FOR_FULL_SCORE)
    score = _toward_neutral(raw, words)
    parts = [f"{len(numbers)} number(s)" if numbers else "", f"{len(dates)} date(s)" if dates else "",
             f"{len(names)} name(s) of people, places or organisations" if names else ""]
    parts = [p for p in parts if p]
    reason = ("Concrete details: " + ", ".join(parts) + "." if parts
              else "No concrete details such as numbers, dates or names.")
    return {"score": score, "reason": reason}


def check_headline(title: str, body: str) -> Dict:
    headline = _CATEGORY_PREFIX.sub("", title or "").strip()
    score, issues = 1., []
    bait = sorted({m.group(0).lower() for m in _CLICKBAIT.finditer(headline)})
    if bait:
        score -= min(.6, .3 * len(bait))
        issues.append("clickbait wording (" + ", ".join(f'"{b}"' for b in bait) + ")")
    if "!" in headline:
        score -= .2
        issues.append("an exclamation mark")
    shouting = [w for w in re.findall(r"\b[A-Z]{5,}\b", headline)]
    if len(shouting) >= 2:
        score -= .2
        issues.append("words in capitals")
    if headline.endswith("?"):
        score -= .1
        issues.append("a question headline")
    key_words = {w.lower() for w in _words(headline) if len(w) >= 4 and w.lower() not in _STOP}
    body_lower = (body or "").lower()
    if key_words and body_lower:
        found = sum(1 for w in key_words if w[:5] in body_lower)
        overlap = found / len(key_words)
        if overlap < .5:
            score -= .3 * (1 - overlap / .5)
            issues.append(f"only {found} of {len(key_words)} key headline words appear in the story")
    score = max(0., score)
    reason = ("Headline has " + "; ".join(issues) + "." if issues
              else "Headline matches the story, with no clickbait.")
    return {"score": score, "reason": reason}


def check_verified_language(title: str, body: str) -> Dict:
    terms = sorted({m.group(0).lower() for m in _RUMOUR.finditer(f"{title} {body}")})
    score = max(0., 1 - .25 * len(terms))
    reason = ("Relies on unverified wording: " + ", ".join(f'"{t}"' for t in terms) + "." if terms
              else "No rumour or unverified wording.")
    return {"score": score, "reason": reason}


def analyze_content(article: Dict) -> Dict:
    """Return the content score (0-1) and the result of each check."""
    title = article.get("title") or ""
    excerpt = article.get("content_excerpt")
    if excerpt is None:
        excerpt = (article.get("content") or "")[:2000]
    body = _body(article.get("description") or "", excerpt)
    words = len(_words(body))
    results = {
        "attribution": check_attribution(body, words),
        "specific_facts": check_specific_facts(body, words),
        "headline_honesty": check_headline(title, body),
        "verified_language": check_verified_language(title, body),
    }
    checks = [{"key": key, "label": CHECK_LABELS[key], "weight": CHECK_WEIGHTS[key],
               "score": round(result["score"], 3), "reason": result["reason"]}
              for key, result in results.items()]
    score = sum(CHECK_WEIGHTS[c["key"]] * c["score"] for c in checks)
    return {"score": round(score, 4), "checks": checks, "words": words}
