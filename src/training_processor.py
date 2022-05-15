import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

import pandas as pd
from transformers import AutoTokenizer, PreTrainedTokenizerFast

from .diff_preprocessor import DiffPreprocessor
from .lexer import Lexer


class TrainingProcessor:
    """
    This class is used to convert data into necessary format for training:
    1) Construct history for each author
    2) Tokenize diffs and messages
    3) Save everything in format required by training pipeline
    """

    def __init__(
        self,
        diff_tokenizer_path: str,
        msg_tokenizer_name: str,
        diff_kwargs: Dict[str, Any],
        msg_kwargs: Dict[str, Any],
        **kwargs,
    ):
        self._diff_tok = PreTrainedTokenizerFast(tokenizer_file=diff_tokenizer_path)
        self._msg_tok = AutoTokenizer.from_pretrained(msg_tokenizer_name)
        self._diff_kwargs = diff_kwargs
        self._msg_kwargs = msg_kwargs

    def _tokenize_diffs(self, diffs: List[str]) -> List[List[int]]:
        return self._diff_tok(diffs, **self._diff_kwargs).input_ids

    def _tokenize_messages(self, msgs: List[str]) -> List[List[int]]:
        return self._msg_tok(msgs, **self._msg_kwargs).input_ids

    def __call__(self, in_fname: str, output_dir: str):
        """
        Expects following columns in input file:
        - "author"  - commit author
        - "date"    - commit timestamp
        - "mods"    - commit modifications
        - "message" - commit message
        Note: assumes that commits from each author are already in correct order for history.
        """
        logging.info(f"Start processing {in_fname}")
        df = pd.read_csv(in_fname)
        df["pos_in_history"] = df.groupby("author").cumcount()

        logging.info("Tokenizing diffs")
        df["diff"] = [Lexer.lex(DiffPreprocessor.preprocess(diff)) for diff in df["diff"]]
        diff_input_ids = self._tokenize_diffs(df["diff"].tolist())

        logging.info("Tokenizing messages")
        msg_input_ids = self._tokenize_messages(df["message"].tolist())

        logging.info("Constructing history")
        history = defaultdict(list)
        for msg, id in zip(msg_input_ids, df["author"].tolist()):
            history[id].append(msg)

        logging.info("Saving history")
        with open(os.path.join(output_dir, "mtests_history.json"), "w") as outfile:
            json.dump(history, outfile)

        logging.info("Saving data")
        df["diff_input_ids"] = diff_input_ids
        df[["diff_input_ids", "pos_in_history", "author"]].to_json(
            os.path.join(output_dir, "mtests.json"), lines=True, orient="records"
        )
