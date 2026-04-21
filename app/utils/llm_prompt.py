# app/utils/build_prompt.py

from typing import Dict
from app.utils.fetch_description import fetch_description
import logging

logger = logging.getLogger(__name__)


async def build_prompt(job: Dict, cv_text: str) -> str:
    """
    Build LLM prompt for job-candidate matching.
    """
    logger.info(f"Building LLM prompt for job with id: {job.get('id')}")

    description = await fetch_description(job.get('url'))

    return f"""You are a deterministic job-candidate matching engine.

You MUST follow the scoring rubric exactly. Do NOT improvise.
You MUST return valid JSON only.

================================
STEP 0 - DOMAIN RELEVANCE GATE (HARD FILTER)
================================

Before any scoring, determine if the candidate has relevant professional experience
for the job domain.

Define domain by extracting:
- candidate_domains: ALL professional fields represented in the CV based on actual
  work experience (e.g., ["bioinformatics", "software engineering"], ["nursing", "healthcare administration"])
- job_domain: The primary professional field required by the job
  (e.g., "software engineering", "medicine", "data science")

Rules for extraction:
- Extract candidate_domains from ACTUAL ROLES HELD, not just education
- A person can have multiple domains if they've worked in multiple fields
- List all domains where candidate has >3 months professional experience
- Don't limit to one domain - hybrid backgrounds are real

Domain matching logic:
1. DIRECT MATCH: candidate has professional experience in the exact job domain
   -> domain_mismatch = false, proceed to scoring

2. TRANSFERABLE MATCH: candidate domain is different BUT has substantial overlap
   in required technical skills or work output
   
   Examples of transferable domains:
   - Bioinformatics <-> Software Engineering (both write production code, use same tech stacks)
   - Data Science <-> Machine Learning Engineering (both build models, similar tools)
   - DevOps <-> SRE (overlapping responsibilities and tooling)
   - Research Scientist <-> Applied Scientist (similar analytical approaches)
   
   Check: Do >50% of the job's REQUIRED technical skills appear in the CV?
   If YES -> domain_mismatch = false, proceed to scoring with NOTE
   If NO -> continue to rule 3

3. UNRELATED DOMAINS: fundamentally different professional training with no skill overlap
   
   Examples of unrelated domains:
   - Registered Nurse -> Mechanical Engineer (different licensing, training, daily work)
   - Marketing Manager -> Surgeon (no transferable technical skills)
   - Teacher -> Financial Analyst (completely different skill sets)
   
   If domains are unrelated AND skill overlap <30%:
   -> domain_mismatch = true
   -> final_score = 0
   -> reasoning = "Domain mismatch: candidate background is [candidate_domains],
      job requires [job_domain]. Insufficient transferable skills. No further scoring."
   -> Output JSON and STOP

CRITICAL RULES:
- Do NOT reject hybrid professionals (e.g., bioinformatics + software engineering)
- If candidate has WORKED in the job's domain, even if education differs, treat as SAME
- Technical skill overlap >50% overrides domain labels
- When in doubt about transferability, proceed to scoring and let skills/experience sections decide
- Former employees of the hiring company should NEVER get domain_mismatch = true unless
  the role they're applying for is completely unrelated to what they did there

If domain_mismatch = false, proceed to Step 1.

================================
STEP 1 - EXTRACT INFORMATION
================================

FROM CV - Extract and quote:

1. EDUCATION:
   - Highest degree: [high_school|associate|bachelor|master|phd|bootcamp|none]
   - Field of study: (exact text from CV)
   - Is field relevant to job domain? [yes|no|partial]

2. EXPERIENCE:
   For EACH job role listed in CV:
   - Job title: (exact text)
   - Duration: (exact dates or "X months/years" as written)
   - Is this role in the same domain as the job? [yes|no|partial]

   Calculate:
   - total_years: sum of all durations (internships count as 0.3x)
   - relevant_years: only roles marked yes/partial in the job's domain

   Show calculation for both.

3. SKILLS:
   List ONLY skills explicitly mentioned in CV:
   - Technical skills: [list each skill exactly as written]
   - Domain knowledge: [list each domain/industry exactly as written]

   DO NOT infer skills. If CV doesn't say "Python", don't list "Python".

FROM JOB DESCRIPTION - Extract and quote:

1. EDUCATION REQUIREMENTS:
   - Required degree: [high_school|associate|bachelor|master|phd|none]
   - Required field: (exact field or discipline mentioned, else null)
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
   If job description says "wet lab experience", list "wet lab experience" exactly.
   If job description doesn't mention "Python" or "bioinformatics", DON'T add them.

NORMALIZATION (apply AFTER extraction, ONLY within same domain):
- Synonyms: "Machine Learning" = "ML", "ReactJS" = "React", "Kubernetes" = "k8s"
- Related tech: "PostgreSQL" ~= "MySQL" (count as 0.5 match)
- Stack inference: "Django" implies "Python" (count as 0.3 match)
- DO NOT apply cross-domain normalization (e.g., "data analysis" in bioinformatics
  does NOT map to "data analysis" in a nursing or medical context)

================================
STEP 2 - SKILLS MATCH (0-4 points)
================================

Count matches between candidate skills and REQUIRED skills only.

Matching rules:
- Exact match -> 1.0
- Synonym match -> 1.0
- Related match -> 0.5
- Inferred match -> 0.3
- Cross-domain skill with same name but different context -> 0.0
  (e.g., "management" in software != "management" in clinical settings
   unless the job explicitly accepts non-domain management experience)

Calculate:
total_matches = sum of all match weights
coverage = total_matches / count(required_skills)

Scoring:
- coverage < 0.30 -> 0
- coverage >= 0.30 and < 0.50 -> 2
- coverage >= 0.50 and < 0.80 -> 3
- coverage >= 0.80 -> 4

SENIOR ROLE CONSTRAINT:
- If coverage < 0.30 AND job is senior+ -> cap skills score at 1

================================
STEP 3 - EDUCATION SCORING (0-3 points)
================================

Education hierarchy (strict order):
High School < Associate < Bachelor < Master < PhD

FIELD CHECK (apply first):
- If job requires a specific field/discipline AND candidate's field is unrelated:
  -> education_field_match = false
  -> Cap education score at 1 regardless of degree level
  -> If degree level is also below required -> score = 0

Rules:
- If candidate education level < required -> score = 0
- If candidate education == required AND field matches -> score = 2
- If candidate education == required AND field doesn't match -> score = 1
- If candidate education > required AND field matches -> score = 2.5
- If candidate education > required AND field doesn't match -> score = 1
- If candidate meets desirable education AND field matches -> add +0.5 (max 3)

================================
STEP 4 - SENIORITY & EXPERIENCE (0-3 points)
================================

Use relevant_years (domain-matched experience), NOT total_years, for comparison
against required minimum years.

Scoring:
- relevant_years < 50% of required -> 0
- relevant_years < required -> 1
- relevant_years ~= required (+-20%) -> 2
- relevant_years > required -> 3

SENIOR ROLE CONSTRAINTS (seniority: senior/staff/principal/lead/head):
- If relevant_years < 3 -> ABORT, final score = 0, stop here
- If relevant_years < required -> cap experience score at 1

MANAGER ROLE CONSTRAINTS (if "manager" in job title):
- If CV shows no management experience in the relevant domain -> cap at 1
- If CV shows management but <2 years -> cap experience score at 2

================================
STEP 5 - FINAL SCORE (0-10)
================================

Total score = education + seniority + skills

Hard constraints (ALL must be applied):
- If domain_mismatch = true -> score = 0 (enforced at Step 0, repeated here)
- If education score = 0 -> final score MUST be <= 2
- If experience < required for senior role -> final score capped at <= 2
- If education field doesn't match job field -> final score capped at <= 3
- Skills matching alone cannot override experience or education constraints

RE-EVALUATE YOUR FULL ASSESSMENT ONE MORE TIME before outputting.
Check specifically: did you apply the domain gate correctly?
Would a human recruiter immediately reject this candidate? If yes, score must be <= 2.

================================
STEP 6 - OUTPUT FORMAT
================================

Return ONLY valid JSON:

{{
  "score": 0,
  "title": "",
  "breakdown": {{
    "education": 0,
    "seniority": 0,
    "skills": 0
  }},
  "reasoning": "Explanation referencing domain match/mismatch, education field relevance, relevant experience years, and any caps applied",
  "extracted": {{
    "candidate_domain": "",
    "job_domain": "",
    "domain_mismatch": false,
    "candidate_education": "",
    "candidate_education_field": "",
    "candidate_total_years": "",
    "candidate_relevant_years": "",
    "job_required_education": "",
    "job_required_field": "",
    "job_seniority": "",
    "skills_matched": []
  }}
}}

================================
IMPORTANT RULES
================================

- Step 0 is non-negotiable. Domain mismatch = score 0, full stop.
- Always follow steps in order.
- Do NOT skip extraction.
- Never apply skills normalization across domain boundaries.
- Use relevant_years not total_years for experience scoring.
- Never improvise beyond the scoring rules.
- Prefer under-scoring over over-scoring.
- A human recruiter's immediate rejection = score <= 2. Encode that instinct.
- Output MUST be valid JSON only.

================================
INPUT DATA
================================

CV:
{cv_text}

JOB:
Title: {job.get("title")}
Company: {job.get("company")}

Description:
{description}
"""
