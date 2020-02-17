from chatterbot import ChatBot
bot = ChatBot(
    '伪全能怡姐',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter',
    filters=['chatterbot.filters.RepetitiveResponseFilter']
)
def r(s):return bot1.get_response(s).text

bot1 = ChatBot(
    '伪全能怡姐',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter',
    filters=['chatterbot.filters.RepetitiveResponseFilter']
)
def p(s):return bot1.get_response(s).text

beg = '这样吗……知道定格的真相了吧。'
print('“'+beg+'”')
t = beg
while True:
    t = r(t)
    print('“'+t+'”')
    t = p(t)
    print('“'+t+'”')