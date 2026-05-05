import requests

class OllamaLLM:

    def __init__(self,
                 model_name: str = "qwen2.5:7b-instruct",
                 base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.url = f"{base_url}/api/generate"

    def generate(self, prompt: str) -> str:

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 256
            }
        }

        response = requests.post(self.url, json=payload)
        response.raise_for_status()

        data = response.json()

        if "response" not in data:
            raise RuntimeError("Invalid response from Ollama")

        return data["response"].strip()
