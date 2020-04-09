import time
import re
import argparse
from typing import Set
from aiocqhttp.event import Event
from bot import BotYiri

MAX_LEVEL = 100
MAX_QUOTA = 100000


def op(level_required=MAX_LEVEL):
    def check_op(yiri: BotYiri, message: str, flags: Set[str], context: Event):
        storage = yiri.get_storage('operators')
        if context.user_id in storage.keys():
            level, quota, expiration = storage[context.user_id]
            quota -= 1
            if quota <= 0:
                storage.remove(context.user_id)
                return '管理员次数已用尽。', yiri.SEND_MESSAGE | yiri.BREAK_OUT
            if time.time() > expiration:
                storage.remove(context.user_id)
                return '管理员已到期。', yiri.SEND_MESSAGE | yiri.BREAK_OUT
            if level > level_required:
                return f'权限不足，当前是{level}级权限，需要{level_required}级权限。', yiri.SEND_MESSAGE | yiri.BREAK_OUT
            storage[context.user_id] = [level, quota, expiration]
            return None
        return f'权限不足。', yiri.SEND_MESSAGE | yiri.BREAK_OUT
    return check_op


def add_op(yiri: BotYiri, qqid: int, level: int, quota=-1, timeout=-1):
    storage = yiri.get_storage('operators')
    expiration = time.time() + timeout * 60 if timeout >= 0 else float('inf')
    quota = quota if quota >= 0 else MAX_QUOTA
    level = level if 1 <= level <= MAX_LEVEL else MAX_LEVEL
    storage[qqid] = [level, quota, expiration]
    return level, quota, expiration


def remove_op(yiri: BotYiri, qqid: int):
    storage = yiri.get_storage('operators')
    storage.remove(qqid)


def get_op_info(yiri: BotYiri, qqid: int):
    storage = yiri.get_storage('operators')
    if qqid in storage.keys():
        return storage[qqid]
    return MAX_LEVEL + 1, 0, 0.0


def format_time(time_sec):
    if time_sec != float('inf'):
        time_struct = time.gmtime(time_sec - time.timezone)
        return time.strftime('%Y{y}%m{m}%d{d}%H{h}%M{f}%S{s}', time_struct).format(y='年', m='月', d='日', h='时', f='分', s='秒')
    return '无限'


def register_op_commands(yiri: BotYiri):
    # pylint: disable=unused-variable
    @yiri.msg_preprocessor()
    async def op_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.o':
            if len(message) <= 2:
                return message, flags
            message = re.sub(r'\[CQ:at,qq=(\d+)\]', lambda x: x.groups()[0], message)
            if message[2] == 'r':
                flags.add('.op_remove')
                message = message[3:].strip()
                return message, flags
            flags.add('.op_add')
            message = message[2:].strip()            
        return message, flags

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--level', type=int, default=-1)
    parser.add_argument('-q', '--quota', type=int, default=-1)
    parser.add_argument('-t', '--timeout', type=float, default=-1)

    @yiri.msg_handler('.op_add')
    @yiri.require(op())
    async def op_add(message: str, flags: Set[str], context: Event):
        match = re.match(r'^(\d+)\s?(.*)$', message)
        if not match:
            reply = '语法错误！'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        qqid, args = match.groups()
        qqid = int(qqid)
        try:
            namespace = parser.parse_args(args.split())
        except SystemExit:
            reply = '语法错误！'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        level, _, _ = get_op_info(yiri, context.user_id)
        if namespace.level < 0:
            namespace.level = level + 1
        if namespace.level == 0:
            reply = '权限不足！'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        if level >= namespace.level:
            reply = f'权限不足，需要至少{namespace.level - 1}级权限。'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        n_level, _, _ = get_op_info(yiri, qqid)
        if level >= n_level:
            reply = f'权限不足，需要至少{n_level - 1}级权限。'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        level, quota, expiration = add_op(
            yiri, qqid, namespace.level, namespace.quota, namespace.timeout)
        reply = f'已为用户{qqid}添加管理员，等级为{level}'
        if namespace.quota >= 0:
            reply += f'，限额{quota}次'
        if namespace.timeout >= 0:
            reply += f'，到{format_time(expiration)}为止'
        reply += '。'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.op_remove')
    @yiri.require(op())
    async def op_remove(message: str, flags: Set[str], context: Event):        
        qqid = int(message)
        level, _, _ = get_op_info(yiri, context.user_id)
        n_level, _, _ = get_op_info(yiri, qqid)
        if n_level == 0:
            reply = '权限不足！'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        if level >= n_level:
            reply = f'权限不足，需要至少{n_level - 1}级权限。'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        remove_op(yiri, qqid)
        reply = f'已移除用户{qqid}的管理员权限。'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
