import requests
import re
import time

# данные пользователя
user_params = {
    'access_token': '<your_access_token>', 
    'user_id': '<your_user_id>',
    'v': '5.50'
}

client_id = '5429354' # id приложения
lisa_id = '357311639' # id Лизы

dict = '' # словарь для поиска слов
used_letters = [] # список использованных букв

def read_dict():
    """Чтение словаря из файла"""
    f = open('dict.txt')
    global dict
    dict = f.read()
    f.close()

def vk_request(method, method_params):
    """Отправка запроса через vk api"""
    req = 'https://api.vk.com/method/{0}?'.format(method);
    for key in user_params:
        req = req + key + '=' + user_params[key] + '&'
    for key in method_params:
        req = req + key + '=' + method_params[key] + '&'
    req = req[:-1]
    response = requests.get(req)
    return response

def send_message(user_id, message):
    """Отправка сообщения"""
    params = {'user_id': user_id, 'message': message}
    r = vk_request('messages.send', params).json()
    if 'response' in r:
        id = r['response']
    else:
        id = 0
    return id

def get_message(last_message_id):
    """Получение сообщения, которое идет после сообщения с last_message_id от Лизы"""
    message = ''
    user_id = ''
    params = {'last_message_id': last_message_id, 'count': '1', 'time_offset': '100'}
    r = vk_request('messages.get', params).json()
    if 'response' in r:
        response = r['response']
        if len(response['items']) > 0:
            item = response['items'][0]
            message = item['body']
            user_id = str(item['user_id'])
    return (user_id, message)

def wait_for_message(letter):
    """Ожидание сообщения от Лизы"""
    message_id = send_message(lisa_id, 'вис ' + letter)
    now = time.time()
    f = True
    while True:
        time.sleep(5)
        user_id, message = get_message(str(message_id))
        if user_id == lisa_id:
            return message
        # если ожидание превышает 20 сек отправить сообщение еще раз
        if (time.time() - now) > 20:
            # защита от Flood error
            if f: 
                message_id = send_message(lisa_id, letter)
            else:
                message_id = send_message(lisa_id, 'вис ' + letter)
            f = not f

def parse_message(message):
    """Парсинг сообщения, получение регулярного выражения для поиска по словарю"""
    prog = re.compile('Загаданное слово.*')
    alt_prog = re.compile('Такую букву уже отгадывали.')
    win_prog = re.compile('Вы победили!')
    lose_prog = re.compile('Вы проиграли..')
    if win_prog.search(message): # угадали
        return 'win'
    if lose_prog.search(message): # не угадали
        return 'lose'
    if alt_prog.search(message): # Такую букву уже отгадывали. 
        return 'pass'
    match = prog.search(message)
    re_search = None
    if match:
        line = match.group(0)
        tokens = line.split()
        chars = tokens[2:]
        # формирование строки, содержащей регулярное выражение
        re_string = '^'
        for char in chars:
            if char == '_':
                re_string = re_string + '[а-я]'
            else:
                re_string = re_string + char
        re_string = re_string + '$'
        re_search = re.compile(re_string, re.MULTILINE)
    return re_search

def get_words(re_search):
    """Поиск слов в словаре по регулярному выражению"""
    words = []
    match = re_search.finditer(dict)
    # выбор всех найденных слов в словаре
    if match:
        for m in match:
            words.append(m.group(0))
    return words

def get_letter(words):
    """Выбор следующей буквы"""
    letters = {}
    # подсчет количества всех встречающихся неиспользованных букв в найденных словах
    for word in words:
        for letter in word:
            if letter in letters:
                letters[letter] = letters[letter] + 1
            elif not (letter in used_letters):
                letters[letter] = 1
    # выбор буквы, которая встречается наибольшее кол-во раз
    letter = max(letters.keys(), key=lambda x: letters[x])
    # добавление ее в список использованных
    used_letters.append(letter) 
    return letter

def guess_word():
    """Игра"""
    letter = ''
    while True:
        # отправка сообщения и ожидание ответа
        message = wait_for_message(letter)
        print('message received', message.split('\n')[:2])
        # парсинг сообщения
        re_search = parse_message(message)
        # если произошла какая-то ошибка (маловероятно)
        if not re_search:
            print('some error')
            return
        # слово угадано
        if re_search == 'win':
            print('win')
            return
        # слово не угадано
        if re_search == 'lose':
            print('lose')
            return
        # Такую букву уже отгадывали.
        if re_search != 'pass':
            words = get_words(re_search)
            letter = get_letter(words)

if __name__ == '__main__':
    read_dict()
    guess_word()
