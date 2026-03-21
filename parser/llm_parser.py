#app/parser/llm_parser.py

"""
Match jobs against CV using Groq LLM
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Tuple
import re
import PyPDF2
from openai import OpenAI
from app.utils.llm_prompt import build_prompt

def normalize_text(text: str) -> str:
    """
    Normalize text to reduce LLM variability.
    """
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


class GroqMatcher:
    """
    Match jobs against CV using Groq models
    """

    def __init__(self, api_key: str, cv_path: Path):

        self.cv_path = Path(cv_path)

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

        self.cv_text = normalize_text(self._extract_cv_text())

    def _extract_cv_text(self) -> str:
        """
        Extract text from CV PDF
        """

        try:

            with open(self.cv_path, "rb") as f:

                reader = PyPDF2.PdfReader(f)

                text = ""

                for page in reader.pages:

                    extracted = page.extract_text()

                    if extracted:
                        text += extracted

                return text

        except Exception as e:

            print("CV read error:", e)

            return ""

    async def match_job(self, job: Dict) -> Dict:
        """
        Evaluate job relevance against CV
        """

        prompt = await build_prompt(job, self.cv_text)

        try:

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert recruiter evaluating job relevance."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                top_p=0.0
            )

            text = response.choices[0].message.content

            return self._parse_response(text)

        except Exception as e:

            return {"score": 0.0, "reasoning": f"Error: {str(e)}"}

    def _parse_response(self, response: str):
        """Parse LLM response - non-recursive with fallbacks."""
        
        # Clean markdown fences
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Try to extract JSON block if mixed with text
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            response = response[json_start:json_end]
        

        
        # First attempt: parse as-is
        try:
            data = json.loads(response)
            score = float(data.get("score", 0))
            reasoning = data.get("reasoning", "")
            print(response)
            return {"score": score, "reasoning": reasoning}
        except json.JSONDecodeError:
            pass
        
        # Second attempt: fix common JSON errors
        try:
            fixed = response.replace("'", '"')  # Single quotes
            fixed = fixed.replace(",}", "}")    # Trailing commas in objects
            fixed = fixed.replace(",]", "]")    # Trailing commas in arrays
            
            data = json.loads(fixed)
            score = float(data.get("score", 0))
            reasoning = data.get("reasoning", "")
            
            return {"score": score, "reasoning": reasoning}
        except json.JSONDecodeError:
            pass
        
        # Third attempt: extract score with regex (no recursion)
        score_match = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', response)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', response)
        
        if score_match:
            score = float(score_match.group(1))
            reasoning = reasoning_match.group(1) if reasoning_match else "Partial parse"
            return {"score": score, "reasoning": reasoning}
        
        # Final fallback: return error
        print(f"[!] Failed to parse response")
        print(f"Response preview: {response[:300]}")
        return {"score": 0.0, "reasoning": "Failed to parse JSON"}



async def process_job(matcher, job):
    semaphore = asyncio.Semaphore(8)

    async def safe_match(job):
        async with semaphore:
            return await matcher.match_job(job)

    return await safe_match(job)



