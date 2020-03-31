import re
from typing import Set
from aiocqhttp.event import Event
import torch
from bot import BotYiri
from .utils import device
from .vocabulary import Vocabulary
from .network import Seq2SeqTransformer
from .beam_search import get_responses

def init(yiri: BotYiri):
    # pylint: disable=unused-variable
    vocabulary = Vocabulary(r'plugins/GSPI/vocabulary.txt')
    transformer = Seq2SeqTransformer(256, 27, len(vocabulary), num_encoder_layers=3, num_decoder_layers=3,
                                     max_len=175).to(device)
    transformer.load_state_dict(torch.load(r'plugins/GSPI/transformer.state'))

    @yiri.msg_preprocessor()
    def gspi_pre(message: str, flags: Set[str], context: Event):
        if message[:2] == '.g':
            message = message[2:].lower().replace(',', '，')
            message = re.sub(r'[^a-z，]', '', message)
            flags.add('.gspi')
        return message, flags
        
    @yiri.msg_handler('.gspi')
    def gspi(message: str, flags: Set[str], context: Event):
        reply = get_responses(transformer, vocabulary, message, beam_search=25, diverse_alpha=1, diverse_gamma=-0.1, diverse_lambda=1, best_n=1, use_random=True)[0]
        print(reply)
        return reply, yiri.SEND_MESSAGE | yiri.BREAK_OUT
