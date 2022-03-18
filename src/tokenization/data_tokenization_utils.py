import os
import json
import jsonlines
import logging
import pandas as pd
from tqdm import tqdm
from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer, PreTrainedTokenizerFast
from ..base_utils import BaseProcessor


class TrainingProcessor(BaseProcessor):
    """
    This class is used to convert data into necessary format for training:
    1) Construct history for each author
    2) Tokenize diffs and messages
    3) Save everything in format required by my training pipeline
    """

    def __init__(
        self,
        diff_tokenizer_path: str,
        msg_tokenizer_name: str,
        blocksize: int,
        clean_temp_files: bool,
        diff_kwargs: Dict[str, Any],
        msg_kwargs: Dict[str, Any],
        chunksize: int,
        data_format: str,
        n_workers: Optional[int] = None,
        logger_name: Optional[str] = None,
    ):
        super().__init__(chunksize=chunksize, logger_name=logger_name, n_workers=n_workers, data_format=data_format)
        self._diff_tok = PreTrainedTokenizerFast(tokenizer_file=diff_tokenizer_path)
        self._msg_tok = AutoTokenizer.from_pretrained(msg_tokenizer_name)
        self._data_format = data_format
        self._chunksize = chunksize
        self._blocksize = blocksize
        self._clean_temp_files = clean_temp_files
        self._diff_kwargs = diff_kwargs
        self._msg_kwargs = msg_kwargs

    def _tokenize_diffs(self, diffs: List[str]) -> List[List[int]]:
        return self._diff_tok(diffs, **self._diff_kwargs).input_ids

    def _tokenize_messages(self, msgs: List[str]) -> List[List[int]]:
        return self._msg_tok(msgs, **self._msg_kwargs).input_ids

    def _preprocess_data(self, in_fname: str, output_dir: str, part: str):
        """
        This method:
        - adds info about position in history to each example
        - (only for train part) shuffles data
        - saves results to separate file
        Note: assumes that commits from each author are already in correct order for history.
        """
        df = self._read_input(in_fname, read_lazy=True, blocksize=self._blocksize)
        df["pos_in_history"] = df.groupby("author").cumcount()

        if part == "train":
            df = df.sample(frac=1.0, random_state=123)

        self._prepare_outfile(os.path.join(output_dir, f"temp_{part}"))

        for partition in tqdm(df.partitions, desc=f"Saving data in blocks (~{self._blocksize * 1e-7} Mb)"):
            partition = partition.compute()
            partition["date"] = partition["date"].astype(str)
            self._append_to_outfile(partition, os.path.join(output_dir, f"temp_{part}"))

    def _process_messages(self, output_dir: str, part: str):
        """
        This method tokenizes messages, constructs commit message history for each author and saves to separate file.
        """
        reader = self._read_input(os.path.join(output_dir, f"temp_{part}"))

        open(os.path.join(output_dir, f"msgs_{part}.jsonl"), mode="w").close()
        for chunk in tqdm(reader, desc=f"Tokenizing messages in chunks ({self._chunksize} rows)"):
            msg_input_ids = self._tokenize_messages(chunk["message"].tolist())
            chunk["msg_input_ids"] = msg_input_ids

            with jsonlines.open(os.path.join(output_dir, f"msgs_{part}.jsonl"), mode="a") as writer:
                for row in chunk[["msg_input_ids", "author"]].to_dict(orient="records"):
                    writer.write(row)
        df = pd.read_json(os.path.join(output_dir, f"msgs_{part}.jsonl"), orient="records", lines=True)

        history = df[["author", "msg_input_ids"]].groupby("author").agg(list)["msg_input_ids"].to_dict()
        with open(os.path.join(output_dir, f"{part}_history.json"), "w") as outfile:
            json.dump(history, outfile)

    def _process_diffs(self, output_dir: str, part: str):
        """
        This method tokenizes diffs and saves all necessary information for working with commit message history
        to separate file.
        """
        reader = self._read_input(os.path.join(output_dir, f"temp_{part}"))
        open(os.path.join(output_dir, f"{part}.json"), mode="w").close()

        for chunk in tqdm(reader, desc=f"Tokenizing diffs in chunks ({self._chunksize} rows)"):
            diff_input_ids = self._tokenize_diffs(chunk["mods"].tolist())
            chunk["diff_input_ids"] = diff_input_ids

            with jsonlines.open(os.path.join(output_dir, f"{part}.json"), mode="a") as writer:
                for row in chunk[["diff_input_ids", "pos_in_history", "author"]].to_dict(orient="records"):
                    writer.write(row)

    def __call__(self, in_fname: str, output_dir: str, part: str):
        """
        Expects following columns in input file:
        - "author"  - commit author
        - "date"    - commit timestamp
        - "mods"    - commit modifications
        - "message" - commit message
        Note: assumes that commits from each author are already in correct order for history.
        """
        logging.info(f"Start processing {part}")
        self._preprocess_data(in_fname, output_dir, part)
        self._process_messages(output_dir, part)
        self._process_diffs(output_dir, part)
        logging.info(f"Finish processing {part}")

        if self._clean_temp_files:
            os.remove(os.path.join(output_dir, f"temp_{part}.{self.data_format}"))
            os.remove(os.path.join(output_dir, f"msgs_{part}.jsonl"))
