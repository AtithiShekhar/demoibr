

# core/llm.py - COMPLETE UPDATED VERSION
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
    
    def answer_question(self, question: str, context: str) -> str:
        """
        Answer a user question based on provided context from ChromaDB.
        
        Args:
            question: The user's question
            context: Retrieved context from ChromaDB
            
        Returns:
            str: The LLM's answer based on the context
        """
        prompt = f"""You are a helpful and knowledgeable medical information assistant. Your role is to answer questions about medications accurately based on the provided database context.

INSTRUCTIONS:
1. Answer the user's question using ONLY the information provided in the context below
2. Be clear, concise, and well-structured in your response
3. If the context contains the answer, provide specific details and cite the relevant information
4. If the context does NOT contain enough information to answer the question, clearly state: "I don't have enough information in the database to answer this question completely."
5. Use bullet points or numbered lists when presenting multiple pieces of information
6. Always prioritize accuracy over completeness - never make up information

CONTEXT FROM DATABASE:
{context}

USER QUESTION: {question}

ANSWER:"""
        
        return self._call(prompt)

