import random
import torch
from .network import EncoderRNN, AttnDecoderRNN, device
from .beam_search import get_response


str_preprocessor, encoder, decoder = [None] * 3

def init():
    global str_preprocessor, encoder, decoder
    str_preprocessor = torch.load('core_seq2seq/str_preprocessor.class')

    encoder = EncoderRNN(str_preprocessor.n_word, 256).to(device)
    encoder.load_state_dict(torch.load('core_seq2seq/encoder.state'))

    decoder = AttnDecoderRNN(256, str_preprocessor.n_word).to(device)
    decoder.load_state_dict(torch.load('core_seq2seq/decoder.state'))


def get_message(msg):
    msg = msg[:990]
    if not msg[-1] in r'，。、；‘’“”【】（）()[]{},./\;:<>?《》？|-=——+_`~·！!@#$%^&*()￥"' + "'":
        msg = msg + '。'
    input_tensor = str_preprocessor.str2tensor(msg)
    results, score = get_response(input_tensor, encoder, decoder,
                                  str_preprocessor, beam_search=25, best_n=5, weight_lambda=0.65)
    result = results[random.randint(0, 4)]
    while result[-1] == result[-2] and result[-1] == result[-3] and len(result) >= 3:
        result = result[:-1]
    return result, score


class Chatter():
    def __init__(self):
        pass

    def response(self, message_str):
        result, score = get_message(message_str)
        return result, score, score > -0.22
