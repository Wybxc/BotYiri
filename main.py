import re
import random
import time
import pymongo
from bot import QQBot
from core_seq2seq.core import Chatter

with open('account.txt') as f:
    account = f.read().strip()
yiri = QQBot(access_token=account)


if __name__ == '__main__':
    mongoClient = pymongo.MongoClient('mongodb://localhost:27017/')
    messageDB = mongoClient['QQ_Messages']

@yiri.msg_preprocessor
def save_log(message, flags, context):
    messageCollection = messageDB[str(context['group_id'])]
    message = {
        '_id': context['message_id'],
        'time': time.asctime(time.localtime(time.time())),
        'user_id': context['user_id'],
        'raw_message': context['raw_message'],
    }
    messageCollection.insert_one(message)

@yiri.msg_preprocessor
def at_me(message, flags, context):
    if 'group' in flags or 'discuss' in flags:
        at_me_code = f'[CQ:at,qq={yiri.QQID}]'
        if at_me_code in message:
            message = message.replace(at_me_code, '').strip()
            flags.add('at_me')
    return message, flags


@yiri.msg_preprocessor
def remove_cq_code(message, flags, context):
    return re.sub(r'\[.*?\]', '', message).strip(), flags


@yiri.msg_handler
def just_at_me(message, flags, context):
    if ('at_me' in flags) and message == '':
        if random.random() < 0.9:
            return '你在叫我吗？', yiri.SEND_MESSAGE | yiri.BREAK_OUT
        else:            
            return '爱卿平身？', yiri.SEND_MESSAGE | yiri.BREAK_OUT


@yiri.msg_handler
def kick_sender(message, flags, context):
    if ('at_me' in flags) and message == '请踢断我的肋骨吧！':
        return '马上安排', yiri.SEND_MESSAGE | yiri.BREAK_OUT | yiri.KICK_OUT


@yiri.msg_preprocessor
def dice_command(message, flags, context):
    if message[:2] == '.d':
        message = re.sub(r'[^0-9]', '', message[2:])
        if message == '':
            message = '1'
        flags.add('dice')
    return message, flags


@yiri.msg_handler
def dice(message, flags, context):
    if 'dice' in flags:
        rnd = random.randint(1, max(int(message), 1))
        reply = f'这是怡姐，不是骰子。（说完还是很诚实地摇了{rnd}点）'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


chatters = {}
@yiri.msg_handler
def chat(message, flags, context):
    id_ = str(context['user_id'])
    ch = chatters.get(id_, None)
    if ch is None:
        ch = Chatter()
        chatters[id_] = ch

    reply, score, approve = ch.response(message)
    if approve or ('private' in flags) or ('at_me' in flags) or (random.random() > 0.95):
        print('{}, score={}'.format(reply, score))
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


@yiri.msg_handler
def test(message, flags, context):
    print(message, flags, yiri.QQID)
    if 'at_me' in flags:
        return '怡姐正在维护中...', yiri.SEND_MESSAGE | yiri.BREAK_OUT

if __name__ == '__main__':
    yiri.run(host='127.0.0.1', port='7700')
