# -*- coding: utf-8 -*-
# Простая нейросеть для классификации фраз о "парах" (расписании).
# Установка: pip install scikit-learn joblib

import re
from dataclasses import dataclass
from typing import List, Tuple

from joblib import dump, load
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
import numpy as np

MODEL_PATH = "pair_schedule_classifier.joblib"

# --------------------------
# Нормализация и правила
# --------------------------
def normalize_text(s: str) -> str:
    """Мягкая нормализация для русского текста."""
    s = s.lower()
    s = s.replace("ё", "е")
    # распространенные опечатки "завтра"
    s = re.sub(r"\bзатр[аи]\b", "завтра", s)
    s = re.sub(r"\bзавтро\b", "завтра", s)
    # убрать лишние знаки
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)  # оставить буквы/цифры/_
    s = re.sub(r"\s+", " ", s).strip()
    return s

# Сильные отрицания рядом с "парами" → точно False
NEG_FALSE_PATTERNS = [
    r"не\s+буд\w+.*пар",     # "не будет ... пар"
    r"пар[ауеы]?\s+не\s+буд\w+",
    r"нет\s+пар",            # "нет пар"
    r"пар\s+нет",
    r"не\s+хочу.*пар",       # "не хочу ... пар"
    r"не\s+буду.*пар",       # "не буду ... пар(ах)"
    r"сегодня\s+нет\s+пар",
    r"завтра\s+нет\s+пар",
]

def has_strong_negation(t: str) -> bool:
    t = normalize_text(t)
    return any(re.search(p, t) for p in NEG_FALSE_PATTERNS)

# --------------------------
# Датасет
# --------------------------
@dataclass
class Sample:
    text: str
    label: int  # 1=True, 0=False

base_samples: List[Sample] = [
    # Ваши примеры
    Sample("Какие затра пары?", 1),
    Sample("Расписание завтра", 1),
    Sample("Ну хорошо: вечером приду на пары", 0),
    Sample("Какая пара?", 0),
    Sample("Не хочу завтра на пары", 0),
    Sample("Я завтра приду на пары", 0),
    Sample("что у нас завтра по парам?", 1),
    Sample("Есть ли на завтра расписание по парам?", 1),
    Sample("Сегодня вообще нет пар", 0),
    Sample("Не буду сегодня на парах", 0),
    Sample("Сколько пар у меня завтра?", 1),
    Sample("Я не знаю: есть ли у меня пары", 1),
    Sample("Расписание на сегодня", 1),
    Sample("Будут ли завтра пары?", 1),
    Sample("он занят, так что пар не будет", 0),
    Sample("пар не будет", 0),
    Sample("Можно узнать расписание на завтра?", 1),
    Sample("У меня завтра пара по математике?", 1),
    Sample("Завтра не будет пар?", 1),

    # Усиления (вариации/опечатки/синонимы)
    Sample("А какие завтра пары?", 1),
    Sample("что по парам завтра", 1),
    Sample("пары завтра будут", 1),
    Sample("расписание пары завтра", 1),
    Sample("расписание на завтра", 1),
    Sample("есть пары сегодня?", 1),
    Sample("сколько пар сегодня", 1),
    Sample("какие пары сегодня", 1),
    Sample("какая первая пара завтра", 1),
    Sample("у меня завтра пары?", 1),
    Sample("завтра пары есть?", 1),

    Sample("а у нас завтра ПАР не будет чтоли?", 0),
    Sample("я спросил, пар не будет", 0),
    Sample("сказали на пары не идти", 0),
    Sample("пар не будет", 0),
    Sample("нет пар завтра", 0),
    Sample("завтра пар нет", 0),
    Sample("я на пары не приду", 0),
    Sample("ничего про пары", 0),
    Sample("вечером буду дома", 0),
    Sample("скорее всего пар не будет", 0),
    Sample("пары отменили", 0),
    Sample("сегодня без пар", 0),
    Sample("На пары надо ходить", 0),
    Sample("лох", 0), Sample("пидр", 0),  Sample("пидор", 0),


    Sample("с легким паром", 0),
    Sample("парить есть что", 0),
    Sample("испарик", 0),
]

def make_xy(samples: List[Sample]) -> Tuple[List[str], List[int]]:
    X = [normalize_text(s.text) for s in samples]
    y = [s.label for s in samples]
    return X, y

# --------------------------
# Модель (Pipeline)
# --------------------------
def build_pipeline() -> Pipeline:
    # Символьные n-граммы хорошо переносят опечатки
    vec = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        lowercase=True,
        max_features=50000,
    )
    mlp = MLPClassifier(
        hidden_layer_sizes=(64,),
        activation="relu",
        solver="adam",
        alpha=1e-4,
        max_iter=200,
        random_state=42,
    )
    return Pipeline([("tfidf", vec), ("mlp", mlp)])

def train_and_save():
    X, y = make_xy(base_samples)

    # небольшая валидация, чтобы увидеть, что всё ок
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    clf = build_pipeline()
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_val)
    acc = accuracy_score(y_val, y_pred)
    print(f"Validation accuracy: {acc:.3f}")
    print(classification_report(y_val, y_pred, digits=3))

    dump(clf, MODEL_PATH)
    print(f"Model saved to: {MODEL_PATH}")

# --------------------------
# Инференс
# --------------------------
class ScheduleClassifier:
    def __init__(self, path: str = MODEL_PATH):
        self.pipeline: Pipeline = load(path)

    def predict_proba(self, text: str) -> float:
        t = normalize_text(text)
        proba = self.pipeline.predict_proba([t])[0][1]  # вероятность класса 1
        return float(proba)

    def is_schedule_query(self, text: str, threshold: float = 0.5) -> bool:
        # Жёстко рубим отрицания
        if has_strong_negation(text):
            return False
        p = self.predict_proba(text)
        return p >= threshold

# --------------------------
# Пример использования
# --------------------------
if __name__ == "__main__":
    # 1) Обучение (один раз)
    train_and_save()

    # 2) Инференс
    clf = ScheduleClassifier(MODEL_PATH)

    tests = [
        "Какие затра пары?",
        "Расписание завтра",
        "Ну хорошо: вечером приду",
        "Какая пара?",
        "Не хочу завтра на пары",
        "Я завтра приду на пары",
        "Подскажи: что у меня завтра по парам?",
        "Есть ли завтра расписание по парам?",
        "Сегодня вообще нет пар",
        "Не буду сегодня на парах",
        "Сколько пар у меня завтра?",
        "Я не знаю: есть ли у меня пары",
        "Расписание на сегодня",
        "Будут ли завтра пары?",
        "Я завтра занят: так что пар нет",
        "Можно узнать расписание на завтра?",
        "У меня завтра пара по математике?",
        "Завтра не будет пар?",
        "а у нас затра ПАР не будет чтоли?"
    ]

    print("\nPredictions:")
    for t in tests:
        print(f"{t:>50}  ->  {clf.is_schedule_query(t)}  (p={clf.predict_proba(t):.2f})")


    print("\n\n")
    while True:
        text = input("> ")
        if text == "exit":
            break
        print(f"-> {clf.is_schedule_query(text)}  (p={clf.predict_proba(text):.2f})\n")

