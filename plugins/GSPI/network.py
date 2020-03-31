import math
import torch
import torch.nn as nn
from .utils import device

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)


class Seq2SeqTransformer(nn.Module):
    def __init__(self, d_model, vocab_size_src, vocab_size_tgt, num_encoder_layers=6, num_decoder_layers=6, emb_dropout_p=0.1,
                 pec_dropout_p=0.1, max_len=5000):
        super(Seq2SeqTransformer, self).__init__()
        self.d_model = d_model
        self.vocab_size_src = vocab_size_src
        self.vocab_size_tgt = vocab_size_tgt
        self.max_len = max_len
        self.embed_src = nn.Embedding(vocab_size_src, d_model)
        self.embed_tgt = nn.Embedding(vocab_size_tgt, d_model)
        # self.dropout = nn.Dropout(emb_dropout_p)
        self.pos_enc = PositionalEncoding(d_model, dropout=pec_dropout_p, max_len=max_len)

        self.transformer = nn.Transformer(d_model, num_encoder_layers=num_encoder_layers,
                                          num_decoder_layers=num_decoder_layers)
        self.out = nn.Linear(d_model, vocab_size_tgt)
        self.get_pinyin = nn.Linear(d_model, vocab_size_src)

    def forward(self, source, target, src_key_padding_mask=None, tgt_key_padding_mask=None):
        target_length = target.shape[1]
        source = self.embed_src(source.transpose(0, 1))
        target = self.embed_tgt(target.transpose(0, 1))
        source = self.pos_enc(source * math.sqrt(self.d_model))
        target = self.pos_enc(target * math.sqrt(self.d_model))

        # memory_key_padding_mask = src_key_padding_mask.clone() if src_key_padding_mask is not None else None
        memory_key_padding_mask = src_key_padding_mask
        tgt_mask = self._gen_no_peek_mask(target_length)

        output = self.transformer(source, target, tgt_mask=tgt_mask, src_key_padding_mask=src_key_padding_mask,
                                  tgt_key_padding_mask=tgt_key_padding_mask,
                                  memory_key_padding_mask=memory_key_padding_mask)
        output = output.transpose(0, 1)
        result = self.out(output)
        source_back = self.get_pinyin(output)
        return result, source_back  # size == (batch_size, target_full_length, vocab_size)

    def _gen_no_peek_mask(self, length):
        mask = torch.transpose(torch.triu(torch.ones(length, length)) == 1, 0, 1)
        mask = mask.float().masked_fill(mask == 0, float('-inf')).masked_fill(mask == 1, float(0.0))
        return mask.to(device)