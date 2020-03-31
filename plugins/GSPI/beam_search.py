import torch
import torch.nn.functional as F
from .utils import device
from .vocabulary import Vocabulary
from .network import Seq2SeqTransformer


def get_response_greedy(transformer: Seq2SeqTransformer, vocabulary: Vocabulary, source: str):
    length = len(source)
    source = torch.tensor(vocabulary.encode_pinyin(source), dtype=torch.long, device=device)
    source = source.view(1, -1)
    history = [vocabulary.SOS]
    with torch.no_grad():
        for di in range(length):
            target = torch.tensor(history, dtype=torch.long, device=device).view(1, -1)
            output, _ = transformer(source, target)
            output = output[0, -1] + vocabulary.pinyin_masks[source[di]]
            values, indices = output.topk(1)
            history.append(int(indices[0]))
    return vocabulary.decode(source)


def get_responses(transformer: Seq2SeqTransformer, vocabulary: Vocabulary, source: str, beam_search=25,
                  diverse_alpha=0.9, diverse_gamma=0.65, diverse_lambda=0.65, best_n=5, use_random=False):
    length = len(source)
    if length == 0:
        return [''] * best_n
    source = torch.tensor(vocabulary.encode_pinyin(source), dtype=torch.long, device=device)
    sources = source.expand(beam_search, -1)

    with torch.no_grad():
        # 初始化 beam
        target = torch.tensor([vocabulary.SOS], dtype=torch.long, device=device).view(1, -1)
        output, _ = transformer(source.view(1, -1), target)
        output = output[0, -1]
        output = output + vocabulary.pinyin_masks[source[0]]
        output = F.log_softmax(output, dim=0)
        values, indices = output.topk(beam_search)
        histories = indices.unsqueeze(1)
        scores = values

        for di in range(length - 1):
            # 模型批量计算下一个字符的概率
            output, _ = transformer(sources, histories)
            output = output[:, -1, :] + vocabulary.pinyin_masks[source[di + 1]]
            output = F.log_softmax(output, dim=1)
            values, indices = output.topk(beam_search)

            # 获得下一个整句的概率
            values *= diverse_lambda ** di
            values -= torch.arange(1, beam_search + 1, device=device) * diverse_gamma
            inv = 1 / (di + 1)
            weight_old_score = (1 - inv) ** diverse_alpha
            weight_next_score = inv ** diverse_alpha
            if use_random:
                scores = scores * 0.9975 + torch.rand(beam_search, device=device) * 0.005  # 千分之5的随机浮动
            new_scores = values * weight_next_score + scores * weight_old_score
            next_characters = indices

            # 提取其中的前 beam_search 项
            candidates = [None] * (beam_search * beam_search)
            for i in range(beam_search):
                for j in range(beam_search):
                    candidates[i * beam_search + j] = (float(new_scores[i][j]), i, int(next_characters[i][j]))
            candidates.sort(reverse=True)
            histories_list = []
            scores_list = []
            for score, last, char in candidates:
                sentence = histories[last].tolist() + [char]
                histories_list.append(torch.tensor(sentence, dtype=torch.long, device=device))
                scores_list.append(score)

                # 只挑选前 beam_search 项
                if len(histories_list) == beam_search:
                    break

            # 张量化
            histories = torch.stack(histories_list)
            scores = torch.tensor(scores_list, device=device)

    # 提取结果
    best_n = best_n if best_n <= beam_search else beam_search
    results = []
    for i in range(best_n):
        results.append(vocabulary.decode(histories[i]))
        # results.append(str(histories[i]))
    return results
