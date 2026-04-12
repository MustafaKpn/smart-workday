# app/utils/build_prompt.py

from typing import Dict
from app.utils.fetch_description import fetch_description
import logging

logger = logging.getLogger(__name__)


async def build_prompt(job: Dict, cv_text: str) -> str:
    """
    Build LLM prompt for job-candidate matching.
    Supports multi-domain candidates (e.g. software eng + bioinformatics + data analysis).
    """
    logger.info(f"Building LLM prompt for job with id: {job.get('id')}")

    description = await fetch_description(job.get('url'))

    prompt = f"""You are a deterministic job-candidate matching engine.

You MUST follow the scoring rubric exactly. Do NOT improvise.
You MUST return valid JSON only.

================================
STEP 0 - BUILD CANDIDATE DOMAIN PROFILE
================================

A candidate may have experience across multiple professional domains.
Do NOT assume a single primary domain. Extract ALL domains the candidate
has genuine experience or education in.

For each domain found in the CV, extract:
- domain: the professional field name (e.g. "software engineering",
  "bioinformatics", "data analysis", "nursing", "mechanical engineering")
- years: total years of experience in that domain (internships count as 0.3x,
  research/academic projects count as 0.2x per project)
- evidence: specific roles, degrees, or projects that justify this domain entry
- depth: [surface|working|substantial]
    surface     = mentioned in passing, coursework only, or < 3 months
    working     = at least one real role/project with deliverables, 3-12 months
    substantial = multiple roles or projects, 12+ months, or advanced degree in field

Rules:
- Only list a domain if the CV has concrete evidence for it (role, project, degree).
- Do NOT infer domains from vague mentions.
- Data analysis is its own domain. Do not conflate with software engineering
  or bioinformatics unless the CV explicitly uses it as a job function.
- Academic research counts toward a domain only at depth=working or above
  if it involved real deliverables (thesis, published pipeline, production tool).

Example output for a multi-domain candidate:
  candidate_domains: [
    {{ "domain": "software engineering", "years": 1.5, "depth": "substantial", "evidence": "THG full-stack role" }},
    {{ "domain": "bioinformatics", "years": 1.3, "depth": "substantial", "evidence": "Illumina internship + MSc research projects" }},
    {{ "domain": "data analysis", "years": 2.0, "depth": "working", "evidence": "statistical analysis across MSc, Illumina, and THG roles" }}
  ]

================================
STEP 1 - DOMAIN GATE (HARD FILTER)
================================

Extract the job's required domain:
- job_domain: the primary professional field the job requires
  (e.g. "software engineering", "data engineering", "nursing", "bioinformatics")
- job_role_type: the specific role type within that domain
  (e.g. "backend", "data engineer", "ML engineer", "surgical nurse", "devops")

Gate logic:
- Check if ANY entry in candidate_domains matches job_domain.
- A match requires:
    1. The domain name is the same or a recognized subset/superset
       (e.g. "bioinformatics" matches "computational biology")
    2. The depth is at least "working"

Domain match taxonomy (use this strictly):

  SAME:
    - software engineering <-> backend engineering
    - software engineering <-> full-stack engineering
    - data analysis <-> data analytics
    - bioinformatics <-> computational biology
    - bioinformatics <-> genomics data science

  RELATED (counts as a weak match, see below):
    - software engineering <-> data engineering
    - software engineering <-> ML engineering
    - bioinformatics <-> data analysis
    - data analysis <-> data engineering

  DIFFERENT (no match, gate fails):
    - software engineering <-> nursing
    - bioinformatics <-> mechanical engineering
    - data analysis <-> surgical care
    - any technical domain <-> any clinical/medical domain
      (unless job explicitly requires both, e.g. "clinical data scientist")

RELATED domain handling:
- If the only match is RELATED (not SAME), set domain_match = "related"
- Do NOT fail the gate. Proceed to scoring.
- Cap the final score at 6 regardless of other scores.
- Apply strict skills threshold in Step 4.

If NO domain in candidate_domains matches job_domain (SAME or RELATED):
  -> Set domain_mismatch = true
  -> Set final_score = 0
  -> Set reasoning = "Domain mismatch: candidate domains are [list], job requires [job_domain]."
  -> Output JSON immediately and STOP. Do not proceed further.

If a match is found:
  -> Set domain_mismatch = false
  -> Set matched_domain = the candidate domain entry that matched
  -> Set domain_match = "exact" or "related"
  -> Proceed to Step 2.

================================
STEP 2 - ROLE TYPE CHECK (WITHIN DOMAIN)
================================

Now check if the candidate's role type within the matched domain aligns
with the job's role type.

Extract candidate_role_type from the matched_domain evidence:
  (e.g. "backend", "full-stack", "data analyst", "bioinformatics scientist",
   "ML engineer", "devops", "frontend")

Compare candidate_role_type vs job_role_type:

  ALIGNED: same or directly transferable
    - full-stack <-> backend
    - data analyst <-> business analyst
    - bioinformatics scientist <-> computational biologist

  ADJACENT: same domain, different specialization, transferable with gaps
    - backend <-> data engineer
    - software engineer <-> ML engineer
    - data analyst <-> data engineer

  DIVERGENT: same broad domain but meaningfully different track
    - frontend <-> data engineer
    - devops <-> data scientist
    - backend <-> embedded systems

Role type scoring impact:
  - ALIGNED   -> no cap from role type
  - ADJACENT  -> cap final score at 7, apply standard skills threshold
  - DIVERGENT -> cap final score at 5, apply strict skills threshold

================================
STEP 3 - EXTRACT INFORMATION
================================

FROM CV - using matched_domain context:

1. EDUCATION:
   - Highest degree: [high_school|associate|bachelor|master|phd|bootcamp|none]
   - Field of study: (exact text from CV)
   - Is field relevant to job_domain? [yes|no|partial]

2. EXPERIENCE:
   For EACH job role listed in CV:
   - Job title: (exact text)
   - Duration: (exact dates or "X months/years" as written)
   - Domain: which candidate_domain does this role belong to?
   - Relevance to job_domain: [direct|partial|none]

   Calculate:
   - total_years: all roles combined (internships 0.3x, do not double-count overlaps)
   - relevant_years: only roles with relevance = direct or partial
     (partial roles count as 0.5x toward relevant_years)

   Show calculation explicitly.

3. SKILLS:
   List ONLY skills explicitly mentioned in CV:
   - Technical skills: [list each skill exactly as written]
   - Domain knowledge: [list each domain/industry exactly as written]

   DO NOT infer skills. If CV does not say "Python", do not list "Python".

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

   CRITICAL: DO NOT add skills that are not in the job description.
   DO NOT break compound skills into sub-skills.
   (e.g. "wet lab experience" stays as "wet lab experience")

NORMALIZATION (apply AFTER extraction, ONLY within matched domain):
- Synonyms: "Machine Learning" = "ML", "ReactJS" = "React", "Kubernetes" = "k8s"
- Related tech: "PostgreSQL" ~= "MySQL" (count as 0.5 match)
- Stack inference: "Django" implies "Python" (count as 0.3 match)
- DO NOT apply cross-domain normalization.
  (e.g. "data analysis" in bioinformatics context != "data analysis"
   in a nursing or finance context)

================================
STEP 4 - SKILLS MATCH (0-4 points)
================================

Count matches between candidate skills and REQUIRED job skills only.

Matching rules:
- Exact match -> 1.0
- Synonym match -> 1.0
- Related match (same domain, similar tool) -> 0.5
- Inferred match (stack/framework implies language) -> 0.3
- Same skill name but different domain context -> 0.0

Calculate:
  total_matches = sum of all match weights
  coverage = total_matches / count(required_skills)

Scoring thresholds depend on domain_match and role_type alignment:

  If domain_match = "exact" AND role_type = ALIGNED (standard threshold):
    - coverage < 0.30 -> 0
    - coverage >= 0.30 and < 0.50 -> 2
    - coverage >= 0.50 and < 0.80 -> 3
    - coverage >= 0.80 -> 4

  If domain_match = "related" OR role_type = ADJACENT (strict threshold):
    - coverage < 0.40 -> 0
    - coverage >= 0.40 and < 0.60 -> 2
    - coverage >= 0.60 and < 0.85 -> 3
    - coverage >= 0.85 -> 4

  If role_type = DIVERGENT (very strict threshold):
    - coverage < 0.50 -> 0
    - coverage >= 0.50 and < 0.70 -> 2
    - coverage >= 0.70 and < 0.90 -> 3
    - coverage >= 0.90 -> 4

SENIOR ROLE CONSTRAINT:
- If coverage < 0.30 AND job is senior+ -> cap skills score at 1

================================
STEP 5 - EDUCATION SCORING (0-3 points)
================================

Education hierarchy (strict order):
High School < Associate < Bachelor < Master < PhD

FIELD CHECK (apply first):
- If job requires a specific field AND candidate's field is unrelated:
  -> education_field_match = "no"
  -> Cap education score at 1 regardless of degree level
  -> If degree level is also below required -> score = 0

- If candidate has a degree in a RELATED field
  (e.g. bioinformatics for a data science role, or computer science for
   a software engineering role):
  -> education_field_match = "partial"
  -> Apply normal degree level scoring but do not award the +0.5 preferred bonus

Rules:
- candidate education level < required -> score = 0
- candidate education == required AND field = yes -> score = 2
- candidate education == required AND field = partial -> score = 1.5
- candidate education == required AND field = no -> score = 1
- candidate education > required AND field = yes -> score = 2.5
- candidate education > required AND field = partial -> score = 2
- candidate education > required AND field = no -> score = 1
- candidate meets desirable education AND field = yes -> add +0.5 (max 3)

================================
STEP 6 - SENIORITY & EXPERIENCE (0-3 points)
================================

Use relevant_years from Step 3, NOT total_years.

Scoring:
- relevant_years < 50% of required -> 0
- relevant_years >= 50% and < required -> 1
- relevant_years ~= required (+-20%) -> 2
- relevant_years > required -> 3

SENIOR ROLE CONSTRAINTS (seniority: senior/staff/principal/lead/head):
- If relevant_years < 3 -> ABORT, final score = 0, stop here
- If relevant_years < required -> cap experience score at 1

MANAGER ROLE CONSTRAINTS (if "manager" in job title):
- If CV shows no management experience in the relevant domain -> cap at 1
- If CV shows management but < 2 years -> cap experience score at 2

================================
STEP 7 - FINAL SCORE (0-10)
================================

Base score = education + seniority + skills

Apply caps in this strict order (each cap can only reduce, never increase):

1. Domain mismatch cap:
   - domain_mismatch = true -> score = 0

2. Domain relation cap:
   - domain_match = "related" -> score = min(score, 6)

3. Role type cap:
   - role_type_alignment = ADJACENT -> score = min(score, 7)
   - role_type_alignment = DIVERGENT -> score = min(score, 5)

4. Education hard caps:
   - education score = 0 -> score = min(score, 2)
   - education_field_match = "no" -> score = min(score, 3)

5. Senior experience cap:
   - seniority is senior+ AND relevant_years < required -> score = min(score, 2)

Skills matching alone cannot override any of the above caps.

RE-EVALUATE YOUR FULL ASSESSMENT ONE MORE TIME before outputting.
Checklist:
- Did I identify ALL candidate domains, not just the most recent one?
- Did the correct domain match the job?
- Did I use relevant_years and not total_years?
- Are all caps correctly applied in order?
- Would a human recruiter shortlist this candidate? If no, score must be <= 3.

================================
STEP 8 - OUTPUT FORMAT
================================

Return ONLY valid JSON. No preamble, no explanation outside the JSON block.
No markdown fences. No backticks. Raw JSON only.

{{
  "score": 0,
  "title": "",
  "breakdown": {{
    "education": 0,
    "seniority": 0,
    "skills": 0
  }},
  "reasoning": "Explanation covering: matched domain, domain_match type, role_type alignment, education field relevance, relevant vs total years, skills coverage, and every cap applied with reason",
  "extracted": {{
    "candidate_domains": [],
    "matched_domain": "",
    "domain_match": "",
    "domain_mismatch": false,
    "job_domain": "",
    "job_role_type": "",
    "candidate_role_type": "",
    "role_type_alignment": "",
    "candidate_education": "",
    "candidate_education_field": "",
    "education_field_match": "",
    "candidate_total_years": 0,
    "candidate_relevant_years": 0,
    "job_required_education": "",
    "job_required_field": "",
    "job_min_years": 0,
    "job_seniority": "",
    "skills_coverage": 0,
    "skills_matched": []
  }}
}}

================================
IMPORTANT RULES
================================

- Steps 0 and 1 are non-negotiable. Domain mismatch = score 0, full stop.
- Always follow steps in order. Never skip extraction.
- Multi-domain candidates: check ALL domains, not just the most recent one.
- Use relevant_years not total_years for experience scoring.
- Never apply normalization across domain boundaries.
- Prefer under-scoring over over-scoring.
- Output MUST be raw valid JSON only. No markdown, no backticks, no extra text.

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

    return prompt