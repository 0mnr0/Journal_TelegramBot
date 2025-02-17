import spacy


#print python version
nlp = spacy.load("ru_core_news_sm")
def FilterChatContext(text):
    doc = nlp(text)
    for token in doc:
        # Проверка на ключевые слова, которые могут быть частью вопроса
        if token.text.lower() in ['пары', 'расписание', 'завтра']:
            return True
        # И игнорирование сообщений, которые явно говорят о том, что человек не придет
        if token.text.lower() in ['не', 'приду', 'отмена']:
            return False
    return False


def spacy_test():
    phrases = [
        ["Какие затра пары?", True],
        ["Расписание завтра", True],
        ["Ну хорошо, вечером приду", False],
        ["Какая пара?", False],
        ["Не хочу завтра на пары", False],
        ["Я завтра приду на пары", True],
        ["Подскажи, что у меня завтра по парам?", True],
        ["Есть ли завтра расписание по парам?", True],
        ["Сегодня вообще нет пар", False],
        ["Не буду сегодня на парах", False],
        ["Сколько пар у меня завтра?", True],
        ["Я не знаю, есть ли у меня пары", False],
        ["Расписание на сегодня", True],
        ["Будут ли завтра пары?", True],
        ["Я завтра занят, так что пар нет", False],
        ["Можно узнать расписание на завтра?", True],
        ["У меня завтра пара по математике?", True],
        ["Завтра не будет пар?", False]
    ]
    for PhraseData in phrases:
        phrase = PhraseData[0]
        Gets = FilterChatContext(phrase)
        WaitingFor = PhraseData[1]
        if WaitingFor != Gets:
            print(f'\nЗапущен тест фразы: "{phrase}"')
            print(f'Ожидаемый результат: "{WaitingFor}", Получено: {Gets} ')

spacy_test()