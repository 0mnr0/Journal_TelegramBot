# -*- coding: utf-8 -*-
# Простая нейросеть для классификации фраз о "парах" (расписании).
# Установка: pip install scikit-learn joblib
import os.path
import re
from dataclasses import dataclass
from typing import List, Tuple

from joblib import dump, load
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split

MODEL_PATH = "triggerDataset.joblib"
DetectionPercent = 0.625 #62.5% Accuracy

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
    Sample("пары завтра", 1),
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
    Sample("пары в понедельник", 1),
    Sample("пары во втроник", 1),
    Sample("пары в среду", 1), Sample("пары среда", 1),
    Sample("пары в четверг", 1),
    Sample("пары в пятницу", 1), Sample("пары пятница", 1),
    Sample("пары в субботу", 1), Sample("пары суббота", 1),
    Sample("пары в воскресенье", 1),

    Sample("пары в пн", 1),
    Sample("пары во вт", 1),
    Sample("пары в ср", 1),
    Sample("пары в чт", 1),
    Sample("пары в пт", 1),
    Sample("пары в сб", 1),
    Sample("пары в вс", 1),

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
    Sample("пары +?", 1), Sample("пары -?", 1),
    Sample("на какой паре зачет", 1),
    Sample("какой парой зачет", 1),
    Sample("сколько пар должно быть", 1),
    Sample("зачёт - парой", 1),
    Sample("зачёт какой парой", 1),
    Sample("будут пары, нет?", 1),
    Sample("пары будут?", 1),
    Sample("пары завтра", 1),
    Sample("пары послезавтра", 1),
    Sample("пары вчера", 1),
    Sample("покажи пары", 1),
    Sample("покажи пары на", 1),
    Sample("напомните пары", 1),
    Sample("напомните пары на", 1),



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
    Sample("парапам", 0), Sample("парарам", 0),


    Sample("с легким паром", 0),
    Sample("когда будут пары", 0),
    Sample("парить есть что", 0),
    Sample("испарик", 0),
    Sample("то есть", 0),
    Sample("пары были", 0),
    Sample("я приду к - паре", 0),
    Sample("я приду к -й паре", 0),
    Sample("пары никогда", 0),
    Sample("пары никогда", 0),
    Sample("паоы", 0),
    Sample("Возможно опоздаю на пару", 0),
    Sample("Возможно опоздаю на пары", 0),
    Sample("До конца пары не успеешь", 0),
    Sample("До конца пары успеешь", 0),
    Sample("Пары отсидеть", 0),
    Sample("", 0),
    Sample("каждые день пары", 0),
    Sample("витая пара", 0),
    Sample("Кто придёт на пару", 0),
    Sample("Кто к паре", 0),
    Sample("Кто к паре", 0),
    Sample("Пары между зачётами", 0),
    Sample("будут пары между зачёт", 0),
    Sample("Пары между зачётами", 0),
    Sample("поработаем на паре", 0),
    Sample("закидывать пары", 0), Sample("закидывает пары", 0),
    Sample("Я к - паре", 0),
    Sample("Я к - паре", 0),
    Sample("оцените пары", 0),
    Sample("оцените пары", 0),
    Sample("задание на паре", 0),
    Sample("задание на паре", 0),
    Sample("спим на паре", 0),
    Sample("спим на паре", 0),
    Sample("пару дней", 0),
    Sample("пару человек", 0),
    Sample("пару часов", 0),
    Sample("пары сделают меня", 0),
    Sample("пары сделают меня", 0),
    Sample("ебал на пару", 0),
    Sample("не показывай пары", 0),


    Sample("s", 0), Sample("ы", 0), Sample("а", 0), Sample(".", 0), Sample("g", 0), Sample("п", 0), Sample("bruh", 0), Sample("0", 0),
    Sample("й", 0), Sample("q", 0), Sample("qq", 0), Sample("ч", 0), Sample("\\", 0), Sample("м", 0), Sample("+", 0), Sample("-", 0),
    Sample("л", 0), Sample("ъ", 0), Sample("ь", 0), Sample("щ", 0), Sample("х", 0), Sample("шо", 0), Sample("ничо", 0), Sample("чё", 0)
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
        max_iter=10000,
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

    def is_schedule_query(self, text: str, threshold: float = DetectionPercent) -> bool:
        # Жёстко рубим отрицания
        if has_strong_negation(text):
            return False
        p = self.predict_proba(text)
        return p >= threshold



if not os.path.exists(MODEL_PATH):
    train_and_save()

clf = ScheduleClassifier(MODEL_PATH)
def GetCommandWeight(txt) -> tuple[bool, float]:
    return clf.is_schedule_query(txt), clf.predict_proba(txt)


if __name__ == "__main__":
    # Обучение
    # train_and_save()

    while True:
        text = input("> ")
        if text == "exit": break
        print(f"-> {clf.is_schedule_query(text)}  (p={clf.predict_proba(text):.2f})\n")

