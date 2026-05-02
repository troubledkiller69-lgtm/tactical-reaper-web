import asyncio
import aiohttp
from ddgs import DDGS
import re
import csv
import logging
import pandas as pd
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def fetch_html(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception:
        pass
    return None

async def spider_bank(session, institution_name):
    """Searches for the bank and spiders its homepage for DXO links."""
    logger.info(f"Spidering: {institution_name}")
    ddgs = DDGS()
    try:
        # Step 1: Find the official website
        results = ddgs.text(institution_name + " credit card login", max_results=3)
        for r in results:
            url = r.get("href")
            if not url: continue
            
            # Step 2: Fetch HTML and look for DXO links
            html = await fetch_html(session, url)
            if not html: continue
            
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                link = a['href']
                if "dxonline-apps" in link and "req=" in link:
                    clean_url = link.split("&")[0]
                    return {"institution": institution_name, "url": clean_url}
    except Exception as e:
        logger.debug(f"Spider failed for {institution_name}: {e}")
    return None

async def run_dumper():
    logger.info("Starting DXO Deep Spider Engine...")
    
    # 1. Load BIN Data and Extract US Credit Unions
    logger.info("Loading bin_data.csv...")
    try:
        df = pd.read_csv("bin_data.csv", low_memory=False)
        cu_df = df[(df['isoCode2'] == 'US') & (df['Issuer'].str.contains('CREDIT UNION', na=False, case=False))]
        unique_cus = cu_df['Issuer'].unique().tolist()
        logger.info(f"Found {len(unique_cus)} unique US Credit Unions.")
    except Exception as e:
        logger.error(f"Failed to load BIN data: {e}")
        return

    # For demonstration, limit to the first 50 to avoid massive ratelimits
    targets = unique_cus[:50]
    logger.info(f"Spidering first {len(targets)} targets...")

    new_portals = []
    
    # 2. Spider
    async with aiohttp.ClientSession() as session:
        tasks = [spider_bank(session, cu) for cu in targets]
        results = await asyncio.gather(*tasks)
        new_portals = [r for r in results if r is not None]

    logger.info(f"Deep Spider complete. Found {len(new_portals)} NEW DXO portals.")

    # 3. Output
    if new_portals:
        with open("new_dxo_links.md", "w", encoding="utf-8") as f:
            f.write("# TACTICAL REAPER | NEW DXONLINE DISCOVERIES\n\n")
            f.write(f"**New Portals Found:** {len(new_portals)}\n\n")
            f.write("| Institution | Portal URL |\n")
            f.write("|-------------|------------|\n")
            for p in new_portals:
                f.write(f"| {p['institution']} | `{p['url']}` |\n")
        logger.info("Results saved to new_dxo_links.md")
    else:
        logger.info("No new portals found in this batch.")

if __name__ == "__main__":
    asyncio.run(run_dumper())
