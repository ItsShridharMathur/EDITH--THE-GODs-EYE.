from groq import Groq

SYSTEM_PROMPT = """You are EDITH, a helpful desktop AI assistant.
Rules:
1) Be concise and practical.
2) Prefer safe guidance.
3) If user asks risky/destructive actions, require confirmation.
4) For technical questions, give structured bullet points where useful.
"""

class GroqClient:
    def __init__(self, config):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL

    async def chat(self, user_input: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.3,
            max_tokens=900,
        )
        return completion.choices[0].message.content or "No response."