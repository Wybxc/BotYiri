import ast
import math
import random
import re
from typing import Set
from aiocqhttp.event import Event
from bot import BotYiri

def iint(n, minimal=1):
    if isinstance(n, float):
        n = int(n)
    if n <= minimal or not isinstance(n, int):
        n = minimal
    return n

def dice(n):
    n = iint(n)
    return random.randint(1, n)

def dicem(count, n):
    result = 0
    for _ in range(iint(count)):
        result += dice(n)
    return result


def calc(s, arguments=None):
    # pylint: disable=eval-used
    try:
        ast_expr = ast.parse(s, mode='eval')
    except SyntaxError:
        return 'Syntax error!'
    for node in ast.walk(ast_expr):
        if isinstance(node, ast.Attribute):
            return 'Calculator does not support attributes!'
    code = compile(ast_expr, '<string>', 'eval')
    env = {k:v for k, v in math.__dict__.items() if '_' not in k}
    env.update({
        '__builtins__': {'int': int, 'float': float, 'range': range},
        'dice': dice, 
        'd': dice,
        'dicem': dicem,
        'dm': dicem,
    })
    if isinstance(arguments, dict):
        env.update(arguments)
    try:
        result = eval(code, env, {})
    except TypeError as e:
        print(e)
        return 'Name is not defined!'
    except NameError as e:
        print(e)
        return 'Name is not defined!'   
    return result

def init(yiri: BotYiri):
    # pylint: disable=unused-variable
    @yiri.msg_preprocessor()
    def calc_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.c':
            message = message[2:].strip()
            message = message.replace('&#91;', '[').replace('&#93;', ']')
            flags.add('.calc')
        return message, flags
        
    @yiri.msg_handler('.calc')
    def calc_(message: str, flags: Set[str], context: Event):
        reply = str(calc(message))
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    # @yiri.msg_preprocessor()
    # def xdef_pre(message: str, flags: Set[str], context: Event):
    #     if message[:2] == '.x':
    #         message = message[2:].strip()
    #         message = message.replace('&#91;', '[').replace('&#93;', ']')
    #     return message, flags
        
    # @yiri.msg_handler('.xdef')
    # def xdef(message: str, flags: Set[str], context: Event):
    #     slices = message.split(' ')
    #     name = slices[0]
    #     code = ' '.join(slices[1:]).replace('&#91;', '[').replace('&#93;', ']')
    #     storage = yiri.get_storage('xdef')
    #     storage[name] = 
    #     reply = f'已添加宏定义{name} := {code}'
    #     print(reply)
    #     return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

        
        