"""
Scraper for Workday-based career sites
"""

import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
import json
import time

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
                if url and not url.startswith("http"):
                    from urllib.parse import urljoin
                    url = urljoin(base_url, url)
                
                location_elem = await element.query_selector('div[data-automation-id="locations"] >> dd')
                location = await location_elem.inner_text() if location_elem else ""
                
                date_elem = await element.query_selector('[data-automation-id="postedOn"] >> dd')
                posted = await date_elem.inner_text() if date_elem else ""
                print("{}".format(title.strip()))
                
                jobs.append({
                    "title": title.strip(),
                    "url": url,
                    "company": self._extract_company_name(base_url),
                    "location": location.strip(),
                    "posted_date": posted.strip(),
                    "description": await self.fetch_description(detail_page, url)
                })
                
            except Exception as e:
                print(f"[-] Error extracting job: {e}")
                continue
        
        return jobs
    
    async def fetch_description(self, page, url: str) -> str:
        try:
            await page.goto(url, timeout=self.timeout)
            desc_elem = page.locator('[data-automation-id="jobPostingDescription"]')
            if await desc_elem.count() > 0:
                return (await desc_elem.inner_text()).strip()
            return await page.inner_text("body")
        except Exception:
            return ""


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



