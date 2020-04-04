import ast
import math
import random
import re
import functools
from typing import Set
from multiprocess import Process, Manager  # pylint: disable=no-name-in-module
from aiocqhttp.event import Event
from bot import BotYiri
from .functions import builtins, CalculateError

ENABLED = True

marcos = {}

env = {k: v for k, v in math.__dict__.items() if '_' not in k}
env['pow'] = None  # math.pow 不如内置的 pow 高级
env.update({
    '__builtins__': {
        'abs': abs,
        'all': all,
        'any': any,
        'ascii': ascii,
        'bin': bin,
        'bool': bool,
        'bytearray': bytearray,
        'bytes': bytes,
        'callable': callable,
        'chr': chr,
        'complex': complex,
        'dict': dict,
        'dir': dir,
        'divmod': divmod,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'hash': hash,
        'hex': hex,
        'int': int,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'iter': iter,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'next': next,
        'oct': oct,
        'ord': ord,
        'pow': pow,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip
    },
})
env.update(builtins)


def multiprocess_eval(code, globals_, locals_, result):
    # pylint: disable=eval-used, broad-except
    result['result'] = None
    result['error'] = None
    try:
        result['result'] = eval(code, globals_, locals_)
    except Exception as e:
        result['error'] = e


def timeout_eval(code, globals_, locals_, timeout=2):
    result = Manager().dict()
    # pylint: disable=not-callable
    p = Process(target=multiprocess_eval, args=(code, globals_,
                                                locals_, result))  
    p.start()
    p.join(timeout=timeout)
    if p.is_alive():
        p.terminate()
        raise TimeoutError('计算超时！')
    if result['error']:
        raise result['error']
    return result['result']


def calc(s):
    env.update(marcos)
    try:
        ast_expr = ast.parse(s, mode='eval')
    except SyntaxError as e:
        print(e)
        return 'Syntax error!'
    for node in ast.walk(ast_expr):
        if isinstance(node, ast.Attribute):
            return 'Calculator does not support attributes!'
    if isinstance(ast_expr.body, ast.Name):
        try:
            marco = env[ast_expr.body.id]
            if callable(marco):
                return marco()
            else:
                return marco
        except KeyError:
            return f'{ast_expr.body.id} is not defined!'
        except TypeError as e:
            return re.sub(r'.*missing', f'{ast_expr.body.id} missing', str(e))
    try:
        result = timeout_eval(s, env, {}, timeout=5)
    except TypeError as e:
        return str(e)
    except NameError as e:
        return str(e)
    except CalculateError as e:
        return e.err_msg
    except TimeoutError as e:
        return str(e)
    return result


def parse_xdef(slices):
    if not slices:
        return None, None
    # 匹配宏名称
    match = re.match(r'^[^\W0-9]\w*', slices[0])
    if not match:
        return None, None
    name = match.group()
    slices[0] = slices[0][len(name):]
    code = ' '.join(slices).strip()
    if code[0] != '=':
        code = 'lambda ' + code.replace(':', ':(', 1) + ')'
    else:
        code = code[1:]
    return name, code


def init(yiri: BotYiri):
    # pylint: disable=unused-variable
    @yiri.msg_preprocessor()
    async def calc_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.c':
            message = message[2:].strip()
            message = message.replace('&#91;', '[').replace('&#93;', ']')
            message = message.replace('\n', ' ').replace('\r', ' ')
            flags.add('.calc')
        return message, flags

    @yiri.msg_handler('.calc')
    async def calc_(message: str, flags: Set[str], context: Event):
        reply = str(calc(message))
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_preprocessor()
    async def xdef_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.x':
            if message[2] == 'r':
                flags.add('.xdef_remove')
                message = message[3:].strip()
            elif message[2] == 'l':
                flags.add('.xdef_list')
                message = message[3:].strip()
            elif message[2] == 'a':
                if message[3] == 'r':
                    flags.add('.xdef_alias_remove')
                    message = message[4:].strip()
                else:
                    flags.add('.xdef_alias')
                    message = message[3:].strip()
            else:
                flags.add('.xdef')
                message = message[2:].strip()
            message = message.replace('&#91;', '[').replace('&#93;', ']')
            message = message.replace('\n', ' ').replace('\r', ' ')
        return message, flags

    for name, code in yiri.get_storage('xdef').items():
        func = calc(code)
        marcos[name] = func

    for alias, name in yiri.get_storage('xdef_alias').items():
        marcos[alias] = marcos[name]

    @yiri.msg_handler('.xdef')
    async def xdef(message: str, flags: Set[str], context: Event):
        slices = message.split(' ')
        storage = yiri.get_storage('xdef')
        name, code = parse_xdef(slices)
        if not name:
            reply = 'Syntax Error!'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        func = calc(code)
        if isinstance(func, str):
            reply = func
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        marcos[name] = func
        storage[name] = code
        reply = f'已添加宏定义{name} := {code}'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.xdef_remove')
    async def xdef_remove(message: str, flags: Set[str], context: Event):
        name = message
        if yiri.get_storage('xdef').remove(name):
            reply = f'已移除宏定义{name}'
            alias = yiri.get_storage('xdef_alias').remove_by_value(name)
            if alias:
                for al in alias:
                    marcos.pop(al, None)
                alias = ', '.join(alias)
                reply += f'，及其别名{alias}'
            marcos.pop(name, None)
        else:
            reply = f'未找到宏定义{name}'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.xdef_list')
    async def xdef_list(message: str, flags: Set[str], context: Event):
        reply = '当前已有的宏定义：\n'
        for name, code in yiri.get_storage('xdef').items():
            reply += f'{name} := {code}\n\n'
        reply += '当前定义的宏别名：\n'
        for alias, name in yiri.get_storage('xdef_alias').items():
            reply += f'{alias} = {name}\n\n'
        reply = reply.strip()
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.xdef_alias')
    async def xdef_alias(message: str, flags: Set[str], context: Event):
        storage = yiri.get_storage('xdef_alias')
        alias, name = message.split(' ')[:2]
        storage[alias] = name
        marcos[alias] = marcos[name]
        reply = f'已定义别名{alias} = {name}'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.xdef_alias_remove')
    async def xdef_alias_remove(message: str, flags: Set[str], context: Event):
        name = message
        storage = yiri.get_storage('xdef_alias')
        if storage.remove(name):
            reply = f'已移除宏别名{name}'
            marcos.pop(name, None)
        else:
            reply = f'未找到宏别名{name}'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
