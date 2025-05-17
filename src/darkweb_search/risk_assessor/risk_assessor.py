import threading
from functools import lru_cache
from dataclasses import dataclass, field
from collections import Counter

from src.darkweb_search.utils.text import preprocess_text

import torch
from transformers import pipeline

@dataclass
class RiskResult:
    score: float
    category_scores: dict[str, float] = field(default_factory=dict)


class RiskAssessor:
    RISK_KEYWORDS = {
        "weapons": {"gun", "pistol", "rifle", "ammo", "weapon", "firearm"},
        "drugs": {"drug", "cocaine", "heroin", "meth", "mdma", "cannabis"},
        "extremism": {"terror", "bomb", "attack", "jihad", "isis", "al-qaeda"},
        "fraud": {"bitcoin", "scam", "fraud", "counterfeit", "phishing"},
        "hitman": {"hitman", "assassin", "kill", "murder", "bounty"},
    }
    ZERO_SHOT_LABELS = list(RISK_KEYWORDS.keys()) + ["other"]
    ZERO_SHOT_TEMPLATE = "This text is about {}."
    _lock = threading.Lock()

    def __init__(self, use_cuda: bool = False, model_name: str = "facebook/bart-large-mnli"):
        self.device = 0 if use_cuda and torch.cuda.is_available() else -1
        self.model_name = model_name
        with self._lock:
            self._pipeline = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=self.device,
            )

    @lru_cache(maxsize=128)
    def _zero_shot_cached(self, text: str, top_k: int) -> tuple[tuple[str, float], ...]:
        result = self._pipeline(
            text,
            candidate_labels=self.ZERO_SHOT_LABELS,
            hypothesis_template=self.ZERO_SHOT_TEMPLATE,
        )
        labels = result.get("labels", [])
        scores = result.get("scores", [])
        pairs = list(zip(labels, scores))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return tuple(pairs[:top_k])

    def assess_keywords(self, text: str) -> RiskResult:
        tokens = preprocess_text(text)
        counts = Counter(tokens)

        hits_per_cat = {
            cat: sum(counts[w] for w in kws) for cat, kws in self.RISK_KEYWORDS.items()
        }
        total_hits = sum(hits_per_cat.values())

        if total_hits == 0:
            return RiskResult(0.0, {})

        max_hits = max(hits_per_cat.values()) or 1
        raw_score = total_hits / (max_hits * len(self.RISK_KEYWORDS))
        score = min(1.0, raw_score)

        proportions = {
            cat: hits / total_hits for cat, hits in hits_per_cat.items() if hits > 0
        }
        return RiskResult(score, proportions)

    def assess_zero_shot(self, text: str, top_k: int = 3) -> RiskResult:
        if not text:
            return RiskResult(0.0, {})
        pairs = self._zero_shot_cached(text, top_k)
        if not pairs:
            return RiskResult(0.0, {})
        
        category_scores = {label: score for label, score in pairs}
        max_score = pairs[0][1]
        return RiskResult(max_score, category_scores)

    def assess(self, text: str, method: str = "both") -> dict[str, RiskResult]:
        results: dict[str, RiskResult] = {}
        if method in ("keywords", "both"):
            results['keywords'] = self.assess_keywords(text)
        if method in ("zero-shot", "both"):
            results['zero_shot'] = self.assess_zero_shot(text)
        return results
