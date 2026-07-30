from datasets import Dataset
from unsloth import FastLanguageModel
from unsloth_zoo.mlx.trainer import MLXTrainer, MLXTrainingConfig


def main():
    # Load Qwen 2.5 Coder (7B or 14B)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="Qwen/Qwen2.5-Coder-7B",
        max_seq_length=2048,
        dtype=None,  # Auto-detect bfloat16/float16
        load_in_4bit=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=128,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0.1,
        bias="none",
        use_gradient_checkpointing=True,
    )

    with open("pep742_data.txt", "r") as f:
        texts = f.read().split("\n\n")

    # MLXTrainer auto-tokenizes via dataset_text_field — no manual tokenization needed
    dataset = Dataset.from_dict({"text": texts})

    training_args = MLXTrainingConfig(
        output_dir="./results",
        per_device_train_batch_size=4,
        num_train_epochs=3,
        logging_steps=10,
        report_to="none",
        max_seq_length=256,
    )

    trainer = MLXTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=training_args,
        dataset_text_field="text",
    )

    trainer.train()

    # MLX-native inference (model.generate is monkey-patched by unsloth)
    prompt = "Write a Python 3.14 script using the new type statement for a Matrix alias."
    output = model.generate(prompt, max_new_tokens=100)
    print(output)

    # Save the model
    model.save_pretrained("./qwen2.5-coder-pep742")
    tokenizer.save_pretrained("./qwen2.5-coder-pep742")


if __name__ == "__main__":
    main()
