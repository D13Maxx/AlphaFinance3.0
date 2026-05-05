
import time
import torch
import psutil
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.llm.qwen_llm import QwenLLM

def get_vram_usage():
    if torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / 1024**3
    return 0.0

def benchmark():
    print("Starting Benchmark...")
    
    # 1. Model Loading
    print("Loading Model (Qwen/Qwen2.5-7B-Instruct) in 4-bit...")
    start_load = time.time()
    
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            load_in_4bit=True,
            trust_remote_code=True
        )
    except Exception as e:
        print(f"FAILED to load model: {e}")
        return

    load_time = time.time() - start_load
    print(f"Model Load Time: {load_time:.2f}s")
    print(f"VRAM Usage after load: {get_vram_usage():.2f} GB")
    
    # 2. Wrapper Init
    llm = QwenLLM(model, tokenizer)
    
    # 3. Query Latency
    query = "What is the net income for 2023? Explain with citations."
    prompt = f"<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"
    
    print(f"\nGeneratin response for: '{query}'")
    start_gen = time.time()
    try:
        response = llm.generate(prompt)
    except Exception as e:
        print(f"Generation FAILED: {e}")
        return

    gen_time = time.time() - start_gen
    print(f"Response: {response[:100]}...")
    print(f"Real Query Latency: {gen_time:.4f}s")
    print(f"VRAM Usage after generation: {get_vram_usage():.2f} GB")
    
    # 4. Check for CUDA errors (implicit in execution, but can check explicit)
    if torch.cuda.is_available():
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA NOT AVAILABLE")

if __name__ == "__main__":
    benchmark()
