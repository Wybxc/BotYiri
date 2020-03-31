from collections import Iterable
from heapq import heappush, heappop, heapify
import torch
from torch import Tensor
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# device = 'cpu'

KEY_MASKS = {}


def gen_key_mask(max_len: int, sentence_len: int) -> Tensor:
    if KEY_MASKS.get(max_len) is None:
        KEY_MASKS[max_len] =  torch.triu(torch.ones(max_len, max_len, device=device)) == 1
    return KEY_MASKS[max_len][sentence_len]


def padding(arr, max_len, pad=0):
    result =  arr + [pad] * (max_len - len(arr))
    return result, len(arr)


class PriorityQueue():
    def __init__(self, arr=None):
        self._queue = []
        if arr is None:
            pass
        elif isinstance(arr, Iterable):
            self._queue.extend(arr)
            heapify(self._queue)
        else:
            raise TypeError('Parameter `arr` must be iterable!')

    def put(self, item):
        heappush(self._queue, item)

    def get(self):
        return heappop(self._queue)

    def empty(self):
        return not self._queue

    def __len__(self):
        return len(self._queue)