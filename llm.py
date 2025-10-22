import os, httpx, asyncio

class LLM:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.key = os.getenv("LLM_API_KEY")

    async def answer(self, prompt: str) -> str:
        # Fallback if no key configured
        if not self.key:
            # Return the prompt tail after 'Користувач:' to simulate a summary-like reply
            return "⚠️ LLM API key is not configured. Повертаю резюме з контексту:\n\n" + prompt[-1200:]
        if self.provider == "openai":
            headers = {"Authorization": f"Bearer {self.key}"}
            body = {"model": self.model, "messages": [{"role":"user","content":prompt}]}
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        raise NotImplementedError("Unsupported LLM provider")
