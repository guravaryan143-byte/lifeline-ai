import re
import logging
import pickle
from pathlib import Path
from functools import lru_cache
from rapidfuzz import fuzz
from app.models import Category

logger = logging.getLogger(__name__)
MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "model.joblib"
KEYWORDS = {
    Category.road_hazard: ["pothole", "road blocked", "traffic signal", "collision", "crash", "road hazard"],
    Category.medical_assistance: ["injured", "medical", "bleeding", "ambulance", "unconscious", "first aid"],
    Category.fire_environmental: ["fire", "smoke", "gas leak", "chemical spill", "flood", "fallen tree"],
    Category.infrastructure_damage: ["broken pipe", "damaged bridge", "broken wire", "collapsed", "damaged building", "power line"],
    Category.public_safety: ["harassment", "unsafe", "suspicious", "threat", "violence", "security concern"],
}
URGENT_REVIEW_TERMS = ["fire", "smoke", "gas leak", "injured", "bleeding", "unconscious",
                       "collision", "crash", "immediate danger", "chemical spill"]

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except (OSError, EOFError, pickle.UnpicklingError, ValueError, AttributeError, ImportError):
        logger.exception("Could not load the AI model; using keyword fallback.")
        return None

def analyze_description(description: str) -> dict:
    text = re.sub(r"\s+", " ", description.strip().lower())
    indicators = [term for terms in KEYWORDS.values() for term in terms if term in text]
    review = any(word in text for word in URGENT_REVIEW_TERMS)
    model = load_model()
    category = Category.other
    confidence = None
    method = "keyword_fallback"
    if model is not None:
        probabilities = model.predict_proba([text])[0]
        best_index = int(probabilities.argmax())
        score = float(probabilities[best_index])
        predicted = str(model.classes_[best_index])
        # This threshold is a conservative abstention threshold, not a safety threshold.
        # Logistic regression probabilities are not calibrated here.
        if score >= 0.45:
            try:
                category = Category(predicted)
                confidence = round(score, 4)
                method = "tfidf_logistic_regression_uncalibrated_score"
            except ValueError:
                pass
        else:
            review = True
    else:
        scores = {cat: sum(1 for term in terms if term in text) for cat, terms in KEYWORDS.items()}
        best = max(scores, key=scores.get)
        if scores[best]:
            category = best
            confidence = None  # no misleading pseudo-probability for keyword matches
        else:
            review = True
    if category == Category.other:
        review = True
    return {
        "category": category, "confidence": confidence,
        "summary": description.strip()[:240], "indicators": indicators[:8],
        "review_required": review, "method": method,
        "notice": "AI output is decision support only. Human review is required for consequential decisions. This is not emergency triage."
    }

def duplicate_candidates(description: str, incidents: list, threshold: int = 78) -> list[dict]:
    matches = []
    for incident in incidents:
        score = fuzz.token_set_ratio(description, incident.description)
        if score >= threshold:
            matches.append({"incident_id": incident.id, "similarity": round(score / 100, 2),
                            "reason": "Text similarity; coordinator confirmation required."})
    return sorted(matches, key=lambda x: x["similarity"], reverse=True)[:5]
