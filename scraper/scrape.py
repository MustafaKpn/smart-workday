"""
Scraper for Workday-based career sites
"""
#app/scraper/scrape.py
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
import json
import time
from app.config import engine
from app.storage.db import raw_jobs
from sqlalchemy import insert
from urllib.parse import urljoin
import xxhash


class WorkdayScraper:
    """Scraper for Workday-based career sites"""
    
    def __init__(self, location: str = None, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.location = location

    async def scrape(self, url: str) -> List[Dict]:
        """Scrape jobs from a Workday career site"""
        print(f"[*] Scraping: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            detail_page = await context.new_page()

            jobs_dict = {"jobs": []}
            
            try:
                await page.goto(url, timeout=self.timeout, wait_until="networkidle")
                await page.wait_for_selector('section[data-automation-id="jobResults"]', 
                                            timeout=self.timeout)
                
                await page.wait_for_selector("ol[role=list]", 
                                            timeout=self.timeout)
                
                if self.location:
                    await page.click("[data-automation-id='distanceLocation']")
                    await page.wait_for_selector("[data-automation-id='stickyContainerHolder']")

                    all_locations = page.locator("[data-automation-id='Locations-checkboxgroup']")
                    option = all_locations.locator(f':text-matches("{self.location}", "i")').first

                    # Check if this option exists
                    if await option.count() > 0:
                        checkbox = option.locator("input[type=checkbox]")

                        # If the checkbox exists, check it; else, click the option
                        if await checkbox.count() > 0:
                            await checkbox.check()
                        else:
                            await option.click()
                    else:
                        print(f"[-] Location '{self.location}' not found, skipping filter.")
                        return []

                    await page.click('[data-uxi-element-id="filterToolbar_viewAllJobsButton"]')
                    await page.wait_for_timeout(1000)


                buttons = page.locator("ol[role=list] button")
                
                buttons_count = await buttons.count()
                
                for i in range(buttons_count):
                    btn = buttons.nth(i)
                    await btn.click()
                    await page.wait_for_timeout(2000)

                    jobs = await self._extract_jobs(page, detail_page, url)
                    jobs_dict["jobs"].extend(jobs)
                        
                with open("./jobs.json", "w") as f:
                    json.dump(jobs_dict, f, indent=4)
                
                
                print(f"[+] Found {len(jobs_dict['jobs'])} jobs")
                return jobs_dict
            
            except Exception as e:
                print(f"[-] Error scraping {url}: {e}")
                return []
            
            finally:
                await browser.close()


    async def _extract_jobs(self, page, detail_page, base_url: str) -> List[Dict]:
        """Extract job data from Workday page"""
        jobs = []

        job_elements = await page.query_selector_all(
            'section[data-automation-id="jobResults"] ul[role="list"] > li'
        )
        
        for element in job_elements:
            try:
                title_elem = await element.query_selector('a[data-automation-id="jobTitle"]')
                title = await title_elem.inner_text() if title_elem else "Unknown"
                
                url = await title_elem.get_attribute("href") if title_elem else ""
                if url.startswith('/'):
                    url = urljoin(page.url or "", url)
                
                location_elem = await element.query_selector('div[data-automation-id="locations"] >> dd')
                location = await location_elem.inner_text() if location_elem else ""
                
                date_elem = await element.query_selector('[data-automation-id="postedOn"] >> dd')
                posted = await date_elem.inner_text() if date_elem else ""

                subtitle_elem = await element.query_selector('[data-automation-id="subtitle"]')
                subtitle = await subtitle_elem.inner_text() if subtitle_elem else "Unknown"

                id = xxhash.xxh64(subtitle).intdigest() & 0x7FFFFFFFFFFFFFFF

                stmt = insert(raw_jobs).values(id=id,
                                               title=title.strip(),
                                               source=self._extract_company_name(base_url),
                                               url=url,
                                               location=location.strip(),
                                               description=await self.fetch_description(detail_page, url))
                
                with engine.connect() as conn:
                    conn.execute(stmt)
                    conn.commit()
                jobs.append({
                    "title": title.strip(),
                    "url": url,
                    "company": self._extract_company_name(base_url),
                    "location": location.strip(),
                    "posted_date": posted.strip(),
                    "description": await self.fetch_description(detail_page, url)
                })

                # print(jobs)
                
            except Exception as e:
                print(f"[-] Error extracting job: {e}")
                continue
        
        return jobs
    
    async def fetch_description(self, page, url: str) -> str:
        try:
            await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            desc_elem = page.locator('[data-automation-id="jobPostingDescription"]')

            paragraphs = desc_elem.locator("p")
            texts = []
            for i in range(await paragraphs.count()):
                des_text = (await paragraphs.nth(i).inner_text()).strip()
                if des_text:
                    texts.append(des_text)
                    
            # Join paragraphs with double newline (or single if you prefer)
            return " ".join(texts)

        except Exception as e:
            return f"[Error fetching description] {str(e)}"


    @staticmethod
    def _extract_company_name(url: str) -> str:
        """Extract company name from Workday URL"""
        parts = url.split(".")
        if len(parts) > 0:
            return parts[0].split("//")[-1].capitalize()
        return "Unknown"


scraper = WorkdayScraper("Cambridge")
# jobs = asyncio.run(scraper.scrape("https://sanger.wd103.myworkdayjobs.com/en-GB/WellcomeSangerInstitute"))
jobs = asyncio.run(scraper.scrape("https://illumina.wd1.myworkdayjobs.com/en-US/illumina-careers?redirect=/en-US/illumina-careers/userHome"))



