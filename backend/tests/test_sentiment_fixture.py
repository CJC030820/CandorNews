"""Validate synthetic evaluation data and classifier output, not perfect accuracy."""

import json
import math
from collections import Counter
from pathlib import Path

import pytest

from app.services.sentiment_analyzer import SentimentAnalyzerService
from scripts import evaluate_sentiment


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sentiment_headlines.json"
DATASET = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
EXAMPLES = DATASET["examples"]
LABELS = {"Positive", "Negative", "Neutral"}
TONES = {"Neutral / Objective", "Mildly Emotional", "Emotionally Charged"}


def test_fixture_documents_synthetic_unvalidated_labels():
    assert DATASET["schema_version"] == 1
    assert DATASET["synthetic"] is True
    assert "human review" in DATASET["annotation_method"]
    assert "fictional" in DATASET["intended_use"]


def test_fixture_has_exactly_100_headlines_per_label():
    assert len(EXAMPLES) == 300
    assert Counter(row["expected_sentiment"] for row in EXAMPLES) == {
        "Positive": 100, "Negative": 100, "Neutral": 100,
    }


def test_fixture_has_unique_stable_ids_and_nonempty_unique_headlines():
    assert {row["id"] for row in EXAMPLES} == {
        f"{prefix}-{number:03d}"
        for prefix in ("pos", "neg", "neu")
        for number in range(1, 101)
    }
    normalized = [" ".join(row["headline"].split()).casefold() for row in EXAMPLES]
    assert all(normalized)
    assert len(set(normalized)) == 300
    prefixes = {"Positive": "pos", "Negative": "neg", "Neutral": "neu"}
    assert all(row["id"].startswith(prefixes[row["expected_sentiment"]] + "-") for row in EXAMPLES)


def test_fixture_covers_ten_topics_equally_for_each_label():
    categories = {row["category"] for row in EXAMPLES}
    assert len(categories) == 10
    assert all(isinstance(category, str) and category.strip() for category in categories)
    assert Counter((row["category"], row["expected_sentiment"]) for row in EXAMPLES) == {
        (category, label): 10 for category in categories for label in LABELS
    }


@pytest.fixture(scope="module")
def analyzer():
    # VADER ships its lexicon with the package and needs no model download.
    return SentimentAnalyzerService()


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda row: row["id"])
def test_synthetic_headline_produces_valid_analysis(analyzer, example):
    result = analyzer.analyze_article_sentiment({"title": example["headline"]})
    assert set(result) == {"sentiment", "sentiment_score", "tone_label"}
    assert result["sentiment"] in LABELS
    assert math.isfinite(result["sentiment_score"])
    assert -1 <= result["sentiment_score"] <= 1
    assert result["tone_label"] in TONES
    # Semantic accuracy is measured by scripts/evaluate_sentiment.py, not by
    # asserting that a lexicon classifier agrees with every intended label.


def test_evaluation_reports_confusion_metrics_and_mismatches(monkeypatch):
    class FixedAnalyzer:
        def analyze_article_sentiment(self, article):
            label = {"A": "Positive", "B": "Positive", "C": "Neutral"}[article["title"]]
            return {"sentiment": label, "sentiment_score": 0.5 if label == "Positive" else 0.0}

    monkeypatch.setattr(evaluate_sentiment, "SentimentAnalyzerService", FixedAnalyzer)
    dataset = {"synthetic": True, "examples": [
        {"id": "a", "headline": "A", "expected_sentiment": "Positive"},
        {"id": "b", "headline": "B", "expected_sentiment": "Negative"},
        {"id": "c", "headline": "C", "expected_sentiment": "Neutral"},
    ]}
    report = evaluate_sentiment.evaluate(dataset)
    assert report["accuracy"] == pytest.approx(2 / 3)
    assert report["macro_f1"] == pytest.approx(5 / 9)
    assert report["per_class"]["Positive"] == {
        "precision": 0.5, "recall": 1.0, "f1": pytest.approx(2 / 3), "support": 1,
    }
    assert report["per_class"]["Negative"] == {
        "precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 1,
    }
    assert report["confusion_matrix_actual_rows_predicted_columns"]["Negative"]["Positive"] == 1
    assert report["mismatch_count"] == 1
    assert report["mismatches"][0]["id"] == "b"
    assert report["mismatches"][0]["predicted_sentiment"] == "Positive"


def test_evaluation_rejects_empty_dataset():
    with pytest.raises(ValueError, match="at least one example"):
        evaluate_sentiment.evaluate({"examples": []})
