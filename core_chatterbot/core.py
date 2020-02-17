from chatterbot import ChatBot

class Chatter():
    def __init__(self):
        self.bot = ChatBot(
            '伪全能怡姐',
            storage_adapter='chatterbot.storage.MongoDatabaseAdapter'
        )

    def response(self, message_str):
        rep = self.bot.get_response(message_str)
        # if rep.text[-1] == '。':
            # rep.text = rep.text[:-1] + 'w'
        return rep.text, rep.confidence, rep.confidence > 0.68
