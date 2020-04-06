import ast
import math
import random
import re
import time
import functools
from typing import Set, Union
from multiprocessing import Process, Pipe  # pylint: disable=no-name-in-module
import dill
from aiocqhttp.event import Event
from bot import BotYiri
from .functions import builtin_marcos, CalculateError

ENABLED = True

TIMEOUT = 2

env = None

regexes = None

eval_process = None

pipe_main, pipe_eval = None, None


def get_default_environment():
    m_env = {'__builtins__': {k: v for k,
                              v in math.__dict__.items() if '_' not in k}}
    m_env['__builtins__'].update({
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
        'zip': zip,
    })
    m_env.update(builtin_marcos)
    return m_env


def set_eval_environment():
    global env, regexes, pipe_main, pipe_eval
    pipe_main, pipe_eval = Pipe(duplex=True)
    env = get_default_environment()
    timeout_eval('update', env, timeout=60)
    regexes = {}


class EvalProcess(Process):  # pylint: disable=inherit-non-class
    def __init__(self, pipe):
        super(EvalProcess, self).__init__()
        self.pipe = pipe
        self.environment = {}

    def run(self):
        # pylint: disable=eval-used, broad-except
        while True:
            op, code = self.pipe.recv()
            code = dill.loads(code)
            result, error = None, None
            try:
                if op == 'eval':
                    result = eval(code, self.environment, {})
                elif op == 'call':
                    name, args = code
                    result = self.environment[name](*args)
                elif op == 'update':
                    self.environment.update(code)
                    result = 0
                elif op == 'xdef':
                    name, value = code
                    self.environment[name] = eval(value, self.environment, {})
                    result = self.environment[name]
                elif op == 'alias':
                    alias, name = code
                    self.environment[alias] = self.environment[name]
                    result = self.environment[alias]
                elif op == 'pop':
                    result = self.environment.pop(code, None)
            except Exception as e:
                error = e
            result = dill.dumps(result)
            self.pipe.send((result, error))


def restart_eval_process():
    global eval_process, pipe_eval, pipe_main
    if eval_process and eval_process.is_alive():
        eval_process.terminate()
        print('超时，重启计算进程中……')
    # pylint: disable=not-callable, attribute-defined-outside-init
    eval_process = EvalProcess(pipe_eval)
    eval_process.deamon = True
    eval_process.start()
    timeout_eval('update', env, timeout=60)


def timeout_eval(op: str, code: Union[str, tuple, dict], timeout=-1):
    if not eval_process:
        restart_eval_process()
    code = dill.dumps(code)
    pipe_main.send((op, code))
    timeout = TIMEOUT if timeout < 0 else timeout
    if pipe_main.poll(timeout=timeout):
        result, error = pipe_main.recv()
        result = dill.loads(result)
    else:
        restart_eval_process()
        raise TimeoutError('计算超时！')
    if error:
        raise error
    return result


def check_safe_expression(s):
    ast_expr = ast.parse(s, mode='eval')
    for node in ast.walk(ast_expr):
        if isinstance(node, ast.Attribute):
            raise SyntaxError('不支持属性调用！')
    return ast_expr


def calc(s):
    start_time = time.time()
    try:
        ast_expr = check_safe_expression(s)
    except SyntaxError as e:
        print(e)
        return str(e)
    if isinstance(ast_expr.body, ast.Name):
        try:
            marco = env[ast_expr.body.id]
            if callable(marco):
                return timeout_eval('call', (ast_expr.body.id, ()))
            else:
                return marco
        except KeyError:
            return f'{ast_expr.body.id} is not defined!'
        except TypeError as e:
            return re.sub(r'.*missing', f'{ast_expr.body.id} missing', str(e))
    try:
        result = timeout_eval('eval', s)
    except TypeError as e:
        return str(e)
    except NameError as e:
        return str(e)
    except CalculateError as e:
        return e.err_msg
    except TimeoutError as e:
        return str(e)
    end_time = time.time()
    print(f'计算耗时：{end_time-start_time}')
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


def parse_redef(s):
    r'''redef 语法与正则的转换:
        %d   -> ((?:\+|-)?\d+)
        %f   -> ((?:\+|-)?\d+\.?\d*)
        %s   -> (\S+)
        %[n] -> (\S{1,n})
        %%   -> (?:%)
    '''
    redef2reg = {
        '%d': r'((?:\+|-)?\d+)',
        '%f': r'((?:\+|-)?\d+\.?\d*)',
        '%s': r'(\S+)',
        '%%': r'(?:%)',
    }
    redef2type = {
        'd': 'd',
        'f': 'f',
        's': 's',
        '[': 's',
        '%': '',
    }
    slices = [0]
    redef_matches = re.finditer(r'(%(?:[dfs%]|\[\d+\]))', s)
    types = ''
    for match in redef_matches:
        x, y = match.span()
        slices += [x, y]
        types += redef2type[s[x+1]]
    slices.append(len(s))
    parts = [s[slices[i]:slices[i+1]] for i in range(len(slices) - 1)]
    reg = r'^\s?'
    for part in parts:
        if part and part[0] == '%':
            if part[1] in 'dfs%':
                reg += redef2reg[part]
            elif part[1] == '[':
                reg += r'(\S{1,' + part[2:-1] + r'})'
            else:
                raise SyntaxError('不合法的%表达式！')
        elif part == '':
            reg += r'\s?'
        else:
            part = re.sub(
                r'([\$\(\)\*\+\.\?\\\^\{\}\|\[\]])', lambda s: '\\'+s.group(), part)
            part = re.sub(r'\s', r'\\s?', part)
            reg += part
    reg += r'\s?$'
    return reg, types


