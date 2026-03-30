from app.config import engine
from app.storage.db import raw_jobs, parsed_jobs
from app.parser.llm_parser import GroqMatcher
from app.utils.logger import setup_logging
from app.storage.JobRepository import JobRepository

# from app.filter.criteria import passes_criteria
# from app.notifier.telegram import send_job
from app.scraper.scrape import WorkdayScraper
from sqlalchemy import update
from dotenv import load_dotenv
import asyncio
import os
import logging


setup_logging()

logger = logging.getLogger(__name__)


load_dotenv("app/.env")
api_key = os.getenv("GROQ_API_KEY")

matcher = GroqMatcher(
    api_key=api_key,
    cv_path="./app/CV_SE.pdf"
)

# jobs = asyncio.run(scraper.scrape("https://sanger.wd103.myworkdayjobs.com/en-GB/WellcomeSangerInstitute"))
# jobs = asyncio.run(scraper.scrape("https://illumina.wd1.myworkdayjobs.com/en-US/illumina-careers?redirect=/en-US/illumina-careers/userHome"))


async def process_jobs():
    scraper = WorkdayScraper("Cambridge")
    await scraper.scrape("https://sanger.wd103.myworkdayjobs.com/en-GB/WellcomeSangerInstitute")

    # Step 1: claim jobs atomically
    with engine.begin() as conn:
        jobs = JobRepository.claim_jobs(conn)

    if not jobs:
        print("[*] No jobs to process")
        return

    print(f"[*] Processing {len(jobs)} jobs")

    for job in jobs:
        try:
            print("Before LLM processing: {}".format(job))
            # Step 2: run LLM
            parsed = await matcher.process_job(job)

            # Step 3: store results
            with engine.begin() as conn:
                conn.execute(parsed_jobs.insert().values(
                    raw_job_id=job["id"],
                    reasoning=parsed["reasoning"],
                    score=parsed["score"],
                ))

                # Step 4: mark done
                conn.execute(
                    update(raw_jobs)
                    .where(raw_jobs.c.id == job["id"])
                    .values(status="done")
                )

            # # Step 5: notify
            # if passes_criteria(parsed):
            #     send_job(parsed)

        except Exception as e:
            print(f"[ERROR] Job {job['id']}: {e}")

            # Step 6: mark failed
            with engine.begin() as conn:
                conn.execute(
                    update(raw_jobs)
                    .where(raw_jobs.c.id == job["id"])
                    .values(status="failed")
                )


async def test():
    from app.storage.JobRepository import JobRepository

    repo = JobRepository(engine)
    jobs = await WorkdayScraper('Cambridge').scrape("https://sanger.wd103.myworkdayjobs.com/en-GB/WellcomeSangerInstitute")
    repo.bulk_insert(jobs)
    job1 = repo.claim_jobs(engine)[0]

    processed = await matcher.process_job(job1)
    print(processed)

    repo.mark_completed(processed.get('id'), processed.get('score'), processed.get('reasoning'))
    
    return

async def main():
    await test()
    # await process_jobs()

if __name__ == "__main__":
    asyncio.run(main())
