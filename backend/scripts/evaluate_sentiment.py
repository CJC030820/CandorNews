"""Evaluate headline polarity offline; synthetic labels are not ground truth.

Run from any directory:
    python backend/scripts/evaluate_sentiment.py
    python backend/scripts/evaluate_sentiment.py --output report.json
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.sentiment_analyzer import SentimentAnalyzerService  # noqa: E402


LABELS = ("Positive", "Negative", "Neutral")
DEFAULT_FIXTURE = BACKEND_ROOT / "tests" / "fixtures" / "sentiment_headlines.json"


def evaluate(dataset):
    analyzer = SentimentAnalyzerService()
    confusion = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    mismatches = []
    examples = dataset["examples"]
    if not examples:
        raise ValueError("The dataset must contain at least one example.")
    for example in examples:
        intended = example["expected_sentiment"]
        if intended not in LABELS:
            raise ValueError(f"Unsupported sentiment label: {intended!r}")
        result = analyzer.analyze_article_sentiment({"title": example["headline"]})
        predicted = result["sentiment"]
        confusion[intended][predicted] += 1
        if predicted != intended:
            mismatches.append({**example, "predicted_sentiment": predicted,
                               "sentiment_score": result["sentiment_score"]})

    per_class = {}
    for label in LABELS:
        true_positive = confusion[label][label]
        predicted_count = sum(confusion[actual][label] for actual in LABELS)
        support = sum(confusion[label].values())
        precision = true_positive / predicted_count if predicted_count else 0.0
        recall = true_positive / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}

    return {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": "vaderSentiment",
        "model_version": version("vaderSentiment"),
        "input_scope": "Headline only, using analyze_article_sentiment with title populated",
        "synthetic": dataset.get("synthetic", False),
        "annotation_method": dataset.get("annotation_method", "Unspecified"),
        "limitations": "AI-authored intended labels require human review. Results measure agreement on this synthetic fixture only, not production accuracy or factual truth.",
        "total": len(examples),
        "intended_label_counts": dict(Counter(row["expected_sentiment"] for row in examples)),
        "accuracy": sum(confusion[label][label] for label in LABELS) / len(examples),
        "macro_f1": sum(metrics["f1"] for metrics in per_class.values()) / len(LABELS),
        "confusion_matrix_actual_rows_predicted_columns": confusion,
        "per_class": per_class,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    dataset = json.loads(args.fixture.read_text(encoding="utf-8"))
    report = evaluate(dataset)

    print(f"Synthetic headline evaluation: {report['total']} examples")
    print(f"Accuracy: {report['accuracy']:.2%}; macro F1: {report['macro_f1']:.4f}")
    print("Intended label rows / predicted label columns:")
    print(f"{'':12}" + "".join(f"{label:>12}" for label in LABELS))
    for intended, row in report["confusion_matrix_actual_rows_predicted_columns"].items():
        print(f"{intended:12}" + "".join(f"{row[predicted]:>12}" for predicted in LABELS))
    print(f"Mismatches: {report['mismatch_count']}")
    print(report["limitations"])

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"JSON report: {args.output}")


if __name__ == "__main__":
    main()
