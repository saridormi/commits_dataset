import os
from dataclasses import dataclass

import hydra
from hydra.core.config_store import ConfigStore
from hydra.utils import to_absolute_path
from omegaconf import DictConfig

from src import TrainingProcessor


@dataclass
class DiffTokenizerConfig:
    truncation: bool = True
    max_length: int = 500
    return_attention_mask: bool = False


@dataclass
class MsgTokenizerConfig:
    truncation: bool = True
    return_attention_mask: bool = False


@dataclass
class ProcessingConfig:
    input_path: str = "data/marker_tests.csv"
    output_path: str = "processed"

    diff_tokenizer_path: str = "data/diff_tokenizer.json"
    msg_tokenizer_name: str = "distilgpt2"
    diff_kwargs: DiffTokenizerConfig = DiffTokenizerConfig()
    msg_kwargs: MsgTokenizerConfig = MsgTokenizerConfig()


cs = ConfigStore.instance()
cs.store(name="config", node=ProcessingConfig)


@hydra.main(config_path=None, config_name="config")
def main(cfg: DictConfig):
    cfg.input_path = to_absolute_path(cfg.input_path)
    cfg.output_path = to_absolute_path(cfg.output_path)
    cfg.diff_tokenizer_path = to_absolute_path(cfg.diff_tokenizer_path)
    os.makedirs(cfg.output_path, exist_ok=True)

    processor = TrainingProcessor(**cfg)
    processor(in_fname=cfg.input_path, output_dir=cfg.output_path)


if __name__ == "__main__":
    main()
