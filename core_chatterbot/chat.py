from chatterbot import ChatBot
bot = ChatBot(
    '伪全能怡姐',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter'
)
def r(s):return bot.get_response(s).text

while True:
    i = input('>>> ').strip()
    if i != 'exit':
        print(r(i))
    else:
        break
        