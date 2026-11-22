"""Explainable credibility cues, not fact checking or a truth probability."""
from datetime import datetime
from urllib.parse import urlparse
import re
from app.services.storage import storage_service
from app.services.content_analyzer import analyze_content

SCORE_VERSION = "content-analysis-v4"
# The publisher's reputation counts for 30%; 20% comes from checking how the
# article itself is reported (content_analyzer); other-publisher coverage is
# a supporting signal (20%).
WEIGHTS = {"source_reputation": .30, "content_quality": .20, "corroboration": .20,
           "metadata_completeness": .15, "sentiment_neutrality": .15}


def publisher_domain(url):
    try:
        host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""
    for domain in ("freemalaysiatoday.com", "nst.com.my", "bernama.com"):
        if host == domain or host.endswith("." + domain):
            return domain
    return host


def related_title(first, second):
    """Candidate matching only; similar headlines do not establish agreement."""
    words = lambda s: set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {
        "the", "and", "for", "with", "from", "that", "this", "says", "after", "into"}
    a, b = words(first), words(second)
    return bool(a and b and len(a & b) >= 3 and len(a & b) / max(len(a), len(b)) >= .6)


class TrustScorerService:
    def __init__(self):
        self.weights = WEIGHTS.copy()

    extract_domain = staticmethod(publisher_domain)

    def calculate_source_reputation(self, source_domain, source_cred=None):
        return min(1., max(0., source_cred.credibility_score / 100)) if source_cred else .5

    async def calculate_source_reputation_async(self, domain):
        record = await storage_service.get_source_credibility_by_domain(domain)
        return self.calculate_source_reputation(domain, record)

    def independent_reports(self, article, candidates):
        current = publisher_domain(article.get("url"))
        reports = {}
        for candidate in sorted(candidates, key=lambda item: item.get("url", "")):
            domain = publisher_domain(candidate.get("url"))
            if domain and domain != current and domain not in reports and related_title(article.get("title"), candidate.get("title")):
                reports[domain] = candidate
        return reports

    def calculate_metadata_completeness(self, article):
        return sum(weight for key, weight in {"author": .25, "published_date": .25,
                   "source": .15, "description": .20, "url": .15}.items() if article.get(key) and not (key == "published_date" and article.get("publication_date_inferred")))

    def calculate_sentiment_neutrality(self, article):
        tone = (article.get("tone_label") or "").lower()
        sentiment = (article.get("sentiment") or "").lower()
        if "neutral" in tone or "objective" in tone or sentiment == "neutral":
            return 1.
        return .7 if "mild" in tone else .4

    async def calculate_trust_score(self, article, similar_articles=None):
        reports = self.independent_reports(article, similar_articles or [])
        reputation = await self.calculate_source_reputation_async(publisher_domain(article.get("url")))
        reputations = [await self.calculate_source_reputation_async(domain) for domain in reports]
        corroboration = (.7 * sum(reputations) / len(reputations) + .3 * min(len(reputations), 4) / 4) if reputations else 0.
        content = analyze_content(article)
        components = {"source_reputation": reputation, "content_quality": content["score"],
                      "corroboration": corroboration,
                      "metadata_completeness": self.calculate_metadata_completeness(article),
                      "sentiment_neutrality": self.calculate_sentiment_neutrality(article)}
        score = round(min(95., 100 * sum(self.weights[key] * value for key, value in components.items())), 2)
        label = "High trust" if score >= 80 else "Medium trust" if score >= 60 else "Low trust" if score >= 40 else "Needs verification"
        evidence = [{"source": item.get("source") or domain, "domain": domain,
                     "url": item["url"], "title": item.get("title", ""),
                     "summary": item.get("summary") or item.get("description") or "",
                     "sentiment": item.get("sentiment"), "toneLabel": item.get("tone_label")}
                    for domain, item in reports.items()]
        explanation = (f"{len(evidence)} distinct other publisher(s) with a similar headline. "
                       "Content quality checks how the article is reported (sources, concrete details, "
                       "headline and wording), not whether it is true. "
                       "Reputation values are configured priors; matching reports may repeat the same original source. "
                       "This heuristic is not a fact check or a probability of truth.")
        return {"trust_score": score, "trust_label": label, "trust_explanation": explanation,
                "trust_components": components, "trust_weights": self.weights.copy(),
                "trust_evidence": evidence, "trust_content_checks": content["checks"],
                "trust_version": SCORE_VERSION,
                "trust_scored_at": datetime.utcnow()}

    async def cold_start_fallback(self, article):
        return await self.calculate_trust_score(article, [])
