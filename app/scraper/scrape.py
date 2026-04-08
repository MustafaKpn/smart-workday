"""
Scraper for Workday-based career sites
"""
#app/scraper/scrape.py
from typing import List, Dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import xxhash
import logging

logger = logging.getLogger(__name__)
logger.info("app/scrape/scrape.py")

class WorkdayScraper:
    """Scraper for Workday-based career sites"""
    
    def __init__(self, location: str = None, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.location = location

    async def scrape(self, url: str) -> List[Dict]:
        """Scrape jobs from a Workday career site"""
        logger.info(f"Scraping: {url}")
        
        all_jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=self.timeout, wait_until="networkidle")
                await page.wait_for_selector('section[data-automation-id="jobResults"]', 
                                            timeout=self.timeout)
                
                await page.wait_for_selector("ol[role=list]", 
                                            timeout=self.timeout)
                
                if self.location:
                    try:
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
                            logger.warning(f"Location '{self.location}' not found, skipping filter.")
                            return []

                        await page.click('[data-uxi-element-id="filterToolbar_viewAllJobsButton"]')
                        await page.wait_for_timeout(1000)
                    except:
                        pass


                buttons = page.locator("ol[role=list] button")
                
                buttons_count = await buttons.count()
                
                for i in range(buttons_count):
                    btn = buttons.nth(i)
                    await btn.click()
                    await page.wait_for_timeout(2000)

                    all_jobs.extend(await self._extract_jobs(page, url))
                
                return all_jobs
            
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                return []
            
            finally:
                await browser.close()


    async def _extract_jobs(self, page, base_url: str):
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
                
                subtitle_elem = await element.query_selector('[data-automation-id="subtitle"]')
                subtitle = await subtitle_elem.inner_text() if subtitle_elem else "Unknown"

                id = xxhash.xxh64(subtitle).intdigest() & 0x7FFFFFFFFFFFFFFF

                jobs.append({
                    'id': id,
                    'title': title.strip(),
                    'company': self._extract_company_name(base_url),
                    'url': url,
                    'location': location.strip()
                })

                logger.info(f"Scraped job with id: {id}")
                

            except Exception as e:
                logger.error(f"Error extracting job: {e}")
                continue
        
        return jobs

    @staticmethod
    def _extract_company_name(url: str) -> str:
        """Extract company name from Workday URL"""
        parts = url.split(".")
        if len(parts) > 0:
            return parts[0].split("//")[-1].capitalize()
        return "Unknown"

