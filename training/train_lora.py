"""
LoRA fine-tuning script for either Track B training target (planner or risk
model). This CANNOT be run in the sandbox this project was built in -- no
GPU, and `pip install torch transformers peft bitsandbytes accelerate` isn't
in requirements.txt on purpose (those are heavyweight, training-only deps
that shouldn't bloat the runtime install for a tool that just needs to
call/serve a model, not train one). Install them yourself on your training
machine:

    pip install torch transformers peft bitsandbytes accelerate trl

Usage (on a real GPU machine, after training/prepare_dataset.py has produced
real data -- do not run this against a <50-example toy dataset and expect
a usable model):

    python -m training.train_lora \
        --base-model Qwen/Qwen2.5-3B-Instruct \
        --train-data training/data/risk_model_train.jsonl \
        --output-dir training/output/risk_model_lora \
        --target risk_model

Every CLI flag below maps directly to a line in
training/model_card_template.md -- fill that out from the values you
actually used, not from this script's defaults, since the defaults are a
reasonable starting point, not a recommendation you should treat as final
without your own tuning.
"""
from __future__ import annotations

import argparse
import json


def _load_jsonl_dataset(path: str):
    """Deferred import of `datasets` so this module can be imported (e.g.
    by tests checking --help output) without the heavyweight training deps
    installed."""
    from datasets import load_dataset

    return load_dataset("json", data_files=path, split="train")


def build_lora_config(rank: int, alpha: int, target_modules: list[str]):
    from peft import LoraConfig, TaskType

    return LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=0.05,
        target_modules=target_modules,
        task_type=TaskType.CAUSAL_LM,
        bias="none",
    )


def train(
    base_model: str,
    train_data_path: str,
    output_dir: str,
    target: str,
    rank: int = 16,
    alpha: int = 32,
    epochs: int = 3,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
) -> None:
    # Deferred imports: this function is what actually needs the heavyweight
    # training stack, kept out of this module's top-level imports so the
    # rest of this file (build_lora_config, argument parsing) stays testable
    # without those deps installed.
    from peft import get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    print(f"[training] target={target} base_model={base_model}")
    print(
        "[training] Reminder (TRD.md §6): confirm this base model ships with intact "
        "safety training before proceeding. LoRA fine-tuning here must not be used to "
        "remove or weaken it -- if you are unsure, stop and read docs/TRD.md §6 and "
        "docs/CODE_LOGIC.md's note on the excluded 'de-safetied model' repo pattern."
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model, device_map="auto")

    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]  # standard for Qwen/Llama-family attention
    lora_config = build_lora_config(rank, alpha, target_modules)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = _load_jsonl_dataset(train_data_path)

    def _format(example):
        text = tokenizer.apply_chat_template(example["messages"], tokenize=False)
        return {"text": text}

    dataset = dataset.map(_format)

    def _tokenize(example):
        return tokenizer(example["text"], truncation=True, max_length=1024)

    tokenized = dataset.map(_tokenize, remove_columns=dataset.column_names)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        report_to=[],  # wire up langfuse/wandb here if desired, per docs/CODE_LOGIC.md §14
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized)
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    print(f"[training] Adapter saved to {output_dir}")
    print(
        "[training] NEXT STEP (mandatory for target=risk_model, strongly recommended for "
        "target=planner): run eval/adversarial_boundary_eval.py --model local against a "
        "server hosting this adapter BEFORE wiring it into a live .env. See eval/README.md "
        "for the pass thresholds, and fill out training/model_card_template.md with the "
        "exact values used in this run."
    )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", required=True, help="e.g. Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--train-data", required=True, help="jsonl from training/prepare_dataset.py")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target", choices=["planner", "risk_model"], required=True)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--alpha", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    train(
        base_model=args.base_model,
        train_data_path=args.train_data,
        output_dir=args.output_dir,
        target=args.target,
        rank=args.rank,
        alpha=args.alpha,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    _main()
