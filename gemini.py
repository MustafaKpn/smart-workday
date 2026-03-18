"""
Match jobs against CV using Groq LLM
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Tuple
import re
import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv

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

    async def match_job(self, job: Dict) -> Tuple[float, str]:
        """
        Evaluate job relevance against CV
        """

        prompt = self._build_prompt(job)

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

            return (0.0, f"Error: {str(e)}")

    def _build_prompt(self, job: Dict) -> str:
        """
        Build LLM prompt
        """

        return f"""
You are a deterministic job–candidate matching engine.

You MUST follow the scoring rubric exactly. Do NOT improvise.
You MUST return valid JSON only.

--------------------------------
STEP 1 — EXTRACT INFORMATION
--------------------------------

From the CV, extract:
- highest education level
- total years of experience
- key skills (technical + domain)

From the job description, extract:
- required education (mandatory)
- desirable education (optional)
- required skills
- years of experience required
- seniority level (junior, mid, senior, lead)

--------------------------------
STEP 2 — EDUCATION SCORING (0–3 points)
--------------------------------

Education hierarchy (strict order):
High School < Associate < Bachelor < Master < PhD

Rules:
- If candidate education < required → score = 0
- If candidate education == required → score = 2
- If candidate education > required → score = 2.5
- If candidate meets desirable education → add +0.5 (max 3)

--------------------------------
STEP 3 — SENIORITY & EXPERIENCE (0–3 points)
--------------------------------

Compare candidate experience vs job requirement:

- If candidate is significantly underqualified → 0
- Slightly underqualified → 1
- Matches requirement → 2
- Exceeds requirement → 3

--------------------------------
STEP 4 — SKILLS MATCH (0–4 points)
--------------------------------

Compare required skills vs candidate skills:

- <30% match → 0
- 30–50% → 1
- 50–70% → 2
- 70–90% → 3
- >90% → 4

--------------------------------
STEP 5 — FINAL SCORE (0–10)
--------------------------------

Total score = education + seniority + skills

Hard constraints:
- If education score = 0 → final score MUST be ≤ 2
- If skills match <30% → final score MUST be ≤ 3

--------------------------------
STEP 6 — OUTPUT FORMAT
--------------------------------

Return ONLY valid JSON:

{{
  "score": 0,
  "breakdown": {{
    "education": 0,
    "seniority": 0,
    "skills": 0
  }},
  "reasoning": "Concise explanation referencing education, experience, and skills",
  "extracted": {{
    "candidate_education": "",
    "candidate_experience_years": "",
    "job_required_education": "",
    "job_seniority": "",
    "skills_matched": []
  }}
}}

--------------------------------
IMPORTANT RULES
--------------------------------

- Be strict and consistent.
- Do NOT inflate scores.
- Do NOT guess missing qualifications — assume missing = not present.
- Prefer under-scoring over over-scoring.
- Output MUST be valid JSON only.

--------------------------------
INPUT DATA
--------------------------------

CV:
{self.cv_text}

JOB:
Title: {job.get("title")}
Company: {job.get("company")}
Location: {job.get("location", "N/A")}

Description:
{job.get("description", "N/A")[:4000]}
"""

    def _parse_response(self, response: str):
        response = response.strip().replace("```json", "").replace("```", "")
        try:
            data = json.loads(response)
            score = float(data.get("score", 0))
            reasoning = data.get("reasoning", "")
            print(response)
            return score, reasoning
        except json.JSONDecodeError:
            # fallback: try regex extraction
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return self._parse_response(match.group(0))
            return 0.0, "Failed to parse JSON"


async def process_jobs(matcher, jobs):
    """
    Run job scoring with concurrency control
    """

    semaphore = asyncio.Semaphore(8)

    async def safe_match(job):

        async with semaphore:

            return await matcher.match_job(job)

    tasks = [safe_match(job) for job in jobs]

    return await asyncio.gather(*tasks)


def main():

    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:

        print("Set GROQ_API_KEY environment variable")
        return

    matcher = GroqMatcher(
        api_key=api_key,
        cv_path="./CV_SE.pdf"
    )

    with open("./jobs.json") as f:
        jobs_data = json.load(f)

    jobs = jobs_data["jobs"]

    results = asyncio.run(process_jobs(matcher, jobs))

    for job, result in zip(jobs, results):
        score, reasoning = result

        print("\n-----------------------------------")
        print("TITLE:", job.get("title"))
        print("COMPANY:", job.get("company"))
        print("SCORE:", score)
        print("REASON:", reasoning)


if __name__ == "__main__":
    main()



