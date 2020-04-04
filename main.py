import re
import random
import time
from typing import Set
import pymongo
from aiocqhttp.event import Event
from bot import BotYiri
import plugins
from core_seq2seq.core import Chatter

if __name__ == '__main__':
    with open('account.txt') as f:
        account = f.read().strip()
    yiri = BotYiri(name='伪全能怡姐', access_token=account)

    # 保存消息记录到 MongoDB
    if __name__ == '__main__':
        mongoClient = pymongo.MongoClient('mongodb://localhost:27017/')
        messageDB = mongoClient['QQ_Messages']


    @yiri.msg_preprocessor('group')
    async def save_log(message: str, flags: Set[str], context: Event):
        messageCollection = messageDB[str(context.group_id)]
        message = {
            '_id': context.message_id,
            'time': time.asctime(time.localtime(time.time())),
            'user_id': context.user_id,
            'raw_message': context.raw_message,
        }
        messageCollection.insert_one(message)


    # 处理 @ 消息
    @yiri.msg_preprocessor('group', 'discuss')
    async def at_me(message: str, flags: Set[str], context: Event):
        at_me_code = f'[CQ:at,qq={context.self_id}]'
        if at_me_code in message:
            message = message.replace(at_me_code, '').strip()
            flags.add('at_me')
        return message, flags


    # 去除 CQ码
    @yiri.msg_preprocessor()
    async def remove_cq_code(message: str, flags: Set[str], context: Event):
        return re.sub(r'\[.*?\]', '', message).strip(), flags


    # 处理.d骰子
    @yiri.msg_preprocessor()
    async def dice_command(message: str, flags: Set[str], context: Event):
        if message[:2] == '.d':
            message = re.sub(r'[^0-9]', '', message[2:])
            if message == '':
                message = '1'
            flags.add('.dice')
        return message, flags


    # 关闭对话机制
    @yiri.msg_preprocessor('group')
    async def disable_chat_command(message: str, flags: Set[str], context: Event):
        if message[:5] == '.关闭对话':
            message = re.sub(r'[^0-9]', '', message[2:])
            if message == '':
                message = '1'
            flags.add('.关闭对话')
        return message, flags

    # ========================分割线========================

    # 处理仅 @ 的情况
    @yiri.msg_handler('at_me')
    async def just_at_me(message: str, flags: Set[str], context: Event):
        if message == '':
            if random.random() < 0.9:
                return '你在叫我吗？', yiri.SEND_MESSAGE | yiri.BREAK_OUT
            else:
                return '爱卿平身。', yiri.SEND_MESSAGE | yiri.BREAK_OUT


    # 处理踢人
    @yiri.msg_handler('at_me')
    async def kick_sender(message: str, flags: Set[str], context: Event):
        if message == '请踢断我的肋骨吧！':
            return '马上安排', yiri.SEND_MESSAGE | yiri.BREAK_OUT | yiri.KICK_OUT


    # 萌即正义！
    @yiri.msg_handler('at_me')
    async def 萌即正义(message: str, flags: Set[str], context: Event):
        if message == '给我一份「萌即正义」！':
            if not yiri.get_status('萌即正义'):
                yiri.add_status('萌即正义', timeout=60, user_id=context.user_id)
                print(f'已为{context.user_id}开启萌即正义。')
                return 'かわいいは正義！(有效期1分钟)', yiri.SEND_MESSAGE | yiri.BREAK_OUT
            else:
                reply = '同一时刻只能有一人开启「萌即正义」模式。'
                return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


    # 处理.d骰子
    @yiri.msg_handler('.dice')
    async def dice(message: str, flags: Set[str], context: Event):
        萌正 = yiri.get_status('萌即正义')
        if 萌正 and context.user_id == 萌正.user_id:
            reply = f'这是怡姐，不是骰子。（说完还是很诚实地摇了6点）（かわいいは正義）'
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        rnd = random.randint(1, max(int(message), 1))
        reply = f'这是怡姐，不是骰子。（说完还是很诚实地摇了{rnd}点）'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


    # 关闭对话机制
    @yiri.msg_handler('.关闭对话')
    async def disable_chat(message: str, flags: Set[str], context: Event):
        timeout = int(message) * 60
        yiri.add_status('关闭对话', timeout=timeout, group_id=context.group_id)
        reply = f'已在群{context.group_id}中关闭对话，时长{message}分钟。'
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    # 加载插件
    plugins.load_plugins(yiri)

    # 处理对话
    chatters = {}
    @yiri.msg_handler()
    async def chat(message: str, flags: Set[str], context: Event):
        if message == '':
            return

        id_ = str(context.user_id)
        ch = chatters.get(id_, None)
        if ch is None:
            ch = Chatter()
            chatters[id_] = ch

        reply, score, approve = ch.response(message)
        print('{}, score={}'.format(reply, score))

        关闭对话 = yiri.get_status('关闭对话')
        if 关闭对话 and context.group_id == 关闭对话.group_id:
            return

        if approve or ('private' in flags) or ('at_me' in flags) or (random.random() > 0.95):
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    yiri.run(host='127.0.0.1', port='7700')
