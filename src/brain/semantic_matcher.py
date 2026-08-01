"""
Paraphrase-resistant semantic matching, additive to the literal keyword
tables in risk_classifier.py and boundary_guard.py.

Why this exists: eval/adversarial_boundary_eval.py already proves the
keyword-only baseline scores ~40% overall and single-digit-to-mid recall on
evasive_destructive/boundary_evasion specifically -- exactly because those
categories are, by construction, phrased to avoid every literal keyword.
eval/README.md's own conclusion is that closing this with more keywords is
an unbounded list problem, and proposes a trained model (Track B) as the
real fix. Track B needs a GPU and real usage data neither of which exist
yet (see docs/STATUS.md).

This module is a cheap, deterministic, dependency-free intermediate step
that needs neither: character-n-gram TF-IDF cosine similarity against a
small hand-written bank of exemplar phrases per category. It is NOT a
replacement for Track B's eventual trained model -- it's a same-day
improvement to the baseline that costs nothing to run (no network call, no
model weights, no GPU) and, unlike keyword substring matching, degrades
gracefully to paraphrase/synonym variation because it scores whole-phrase
character overlap rather than requiring an exact substring.

Design choices, deliberately mirroring the rest of this codebase's
philosophy:
- Fails open (returns None / no match) rather than guessing, exactly like
  RiskModelBackend.judge()'s contract -- a low-confidence semantic score is
  worse than no opinion, so callers keep whatever the keyword floor said.
- Pure Python, no numpy/sklearn/embedding-model download -- this keeps it
  usable offline and testable without any real network access, matching
  requirements.txt's existing minimal-dependency stance.
- Exemplar phrases here are deliberately NOT copied from
  eval/adversarial_cases.jsonl -- doing so would let this module "cheat"
  the eval it's meant to be scored against. They're independently written
  paraphrases of the same underlying intents.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field


def _ngrams(text: str, n: int = 3) -> Counter:
    """Character n-grams over lowercased, whitespace-collapsed text. Word
    boundaries are marked with a single space so "delete this" and "this
    delete" don't share as many n-grams as true substring overlap would
    suggest, while still catching partial-word/synonym drift that literal
    substring matching misses entirely."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return Counter()
    padded = f" {normalized} "
    return Counter(padded[i : i + n] for i in range(len(padded) - n + 1))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class MatchResult:
    label: str | None
    score: float
    matched_exemplar: str | None = None


@dataclass
class SemanticMatcher:
    """label -> list of exemplar phrases. best_match() scores the input
    text's n-gram vector against every exemplar of every label and returns
    the single best (label, score, exemplar) triple, or (None, 0.0, None)
    if given no exemplars at all. Callers apply their own threshold --
    this class only measures similarity, it doesn't decide what counts as
    "close enough" (that's a policy decision that differs between risk
    classification and hard-boundary detection)."""

    exemplars: dict[str, list[str]] = field(default_factory=dict)
    ngram_size: int = 3
    _vectors: dict[str, list[tuple[str, Counter]]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._vectors = {
            label: [(phrase, _ngrams(phrase, self.ngram_size)) for phrase in phrases]
            for label, phrases in self.exemplars.items()
        }

    def best_match(self, text: str) -> MatchResult:
        query_vec = _ngrams(text, self.ngram_size)
        best_label: str | None = None
        best_score = 0.0
        best_exemplar: str | None = None

        for label, phrase_vectors in self._vectors.items():
            for phrase, vec in phrase_vectors:
                score = _cosine(query_vec, vec)
                if score > best_score:
                    best_score = score
                    best_label = label
                    best_exemplar = phrase

        return MatchResult(label=best_label, score=best_score, matched_exemplar=best_exemplar)
