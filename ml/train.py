"""Train a reproducible TF-IDF + Logistic Regression model on synthetic examples."""
from pathlib import Path
import csv, json, joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "incidents.csv"
MODEL = ROOT / "model.joblib"
METRICS = ROOT / "evaluation.json"

def load_data():
    with DATA.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r["text"] for r in rows], [r["label"] for r in rows]

def main():
    texts, labels = load_data()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.30, random_state=42, stratify=labels
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", lowercase=True)),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")),
    ])
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    metrics = {
        "dataset": "synthetic educational examples; not representative of real incidents",
        "random_seed": 42,
        "train_examples": len(x_train),
        "test_examples": len(x_test),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=model.classes_).tolist(),
        "labels": list(model.classes_),
        "note": "Metrics are from a tiny synthetic dataset and must not be interpreted as real-world performance."
    }
    joblib.dump(model, MODEL)
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved model: {MODEL}")
    print(f"Saved evaluation: {METRICS}")

if __name__ == "__main__":
    main()
