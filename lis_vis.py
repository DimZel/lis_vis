# -*- coding: utf-8 -*-
import requests
import re
import time
import os
import sys
import codecs

# данные пользователя
user_params = {
    'access_token': '<your_access_token>', 
    'user_id': '<your_user_id>',
    'v': '5.50'
}

client_id = '5429354' # id приложения
lisa_id = '357311639' # id Лизы

dict = u'' # словарь для поиска слов
used_letters = ['\r', ' '] # список использованных букв (+ костыли для python 2)

ver = int(sys.version[0]) # версия python

def read_dict():
    """Чтение словаря из файла"""
    with codecs.open('dict.txt', 'r', 'utf-8') as f:
        global dict
        if ver == 2:
            dict = unicode(f.read())
        else:
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

def get_message(last_message_id, count):
    """Получение сообщения, которое идет после сообщения с last_message_id"""
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

def get_messages(last_message_id, count):
    """Получение count последних сообщений, котороые идут после сообщения с last_message_id"""
    messages = []
    params = { 'last_message_id': str(last_message_id), 'count': str(count) }
    r = vk_request('messages.get', params).json()
    if 'response' in r:
        response = r['response']
        for item in response['items']:
            message = item['body']
            user_id = str(item['user_id'])
            messages.append((user_id, message))
    return messages

def wait_for_message(letter):
    """Ожидание сообщения от Лизы"""
    message_id = send_message(lisa_id, letter)
    now = time.time()
    f = True
    while True:
        time.sleep(5)
        messages = get_messages(message_id, 5)
        for user_id, message in messages:
            if user_id == lisa_id:
                return message
        # если ожидание превышает 20 сек отправить сообщение еще раз
        if (time.time() - now) > 20 and letter != '':
            # защита от Flood error
            if f: 
                message_id = send_message(lisa_id, letter)
            else:
                message_id = send_message(lisa_id, letter)
            f = not f
			
			now = time.time()

def parse_message(message):
    """Парсинг сообщения, получение регулярного выражения для поиска по словарю"""
    prog = re.compile(u'Загаданное слово.*')
    win_prog = re.compile(u'Вы победили!')
    lose_prog = re.compile(u'Вы проиграли..')
    running_prog = re.compile(u'Игра уже идет.')
    if win_prog.search(message): # угадали
        return 'win'
    if lose_prog.search(message): # не угадали
        return 'lose'
    if running_prog.search(message): # Игра уже идет.
        return 'running'
    match = prog.search(message)
    re_search = None
    if match:
        line = match.group(0)
        tokens = line.split()
        chars = tokens[2:]
        # формирование строки, содержащей регулярное выражение
        re_string = u'^'
        for char in chars:
            if char == u'_':
                re_string = re_string + u'[а-я]'
            else:
                re_string = re_string + char
        re_string = re_string + u'\s'
        if ver == 2:
            re_search = re.compile(unicode(re_string), re.MULTILINE)
        else:
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
        if ver == 2:
            message = unicode(wait_for_message(u'вис ' + letter))
        else:
            message = wait_for_message(u'вис ' + letter)
        print('message received "' + ' \\ '.join(message.split('\n')[:2]) + '"')
        # парсинг сообщения
        re_search = parse_message(message)
        # если произошла какая-то ошибка (маловероятно)
        if not re_search:
            print('some error')
            return None
        # слово угадано
        if re_search == 'win':
            print('win')
            score = len(message.split('\n')[1].split()[2]) - 1
            return score
        # слово не угадано
        if re_search == 'lose':
            print('lose')
            return 0
        # Игра уже идет.
        if re_search == 'running':
            wait_for_message('вис стоп')
            letter = ''
            continue
        words = get_words(re_search)
        if len(words) > 1:
            letter = get_letter(words)
        elif len(words) == 1:
            letter = words[0]
        elif len(words) == 0:
            letter = 'стоп'

def farm_vip():
    message = wait_for_message('баланс')
    score = int(message.split()[2])
    while score < 150:
        new_score = guess_word()
        score += new_score
        print(u'баланс: ' + str(score))


if __name__ == '__main__':
    read_dict()
    if len(sys.argv) > 1:
        if sys.argv[1] == '--vip':
            print('vip')
            farm_vip()
        else:
            print('error')
    else:
        print('word')
        guess_word()
    os.system('pause')