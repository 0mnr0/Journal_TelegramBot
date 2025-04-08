import re
from datetime import datetime, timedelta

daysList = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
days_variants = {
    "понедельник": ["понедельник", "пн"],
    "вторник": ["вторник", "вт"],
    "среда": ["среда", "среду", "ср"],
    "четверг": ["четверг", "чт"],
    "пятница": ["пятница", "пятницу", "пт"],
    "суббота": ["суббота", "субботу", "сб"],
    "воскресенье": ["воскресенье", "вс"]
}
daysVariants = [variant for variants in days_variants.values() for variant in variants]
days_map = {variant: day for day, variants in days_variants.items() for variant in variants}


def IsDateTimeInMessage(txt):
    disallowedSymbols = "?!.:;,[](){}|\"'/<>*+-@#$%&№^`~"
    for symbol in disallowedSymbols:
        txt = txt.replace(symbol, '')

    words = txt.lower()
    for symbol in disallowedSymbols:
        words = words.replace(symbol, '')
    words = words.split()
    for word in words:
        if word in daysVariants:
            return True
    return False


def getDateByText(txt: str, now: datetime) -> datetime:
    disallowedSymbols = "?!.:;,[](){}|\"'/<>*+-@#$%&№^`~"
    words = txt.lower()
    for symbol in disallowedSymbols:
        words = words.replace(symbol, '')
    print("Words: " + words)
    words=words.split()

    # Поиск дня недели в тексте (с учетом склонений)
    searchingDay = None
    for word in words:
        if word in days_map:
            searchingDay = days_map[word]
            break
    if searchingDay is None:
        return now

    dayIndex = list(days_variants.keys()).index(searchingDay)
    currentIndex = now.weekday()

    days_ahead = (dayIndex - currentIndex) % 7
    if days_ahead == 0:
        days_ahead += 7

    return now + timedelta(days=days_ahead)


#Making check if user says "/shed +1" for next day or etc
def isItPlusOperation(txt):
    try:
        first_part, second_part = txt.split(' ', 1)
        command = (second_part.replace(' ',''))[0]
        return command == '+' or command == '-'
    except:
        return False

def getTextOperation(txt):
    first_part, second_part = txt.split(' ', 1)
    # Replace all without nums
    command = (second_part.replace(' ','')) [0]
    action = (second_part.replace(' ',''))[1:]
    if command == '+' or command == '-':
        action = action.replace('+','').replace('-','')
        action = re.findall("\d+", action)[0]
        return command, action


def is_valid_time(time_str):
    try:
        time_str = time_str.strip()
        time_str = re.sub(r"[., ]", ":", time_str)

        try:
            valid_time = datetime.strptime(time_str, "%H:%M")
            return convert_time_to_hh_mm(valid_time)
        except ValueError:
            return None
    except:
        return False


def convert_time_to_hh_mm(time_obj):
    return time_obj.strftime("%H_%M")

def strClear(input_str):
    if any(char.isdigit() for char in input_str):
        # Удаление всех символов, кроме цифр
        digits_only = re.sub(r'\D', '', input_str)
        return digits_only
    else:
        return input_str

def clearDate(s):
    # Проверка на наличие чисел
    if re.search(r'\d', s):
        # Удаление всех буквенных символов, кроме разрешённых знаков
        cleaned_string = re.sub(r'[a-zA-Zа-яА-Я]', '', s)
        return cleaned_string.replace("/",'').replace("?",'')
    return s


def parse_date(date_input):
    # Получаем текущую дату
    today = datetime.today()

    # Убираем все пробелы и приводим к общему разделителю (например, дефис)
    date_input = re.sub(r"[./\s]+", "-", date_input.strip())

    # Разделяем введённые части даты
    date_parts = date_input.split("-")

    # Автозаполнение недостающих частей даты
    if len(date_parts) == 2:  # Например, если введены только день и месяц
        day, month = date_parts
        year = str(today.year)  # Автозаполнение года текущим годом
    elif len(date_parts) == 3:  # Если введены день, месяц и год
        day, month, year = date_parts
    elif len(date_parts) == 1:  # Если введен только день
        day = date_parts[0]
        month = str(today.month)
        year = str(today.year)
    else:
        raise ValueError("Неверный формат даты. Попробуйте другой формат.")

    # Обрабатываем случаи, когда отсутствуют ведущие нули (например, 7-10 -> 07-10)
    day = day.zfill(2)
    month = month.zfill(2)

    # Собираем дату в формат YYYY-MM-DD
    formatted_date = f"{year}-{month}-{day}"

    # Проверяем корректность даты
    try:
        parsed_date = datetime.strptime(formatted_date, "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError("Неверная дата. Проверьте введенные значения.")

