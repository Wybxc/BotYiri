from aiocqhttp import CQHttp

class QQBot():
    NOTHING = 0
    SEND_MESSAGE = 0b000001
    BREAK_OUT = 0b000010
    KICK_OUT = 0b001000
    NOT_AT_SENDER = 0b010000

    def __init__(self, access_token='', console_output=True):
        # pylint: disable=unused-variable
        self._chatters = {}
        self._msg_preprocessors = []
        self._msg_handlers = []
        
        self.bot = CQHttp(access_token=access_token, enable_http_post=False)

        self.QQID = 0
        
        def get_message_type(context):
            if 'message_type' not in context:
                if 'group_id' in context:
                    return 'group'
                elif 'discuss_id' in context:
                    return 'discuss'
                elif 'user_id' in context:
                    return 'private'
            else:
                return context['message_type']

        @self.bot.on_message()
        async def handle_message(context):
            if self.QQID == 0:
                rep = await self.bot.get_login_info()
                self.QQID = rep['user_id']
            message = context['message']
            if console_output:
                print('>>> ' + message)
            flags = set([get_message_type(context)])
            for preprocessor in self._msg_preprocessors:
                message, flags = preprocessor(message, flags, context)
            report_args = {}
            for handler in self._msg_handlers:
                reply, action = handler(message, flags, context)
                at_sender = (action & self.NOT_AT_SENDER) == 0
                if action & self.SEND_MESSAGE:
                    await self.bot.send(context, reply, at_sender=at_sender)            
                if action & self.KICK_OUT:
                    report_args['kick'] = True
                if action & self.BREAK_OUT:
                    return report_args
            return report_args

    def msg_preprocessor(self, func):
        '''
        用于注册消息预处理器的装饰器。
        消息预处理器接受三个参数：消息（字符串），之前的处理标志（字符串set），消息上下文（dict）
        返回两个参数：修改后的消息（字符串），修改后的处理标志（字符串set）
        '''
        def decorated(message, flags, context):
            result = func(message, flags, context)
            return result if result is not None else (message, flags)
        self._msg_preprocessors.append(decorated)
        return decorated

    def msg_handler(self, func):
        '''
        用于注册消息处理器的装饰器。
        消息处理器接受三个参数：消息（字符串），处理标志（字符串set），消息上下文（dict）
        返回两个参数：回复信息（字符串），动作信息（整数）
        '''
        def decorated(message, flags, context):
            result = func(message, flags, context)
            return result if result is not None else ('', self.NOTHING)
        self._msg_handlers.append(decorated)
        return decorated

    async def send(self, context, message, **kwargs):
        return await self.bot.send(context, message, **kwargs)

    def run(self, host='127.0.0.1', port='7700'):
        self.bot.run(host=host, port=port)
