#app/utils/build_prompt.py

from typing import Dict
from app.utils.fetch_description import fetch_description


async def build_prompt(job: Dict, cv_text: str) -> str:
        """
        Build LLM prompt
        """

        description = await fetch_description(job.get('url'))

        return f"""
You are a deterministic job–candidate matching engine.

You MUST follow the scoring rubric exactly. Do NOT improvise.
You MUST return valid JSON only.

--------------------------------
STEP 1 — EXTRACT INFORMATION
--------------------------------

FROM CV - Extract and quote:

1. EDUCATION:
   - Highest degree: [high_school|associate|bachelor|master|phd|bootcamp|none]
   - Field of study: (exact text from CV)

2. EXPERIENCE:
   For EACH job role listed in CV:
   - Job title: (exact text)
   - Duration: (exact dates or "X months/years" as written)
   
   Calculate total years:
   - Add up all durations
   - If dates overlap, don't double-count
   - Internships count as 0.3x
   
   Total years = _____ (show calculation)

3. SKILLS:
   List ONLY skills explicitly mentioned in CV:
   - Technical skills: [list each skill exactly as written]
   - Domain knowledge: [list each domain/industry exactly as written]
   
   DO NOT infer skills. If CV doesn't say "Python", don't list "Python".

FROM JOB DESCRIPTION - Extract and quote:

1. EDUCATION REQUIREMENTS:
   - Required degree: [high_school|associate|bachelor|master|phd|none]
   - Preferred degree: (if mentioned, else null)
   - Quote from job description: "______"

2. EXPERIENCE REQUIREMENTS:
   - Minimum years: (number, or 0 if not stated)
   - Seniority level: [intern|junior|associate|mid|senior|staff|principal|lead|head|manager]
   - Quote from job description: "______"

3. SKILLS REQUIREMENTS:
   List ONLY skills explicitly mentioned in job description:
   - Required skills: [list each skill exactly as written in the job posting]
   - Preferred skills: [list each preferred skill if mentioned]
   
   CRITICAL: DO NOT add skills that aren't in the job description.
   If job description says "wet lab experience", list "wet lab experience" - don't break it into sub-skills.
   If job description doesn't mention "Python" or "bioinformatics", DON'T add them.

NORMALIZATION (apply AFTER extraction):
- Synonyms: "Machine Learning" = "ML", "ReactJS" = "React", "Kubernetes" = "k8s"
- Related tech: "PostgreSQL" ≈ "MySQL" (count as 0.5 match)
- Stack inference: "Django" implies "Python" (count as 0.3 match)

--------------------------------
STEP 2 — SKILLS MATCH (0–4 points)
--------------------------------

Count matches between candidate skills and required skills.

Matching rules:
- Exact match (e.g., both say "Python") → count as 1.0
- Synonym match (e.g., "ML" vs "Machine Learning") → count as 1.0
- Related match (e.g., "MySQL" vs "PostgreSQL") → count as 0.5
- Inferred match (e.g., "Django" for "Python" requirement) → count as 0.3

Calculate:
total_matches = sum of all match weights
coverage = total_matches / count(required_skills)

Scoring:
- coverage < 0.30 → 0
- coverage < 0.50 → 2
- coverage >= 0.50 and < 0.70 → 3
- coverage >= 0.80 → 4

SENIOR ROLE CONSTRAINT:
- If coverage < 0.30 AND job is senior+ → cap skills score at 1

--------------------------------
STEP 3 — EDUCATION SCORING (0–3 points)
--------------------------------

Education hierarchy (strict order):
High School < Associate < Bachelor < Master < PhD

Rules:
- If candidate education < required → score = 0
- If candidate education == required → score = 2
- If candidate education > required → score = 2.5
- If candidate meets desirable education → add +0.5 (max 3)

--------------------------------
STEP 4 — SENIORITY & EXPERIENCE (0–3 points)
--------------------------------
Compare candidate total_years vs required minimum years.

Scoring:
- candidate < 50% of required → 0
- candidate < required → 1
- candidate ≈ required (±20%) → 2
- candidate > required → 3

SENIOR ROLE CONSTRAINTS (if seniority is senior/staff/principal/lead/head):
- If candidate total_years < 3 → ABORT, final score = 0, stop here
- If candidate total_years < required → cap experience score at 1

MANAGER ROLE CONSTRAINTS (if "manager" in job title):
- If CV shows no management experience → cap experience score at 1

--------------------------------
STEP 5 — FINAL SCORE (0–10)
--------------------------------

Total score = education + seniority + skills

Hard constraints:
- DON'T improvise skills
- If education score = 0 → final score MUST be ≤ 2
- If experience < required for senior role → final score capped at ≤ 2
- Skills matching alone cannot override experience or education constraints
  If seniority_level ∈ [senior, staff, principal, lead]:
    - If total_years < 3 → ABORT, set final_score = 0, stop evaluation
    - If relevant_years < 2 → cap experience_score at 1
    - If role_progression != senior_track → cap experience_score at 2

  If role_type = manager:
    - If CV shows no management experience → cap experience_score at 1
    - If CV shows management but <2 years → cap experience_score at 2

RE-EVALUATE YOUR ASSESSMENT ONE MORE THME (TOTAL OF 2)

--------------------------------
STEP 6 — OUTPUT FORMAT
--------------------------------

Return ONLY valid JSON:

{{
  "score": 0,
  "title": "",
  "breakdown": {{
    "education": 0,
    "seniority": 0,
    "skills": 0
  }},
  "reasoning": "Explanation referencing education, experience, and skills, and any caps applied due to seniority mismatch",
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

- Always follow steps in order.
- Do NOT skip extraction.
- Never improvise beyond the scoring rules.
- Prefer under-scoring over over-scoring.
- Follow hard constraints for senior roles strictly.
- Output MUST be valid JSON only.

--------------------------------
INPUT DATA
--------------------------------

CV:
{cv_text}

JOB:
Title: {job.get("title")}
Company: {job.get("company")}

Description:
{description}
"""