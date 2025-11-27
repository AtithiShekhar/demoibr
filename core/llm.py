# core/llm.py - UPDATED WITH JSON GENERATION
from typing import Optional, List, Mapping, Any
from langchain.llms.base import LLM
import google.generativeai as genai
from core.config import get_api_key
import json
import re

class GeminiLLM(LLM):
    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.0
    max_output_tokens: int = 8192

    model: Any = None

    @property
    def _llm_type(self) -> str:
        return "gemini"

    def __init__(self, model_name="gemini-2.0-flash", temperature=0.0, max_output_tokens=8192):
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
        """Answer a user question based on provided context from ChromaDB."""
        prompt = f"""You are a helpful medical information assistant. Answer based ONLY on the provided context.

CONTEXT FROM DATABASE:
{context}

USER QUESTION: {question}

ANSWER:"""
        return self._call(prompt)
    
    def generate_clinical_json(self, patient_data: dict, medications_context: dict) -> dict:
        """
        Generate Fit-Med clinical assessment as structured JSON.
        
        Args:
            patient_data: Patient details dict
            medications_context: Dict of {medication_name: chromadb_context}
            
        Returns:
            dict: Structured clinical assessment report
        """
        # Build context for each medication
        med_contexts_text = ""
        for med_name, context in medications_context.items():
            med_contexts_text += f"\n{'='*80}\n"
            med_contexts_text += f"MEDICATION: {med_name}\n"
            med_contexts_text += f"{'='*80}\n"
            med_contexts_text += f"{context}\n"
        
        prompt = f"""You are Fit-Med — a clinical medication safety and optimization assistant.

Generate a comprehensive clinical medication assessment in VALID JSON format.

PATIENT INFORMATION:
{json.dumps(patient_data, indent=2)}

MEDICATION DATABASE INFORMATION:
{med_contexts_text}

CRITICAL INSTRUCTIONS:
1. Use ONLY information from the database context above
2. If information is missing, use "Information not found in database"
3. Output MUST be valid JSON with this EXACT structure:

{{
  "patient_details": {{
    "age": <int>,
    "gender": "<string>",
    "diagnosis": "<string>",
    "smoking_alcohol": "<string>",
    "date_of_assessment": "<YYYY-MM-DD>"
  }},
  "medication_assessments": [
    {{
      "medication": "<medication_name>",
      "indication": ["<indication1>", "<indication2>"],
      "benefits_specific_to_patient": "<detailed benefits>",
      "risks_and_interactions": "<risks and drug interactions>",
      "strength_of_evidence": "<strength or 'Information not found in database'>",
      "risk_minimisation_measures": ["<measure1>", "<measure2>"],
      "fit_med_outcome": "<Favorable|Conditional|Unfavorable>",
      "recommendation": "<clinical recommendation>"
    }}
  ],
  "monitoring_protocol": [
    {{
      "medication": "<medication_name>",
      "monitoring_parameters": ["<param1>", "<param2>"],
      "frequency": "<frequency>"
    }}
  ],
  "summary": [
    {{
      "medication": "<medication_name>",
      "recommendation": "<brief recommendation>"
    }}
  ]
}}

ASSESSMENT CRITERIA:
- Favorable: Benefits clearly outweigh risks, appropriate for patient
- Conditional: Benefits outweigh risks with proper monitoring/precautions
- Unfavorable: Risks outweigh benefits, consider alternatives

Generate the JSON report now (output ONLY valid JSON, no markdown, no explanation):"""

        response = self._call(prompt)
        
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_str = response.strip()
        
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Failed to parse JSON response: {e}")
            print(f"Raw response:\n{response[:500]}...")
            # Return error structure
            return {
                "error": "Failed to generate valid JSON",
                "raw_response": response
            }