def init_calc(yiri: BotYiri):
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


def init_xdef(yiri: BotYiri):
    # pylint: disable=unused-variable
    for name, code in yiri.get_storage('xdef').items():
        env[name] = timeout_eval('xdef', (name, code), timeout=60)        
    
    for alias, name in yiri.get_storage('xdef_alias').items():
        env[alias] = timeout_eval('alias', (alias, name))

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

    @yiri.msg_handler('.xdef')
    async def xdef(message: str, flags: Set[str], context: Event):
        slices = message.split(' ')
        storage = yiri.get_storage('xdef')
        name, code = parse_xdef(slices)
        if not name:
            reply = '语法错误！'
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        if name in builtin_marcos.keys():
            reply = f'不能覆盖定义{name}！'
        try:
            check_safe_expression(code)
            func = timeout_eval('xdef', (name, code))
        except Exception as e: # pylint: disable=broad-except
            reply = str(e)
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        env[name] = func
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
                    timeout_eval('pop', al, timeout=60)
                    env.pop(al, None)
                alias = ', '.join(alias)
                reply += f'，及其别名{alias}'
            red = yiri.get_storage('redef').remove(name)
            if red:
                regexes.pop(name, None)
                alias = ', '.join(alias)
                reply += f'，及其模板'
            reply += '。'
            timeout_eval('pop', name, timeout=60)
            env.pop(name, None)
        else:
            reply = f'未找到宏定义{name}！'
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
        timeout_eval('alias', (alias, name), timeout=60)
        env[alias] = env[name]
        storage[alias] = name
        reply = f'已定义别名{alias} = {name}'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.xdef_alias_remove')
    async def xdef_alias_remove(message: str, flags: Set[str], context: Event):
        name = message
        storage = yiri.get_storage('xdef_alias')
        if storage.remove(name):
            reply = f'已移除宏别名{name}。'
            timeout_eval('pop', name, timeout=60)
            env.pop(name, None)
        else:
            reply = f'未找到宏别名{name}。'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


def init_redef(yiri: BotYiri):
    # pylint: disable=unused-variable
    type_str = {
        'd': int,
        'f': float,
        's': str
    }

    def instance_type(types):
        return [type_str[t] for t in types]

    for name, (template, regex, types) in yiri.get_storage('redef').items():
        regexes[name] = [regex, instance_type(types)]

    @yiri.msg_preprocessor()
    async def redef_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.r':
            if message[2] == 'r':
                flags.add('.redef_remove')
                message = message[3:].strip()
            elif message[2] == 'x':
                flags.add('.redef_define')
                message = message[3:].strip()
            elif message[2] == 'l':
                flags.add('.redef_list')
                message = message[3:].strip()
            else:
                flags.add('.redef')
                message = message[2:].strip()
            message = message.replace('&#91;', '[').replace('&#93;', ']')
            message = message.replace('\n', ' ').replace('\r', ' ')
        return message, flags

    @yiri.msg_handler('.redef')
    async def redef(message: str, flags: Set[str], context: Event):
        slices = message.split(' ', maxsplit=1)
        if len(slices) <= 1:
            reply = "语法错误！"
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        name, scan = slices
        if not regexes.get(name, None):
            reply = f"未找到宏{name}的模板！"
        else:
            regex, types = regexes[name]
            match = re.match(regex, scan)
            if not match:
                reply = "语法错误！"
            else:
                args = map(lambda t: t[0](t[1]), zip(types, match.groups()))
                try:
                    reply = str(timeout_eval('call', (name, args)))
                except Exception as e: # pylint: disable=broad-except
                    reply = str(e)
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.redef_define')
    async def redef_define(message: str, flags: Set[str], context: Event):
        storage = yiri.get_storage('redef')
        slices = message.split(' ', maxsplit=1)
        if len(slices) <= 1:
            reply = "语法错误！"
            print(reply)
            return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
        name, template = slices
        if env.get(name, None):
            template = template.strip()
            regex, types = parse_redef(template)
            regexes[name] = [regex, instance_type(types)]
            storage[name] = [template, regex, types]
            reply = f"已添加宏{name}的模板`{template}`。"
        else:
            reply = f"未找到宏{name}！"
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.redef_remove')
    async def redef_remove(message: str, flags: Set[str], context: Event):
        name = message
        storage = yiri.get_storage('redef')
        if storage.remove(name):
            reply = f'已移除宏{name}的模板。'
            regexes.pop(name, None)
        else:
            reply = f'未找到宏{name}的模板！'
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT

    @yiri.msg_handler('.redef_list')
    async def redef_list(message: str, flags: Set[str], context: Event):
        reply = '当前已有的宏模板：\n'
        for name, (template, regex, types) in yiri.get_storage('redef').items():
            reply += f'{name} :: {template}\n\n'
        reply = reply.strip()
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT


def init(yiri: BotYiri):
    set_eval_environment()
    init_calc(yiri)
    init_xdef(yiri)
    init_redef(yiri)
