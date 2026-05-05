
import torch

class QwenLLM:

    def __init__(self, model, tokenizer, device="cuda"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def generate(self, prompt: str) -> str:

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True
        )

        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                temperature=0.0,
                top_p=1.0,
                top_k=0,
                repetition_penalty=1.0,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True
        )

        return text.strip()
