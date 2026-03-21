from playwright.async_api import async_playwright



async def fetch_description(url: str) -> str:

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=3000, wait_until="networkidle")
            desc_elem = page.locator('[data-automation-id="jobPostingDescription"]')

            paragraphs = desc_elem.locator("p")
            texts = []
            for i in range(await paragraphs.count()):
                des_text = (await paragraphs.nth(i).inner_text()).strip()
                if des_text:
                    texts.append(des_text)
                    
            return " ".join(texts)

        except Exception as e:
            return f"[Error fetching description] {str(e)}"
    

