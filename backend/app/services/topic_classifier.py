from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import logging
import re

logger = logging.getLogger(__name__)

MAX_CATEGORIES_PER_ARTICLE = 3

# Publishers file articles under sections, which show in the link
# (nst.com.my/sports/..., freemalaysiatoday.com/category/business/...) or, for
# Bernama, at the start of the headline ("Sport : ..."). A section is a much
# more reliable topic signal than a single word in the text.
SECTION_TOPICS = {"sports": "Sports", "sport": "Sports", "business": "Business", "money": "Business",
                  "politics": "Politics", "nation": "Local Malaysia News", "regional": "Local Malaysia News",
                  "malaysia": "Local Malaysia News", "showbiz": "Entertainment"}
# NST tags some headlines in its own way: "#SHOWBIZ: ...".
_HASHTAG_SECTION = re.compile(r"^\s*#([A-Za-z]+)\s*:")
_HEADLINE_SECTION = re.compile(r"^\s*([A-Za-z &]{3,25})\s:\s")


class TopicClassifierService:
    def __init__(self):
        # Keywords for each topic; the keys are the category names shown in
        # the UI. Matching uses whole words (plurals included) so short
        # keywords like "AI" don't match inside "said" or "detail".
        #
        # "weak" keywords are common in news about other subjects ("a team of
        # firefighters", "police said", "the minister visited"): one weak word
        # in the body is not enough to add a topic, but a weak word in the
        # headline, two different weak words, or any strong word is.
        self.topic_keywords = {
            "Local Malaysia News": {
                "strong": ["malaysia", "malaysian", "kuala lumpur", "putrajaya", "selangor", "johor", "penang",
                           "sabah", "sarawak", "perak", "kedah", "kelantan", "terengganu", "pahang",
                           "negeri sembilan", "negri sembilan", "melaka", "malacca", "perlis", "labuan", "ipoh",
                           "kuching", "kota kinabalu", "shah alam", "petaling jaya", "seremban", "johor bahru",
                           "alor setar", "kuantan", "kota bharu", "kuala terengganu", "miri", "sibu", "sandakan",
                           "tawau", "klang", "cyberjaya", "langkawi"],
                "weak": []},
            "Crime": {
                "strong": ["crime", "criminal", "murder", "murdered", "robbery", "robbed", "theft", "stolen", "steal",
                           "arrest", "arrested", "jail", "prison", "sentenced", "convicted", "trafficking", "assault",
                           "kidnap", "kidnapping", "fraud", "scam", "smuggling", "homicide", "syndicate", "burglary",
                           "extortion", "molest", "rape", "stabbed", "shooting", "gunman", "drug bust", "corruption",
                           "bribery", "money laundering"],
                "weak": ["police", "court", "charged", "victim", "suspect", "investigation", "detained", "custody",
                         "gang", "abuse", "raid"]},
            "Technology": {
                "strong": ["technology", "software", "hardware", "artificial intelligence", "machine learning",
                           "gadget", "smartphone", "startup", "semiconductor", "cybersecurity"],
                "weak": ["tech", "computer", "internet", "app", "digital", "chip"]},
            "Business": {
                "strong": ["business", "economy", "stock", "investment", "shares", "bursa", "earnings", "revenue"],
                "weak": ["finance", "market", "company", "industry", "trade"]},
            "Politics": {
                "strong": ["politics", "political", "election", "senate", "parliament", "cabinet", "parti",
                           "lawmaker", "opposition", "coalition", "prime minister", "foreign minister", "diplomatic",
                           "sanctions", "ceasefire", "treaty", "asean", "united nations", "nato"],
                "weak": ["government", "policy", "minister", "president", "summit", "military", "war", "trump",
                         "putin", "xi"]},
            "Sports": {
                "strong": ["sport", "football", "basketball", "tennis", "badminton", "squash", "olympics",
                           "tournament", "championship", "league", "goal", "striker", "coach", "athlete"],
                "weak": ["match", "team", "player", "final", "medal"]},
            "Health": {
                "strong": ["health", "medical", "medicine", "disease", "virus", "vaccine", "nutrition", "dengue",
                           "flu", "influenza"],
                "weak": ["hospital", "patient", "fitness", "doctor", "outbreak"]},
            "AI": {
                "strong": ["artificial intelligence", "machine learning", "deep learning", "neural network",
                           "chatbot", "generative ai", "large language model"],
                "weak": ["ai"]},
            "Entertainment": {
                "strong": ["entertainment", "movie", "film", "celebrity", "hollywood", "bollywood", "concert"],
                "weak": ["music", "actress", "actor", "singer", "drama"]},
            "Finance": {
                "strong": ["banking", "loan", "mortgage", "insurance", "interest rate", "inflation", "ringgit"],
                "weak": ["bank", "credit", "fund"]},
        }

        def pattern(keyword):
            return re.compile(r"\b" + re.escape(keyword.lower()) + r"(?:s|es)?\b")

        self._keyword_patterns = {
            topic: [(k, pattern(k), strength) for strength in ("strong", "weak") for k in groups[strength]]
            for topic, groups in self.topic_keywords.items()
        }

    @staticmethod
    def section_topic(url: Optional[str], title: str = "") -> Tuple[Optional[str], bool]:
        """The topic named by the publisher's section, and whether a section was found.
        A known section that is not Sports/Business/Politics (e.g. "nation", "world")
        returns (None, True)."""
        tag = _HASHTAG_SECTION.match(title or "")
        if tag and tag.group(1).lower() in SECTION_TOPICS:  # NST: "#SHOWBIZ: ..."
            return SECTION_TOPICS[tag.group(1).lower()], True
        match = _HEADLINE_SECTION.match(title or "")
        if match:                                       # Bernama: "Sport : ...", "General : ..."
            return SECTION_TOPICS.get(match.group(1).strip().lower()), True
        try:
            parts = [p.lower() for p in urlparse(url or "").path.split("/") if p]
        except ValueError:
            return None, False
        if parts and parts[0] in ("category", "news") and len(parts) > 1:
            parts = parts[1:]
        if len(parts) >= 2 and not parts[0].isdigit():  # a section, not just a slug
            return SECTION_TOPICS.get(parts[0]), True
        return None, False

    def _score_topics(self, title: str, body: str) -> Dict[str, int]:
        """Score per topic; 0 when the evidence is only one weak word in the body."""
        title_l, body_l = (title or "").lower(), (body or "").lower()
        scores = {}
        for topic, patterns in self._keyword_patterns.items():
            strong = weak = 0
            in_title = False
            for _keyword, pat, strength in patterns:
                hit_title = bool(pat.search(title_l))
                if hit_title or pat.search(body_l):
                    if strength == "strong":
                        strong += 1
                    else:
                        weak += 1
                    in_title = in_title or hit_title
            enough = strong >= 1 or weak >= 2 or (weak == 1 and in_title)
            scores[topic] = (strong * 2 + weak + (2 if in_title else 0)) if enough else 0
        return scores

    def classify_topics(self, title: str, description: str = "", content: str = "",
                        max_categories: int = MAX_CATEGORIES_PER_ARTICLE, url: Optional[str] = None) -> List[str]:
        """Return up to `max_categories` topics, the publisher's own section
        first (when it names one), then by keyword evidence. Falls back to
        ["General"] when nothing matches."""
        scores = self._score_topics(title, f"{description} {content}")
        section, known = self.section_topic(url, title)
        if known and section != "Sports":
            # The publisher filed it outside Sports: sports words in a news story
            # ("a team of officers", "the final report") need stronger evidence.
            sports = [k for k, pat, s in self._keyword_patterns["Sports"]
                      if s == "strong" and pat.search(f"{title} {description} {content}".lower())]
            if len(sports) < 2:
                scores["Sports"] = 0
        ranked = sorted((t for t, score in scores.items() if score > 0 and t != section),
                        key=lambda t: scores[t], reverse=True)
        if section:
            ranked.insert(0, section)
        return ranked[:max_categories] if ranked else ["General"]

    def classify_topic(self, title: str, description: str = "", content: str = "") -> str:
        """Backward-compatible single-topic classification (returns the
        single best-matching topic). Prefer classify_topics() for new code."""
        return self.classify_topics(title, description, content, max_categories=1)[0]
