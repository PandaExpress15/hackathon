from __future__ import annotations

from dataclasses import dataclass

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
except ImportError:  # pragma: no cover
    TfidfVectorizer = None
    LogisticRegression = None
    Pipeline = None


@dataclass(frozen=True)
class IntentPrediction:
    label: str
    confidence: float


TRAINING_EXAMPLES: dict[str, list[str]] = {
    "occupation_pay": [
        "how much do lawyers earn", "salary for nuclear engineers", "median wage for a journalist",
        "pay range for public relations specialists", "what is the wage for political scientists",
    ],
    "occupation_employment": [
        "how many nurses are employed", "employment for public relations specialists",
        "largest occupations", "occupations with the most jobs", "how many nuclear engineers are there",
    ],
    "occupation_compare": [
        "compare lawyers and political scientists", "compare journalists with public relations specialists",
        "which pays more software developers or mechanical engineers", "compare two careers",
    ],
    "state_pay": [
        "which states pay nuclear engineers the most", "lawyer salary in Maryland",
        "highest paying states for journalists", "compare pay in Virginia and Maryland",
    ],
    "state_employment": [
        "which states employ the most public relations specialists", "where are political scientists concentrated",
        "states with the most nurses", "location quotient for nuclear engineers",
    ],
    "growth": [
        "fastest growing occupations", "job outlook for political scientists", "growth through 2034",
        "is nuclear engineering growing", "projected change for journalists",
    ],
    "openings": [
        "occupations with the most annual openings", "how many openings for lawyers",
        "annual job openings for public relations", "careers with most openings",
    ],
    "skills": [
        "skills for nuclear engineers", "what skills do journalists need", "essential skills for lawyers",
        "skills needed in public relations",
    ],
    "knowledge": [
        "knowledge areas for lawyers", "what knowledge do nuclear engineers need", "knowledge for political scientists",
    ],
    "tasks": [
        "what tasks do public relations specialists perform", "what does a nuclear engineer do",
        "daily work of journalists", "duties of political scientists",
    ],
    "software": [
        "software used by broadcast technicians", "tools used by nuclear engineers", "technology for public relations",
    ],
    "degree_earnings": [
        "highest earning bachelor degree fields", "communications degree earnings", "compare engineering and business majors",
        "what major has the highest median earnings",
    ],
    "education_wages": [
        "wages by education level", "bachelor level occupation wages by state",
        "metro pay for occupations requiring a bachelor degree", "employment by typical entry education",
    ],
    "unsupported": [
        "which company has the happiest employees", "guarantee I get hired", "live job openings today",
        "best employer culture", "predict my exact salary",
    ],
}


class IntentRouter:
    def __init__(self) -> None:
        self.model = None
        if Pipeline is not None:
            texts: list[str] = []
            labels: list[str] = []
            for label, examples in TRAINING_EXAMPLES.items():
                texts.extend(examples)
                labels.extend([label] * len(examples))
            self.model = Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
                ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
            ])
            self.model.fit(texts, labels)

    def classify(self, question: str) -> IntentPrediction:
        if self.model is None:
            return IntentPrediction("unknown", 0.0)
        probabilities = self.model.predict_proba([question])[0]
        classes = self.model.classes_
        index = int(probabilities.argmax())
        return IntentPrediction(str(classes[index]), round(float(probabilities[index]), 4))
