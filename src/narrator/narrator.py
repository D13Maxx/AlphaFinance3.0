class DeterministicNarrator:

    @staticmethod
    def narrate(structured_output: dict) -> str:
        mode = structured_output.get("mode")

        lines = [f"Analysis Mode: {mode}"]

        for key, value in structured_output.items():
            if key == "mode":
                continue
            lines.append(f"{key}: {value}")

        return "\n".join(lines)


class LLMBasedNarrator:

    def __init__(self, llm):
        self.llm = llm

    def narrate(self, structured_output: dict) -> str:
        prompt = self._build_prompt(structured_output)
        return self.llm.generate(prompt)

    def _build_prompt(self, structured_output: dict) -> str:
        return (
            "You are a financial analyst.\n"
            "You are given structured financial analysis results.\n"
            "Do NOT compute new values.\n"
            "Do NOT infer missing data.\n"
            "Only convert structured information into a concise professional summary.\n\n"
            f"Structured Data:\n{structured_output}\n\n"
            "Write a concise analysis paragraph."
        )
