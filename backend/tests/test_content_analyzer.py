"""Content-quality checks used by the trust score (app/services/content_analyzer.py)."""
import pytest
from app.services.content_analyzer import CHECK_WEIGHTS, analyze_content
from app.services.trust_scorer import TrustScorerService

REPORTED = {
    "title": "Police arrest 3 suspects over RM2.5 million fraud in Johor Bahru",
    "description": "JOHOR BAHRU: Police arrested three suspects on Monday over a RM2.5 million investment fraud, "
                   "Johor police chief Datuk Ab Rahaman Arsad said in a statement.",
    "content_excerpt": "JOHOR BAHRU: Police arrested three suspects on Monday over a RM2.5 million investment fraud, "
                       "Johor police chief Datuk Ab Rahaman Arsad said in a statement. \"The suspects, aged 31 to 45, "
                       "were detained in Skudai and Tebrau,\" he said, adding that 42 victims had lodged reports since "
                       "March. The case is being investigated under Section 420 of the Penal Code.",
}
RUMOUR = {
    "title": "SHOCKING! You won't believe what netizens found in this viral video",
    "description": "A viral video is going around and netizens claim it shows something big. "
                   "It is believed the story is unconfirmed.",
    "content_excerpt": "",
}


def checks(article):
    return {c["key"]: c for c in analyze_content(article)["checks"]}


def test_weights_add_up():
    assert sum(CHECK_WEIGHTS.values()) == pytest.approx(1)


def test_well_reported_story_scores_high_with_reasons():
    result = analyze_content(REPORTED)
    found = checks(REPORTED)
    assert result["score"] >= .85
    assert "a direct quote" in found["attribution"]["reason"]
    assert "in a statement" in found["attribution"]["reason"]
    assert found["specific_facts"]["score"] >= .9
    assert found["headline_honesty"]["score"] == 1
    assert found["verified_language"]["score"] == 1


def test_rumour_and_clickbait_score_low():
    found = checks(RUMOUR)
    assert analyze_content(RUMOUR)["score"] < .55
    assert found["headline_honesty"]["score"] <= .3
    assert "clickbait" in found["headline_honesty"]["reason"]
    assert found["verified_language"]["score"] == 0
    assert '"netizens"' in found["verified_language"]["reason"]


def test_short_text_moves_toward_neutral_instead_of_failing():
    one_line = {"title": "Minister visits flood victims", "description": "The minister visited victims.",
                "content_excerpt": ""}
    found = checks(one_line)
    # Five words with no source would be 0.25 on full text; with this little text it stays near the middle.
    assert .5 < found["attribution"]["score"] < .6


def test_photo_caption_does_not_hide_dateline():
    article = {"title": "US treasury presses Singapore on sanctions",
               "description": "", "content_excerpt": "Tankers stop near Singapore. (AFP pic) SINGAPORE: US officials met "
               "government authorities this week over sanctions compliance."}
    assert "dateline" in checks(article)["attribution"]["reason"]
    assert "pic" not in checks(article)["attribution"]["reason"]


def test_stored_excerpt_is_used_so_rescoring_is_stable():
    raw = {**REPORTED, "content": REPORTED["content_excerpt"] + " Extra text not stored." * 200}
    stored = {**REPORTED}
    assert analyze_content(raw)["score"] == analyze_content(stored)["score"]


async def test_content_quality_changes_trust_score_by_its_weight(monkeypatch):
    import app.services.trust_scorer as trust_module
    scorer = TrustScorerService()
    article = {**REPORTED, "url": "https://example.test/a", "source": "Example", "sentiment": "Neutral"}
    monkeypatch.setattr(trust_module, "analyze_content", lambda a: {"score": 1., "checks": []})
    high = await scorer.calculate_trust_score(article)
    monkeypatch.setattr(trust_module, "analyze_content", lambda a: {"score": .5, "checks": []})
    low = await scorer.calculate_trust_score(article)
    assert high["trust_score"] - low["trust_score"] == pytest.approx(10)  # 20% weight x 0.5
