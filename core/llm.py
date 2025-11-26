# core/llm.py
from typing import Optional, List, Mapping, Any
from langchain.llms.base import LLM
import google.generativeai as genai
from core.config import get_api_key

class GeminiLLM(LLM):
    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.0
    max_output_tokens: int = 2048

    model: Any = None

    @property
    def _llm_type(self) -> str:
        return "gemini"

    def __init__(self, model_name="gemini-2.0-flash", temperature=0.0, max_output_tokens=2048):
        super().__init__()
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        api_key = get_api_key()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                }
            )
        except Exception as e:
            return f"[Gemini Error] {str(e)}"

        try:
            output = response.text
        except:
            output = str(response)

        if stop:
            for s in stop:
                idx = output.find(s)
                if idx != -1:
                    output = output[:idx]
        return output

    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name, "temperature": self.temperature}
