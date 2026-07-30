"""A lightweight local ML model that classifies question intent."""

from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .intent_training_data import INTENT_EXAMPLES
from .schema import IntentPrediction


class LocalIntentModel:
    """TF-IDF plus logistic regression. It interprets questions but never calculates answers."""

    def __init__(self) -> None:
        texts: list[str] = []
        labels: list[str] = []
        for label, examples in INTENT_EXAMPLES.items():
            texts.extend(examples)
            labels.extend([label] * len(examples))
        self.pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
                ("classifier", LogisticRegression(max_iter=1200, random_state=20260730, class_weight="balanced", C=6.0)),
            ]
        )
        self.pipeline.fit(texts, labels)

    def predict(self, question: str) -> IntentPrediction:
        text = re.sub(r"\s+", " ", question.strip().lower())
        if not text:
            return IntentPrediction(label="unsupported", confidence=0.0, method="fallback")
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        index = int(np.argmax(probabilities))
        return IntentPrediction(label=str(classes[index]), confidence=float(probabilities[index]), method="model")
