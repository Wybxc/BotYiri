import pypinyin
import torch
from .utils import device


class Vocabulary():
    PAD, UNK, SOS = range(3)
    def __init__(self, dict_file='vocabulary.txt'):
        self._pinyin2code = {chr(i + 97): i for i in range(26)}
        self._pinyin2code['，'] = 26
        with open(dict_file, 'r', encoding='utf-8') as f:
            s = f.read()
            self._code2char = [''] * 3 + ['，'] + list(s)
            self._char2code = {s:i for i, s in enumerate(self._code2char)}
            self.vocab_size = len(self._code2char)
            self.pinyin_masks = torch.full((27, self.vocab_size), -1000, dtype=torch.float32, device=device)
            for i, pinyin_list in enumerate(pypinyin.pinyin(s, heteronym=True, style=pypinyin.FIRST_LETTER)):
                for pinyin in pinyin_list:
                    self.pinyin_masks[self._pinyin2code[pinyin], i + 4] = 0
            self.pinyin_masks[26, 3] = 1


    def __len__(self):
        return self.vocab_size

    def encode_pinyin(self, pinyin):
        return [self._pinyin2code[p] for p in pinyin]

    def encode(self, sentence):
        pinyin = [self._pinyin2code[pinyin[0]] for pinyin in pypinyin.pinyin(sentence, style=pypinyin.FIRST_LETTER)]
        result = [self._char2code[c] for c in sentence]
        result = [self.SOS] + result
        return pinyin, result

    def decode(self, sentence):
        result = [self._code2char[c] for c in sentence]
        return ''.join(result)
