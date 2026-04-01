from pathlib import Path

from app.config import engine
from app.parser.llm_parser import GroqMatcher
from app.utils.logger import setup_logging
from app.storage.JobRepository import JobRepository
from app.telegram.telegramnotifier import TelegramNotifier
from app.utils.telegrammsg import build_telegram_message
from app.utils.config_loader import load_active_targets
from app.scraper.scrape import WorkdayScraper
from dotenv import load_dotenv
import asyncio
import os
import logging
import subprocess

subprocess.run(["python3", "-m", "app.storage.db"])
setup_logging()

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent.parent / ".env")
api_key = os.getenv("GROQ_API_KEY")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")


matcher = GroqMatcher(
    api_key=api_key,
    cv_path="./CV.pdf"
)


async def process_jobs():
    notifier = TelegramNotifier(token=bot_token, chat_id=chat_id)
    targets = load_active_targets(Path(__file__).parent.parent / "targets.toml")
    repo = JobRepository(engine)

    for target in targets:
        try:
            scraper = WorkdayScraper(target.location_filter)
            jobs = await scraper.scrape(target.url)
            repo.bulk_insert(jobs)
            logger.info(f"Scraped {len(jobs)} jobs from {target.name}")
            jobs_to_process = repo.claim_jobs()
            logger.info(f"Processing {len(jobs_to_process)} jobs")

            if not jobs_to_process:
                logger.warning("No jobs to process")
                return
            
            for job in jobs_to_process:
                try:
                    # Step 1: run LLM
                    parsed = await matcher.process_job(job)
                    logger.info(f"Processed job {job['id']} with score {parsed.get('score')}")

                    # Step 2: save results
                    repo.mark_completed(parsed.get('id'), parsed.get('score'), parsed.get('reasoning'))

                    # Step 3: if meets criteria, send Telegram message
                    if float(parsed.get("score", 0)) >= 2:
                        job_info = repo.get_job_by_id(job['id'])
                        logger.info(f"Job {job['id']} passed criteria with score {parsed.get('score')}")
                        message = build_telegram_message(job_info, parsed)
                        notifier.send_markdown(message)


                except Exception as e:
                    logger.error(f"Error processing job {job['id']}: {e}")

                    # mark failed
                    repo.mark_failed(job['id'])

        except Exception as e:
            logger.error(f"Scrape failed for {target.name}: {e}")


async def main():
    await process_jobs()

if __name__ == "__main__":
    asyncio.run(main())
