import asyncio
import aiohttp
from duckduckgo_search import DDGS
import re
import csv
import logging
import pandas as pd
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def fetch_html(session, url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception:
        pass
    return None

import urllib.parse

async def spider_bank(session, institution_name, sem):
    """Searches for the bank and spiders its homepage for DXO links."""
    async with sem:
        logger.info(f"Spidering: {institution_name}")
        try:
            import asyncio
            await asyncio.sleep(1) # Soft delay
            query = urllib.parse.quote(institution_name + " credit card login")
            search_url = f"https://search.yahoo.com/search?p={query}"
            
            html = await fetch_html(session, search_url)
            if not html: return None
            
            soup = BeautifulSoup(html, 'html.parser')
            urls = []
            for a in soup.select('.compTitle h3 a'):
                href = a.get('href')
                if href and 'RU=' in href:
                    try:
                        actual_url = urllib.parse.unquote(href.split('RU=')[1].split('/RK=')[0])
                        if actual_url and 'yahoo.com' not in actual_url:
                            urls.append(actual_url)
                    except:
                        pass
                        
            for url in urls[:2]:
                site_html = await fetch_html(session, url)
                if not site_html: continue
                
                site_soup = BeautifulSoup(site_html, 'html.parser')
                for a in site_soup.find_all('a', href=True):
                    link = a['href']
                    if "dxonline-apps" in link and "req=" in link:
                        clean_url = link.split("&")[0]
                        return {"institution": institution_name, "url": clean_url}
        except Exception as e:
            logger.debug(f"Spider failed for {institution_name}: {e}")
        return None

async def run_dumper():
    logger.info("Starting DXO Deep Spider Engine...")
    
    # 1. Load BIN Data and Extract US Credit Unions with BINs
    logger.info("Loading bin_data.csv...")
    try:
        df = pd.read_csv("bin_data.csv", low_memory=False)
        cu_df = df[(df['isoCode2'] == 'US') & (df['Issuer'].str.contains('CREDIT UNION', na=False, case=False))]
        cu_bins = cu_df.groupby('Issuer')['BIN'].apply(lambda x: list(set(x.astype(str)))).to_dict()
        unique_cus = list(cu_bins.keys())
        logger.info(f"Found {len(unique_cus)} unique US Credit Unions.")
    except Exception as e:
        logger.error(f"Failed to load BIN data: {e}")
        return

    # For demonstration, limit to the first 50 to avoid massive ratelimits
    targets = unique_cus
    logger.info(f"Spidering all {len(targets)} targets...")

    new_portals = []
    
    # 2. Spider
    sem = asyncio.Semaphore(2) # Limit to 2 concurrent requests
    async with aiohttp.ClientSession() as session:
        tasks = [spider_bank(session, cu, sem) for cu in targets]
        results = await asyncio.gather(*tasks)
        
        for r in results:
            if r is not None:
                r['bins'] = cu_bins.get(r['institution'], [])
                new_portals.append(r)

    logger.info(f"Deep Spider complete. Found {len(new_portals)} NEW DXO portals.")

    # 3. Output
    if new_portals:
        with open("new_dxo_links.md", "w", encoding="utf-8") as f:
            f.write("# TACTICAL REAPER | NEW DXONLINE DISCOVERIES\n\n")
            f.write(f"**New Portals Found:** {len(new_portals)}\n\n")
            f.write("| Institution | Portal URL | Attached BINs |\n")
            f.write("|-------------|------------|---------------|\n")
            for p in new_portals:
                bins_str = ", ".join(p['bins'])
                f.write(f"| {p['institution']} | `{p['url']}` | {bins_str} |\n")
        
        # Also dump JS object format for easy pasting into index.html
        with open("new_dxo_js_objects.txt", "w", encoding="utf-8") as f:
            for p in new_portals:
                infra = "s1" if "-s1-" in p['url'] else "s2"
                req_match = re.search(r"req=([^&]+)", p['url'])
                req_val = req_match.group(1) if req_match else "UNKNOWN"
                bins_formatted = "[" + ", ".join([f"'{b}'" for b in p['bins']]) + "]"
                name_safe = p['institution'].replace("'", "\\'")
                f.write(f"{{ n: '{name_safe}', u: '{infra}', r: '{req_val}', b: {bins_formatted} }},\n")
                
        logger.info("Results saved to new_dxo_links.md and new_dxo_js_objects.txt")
    else:
        logger.info("No new portals found in this batch.")

if __name__ == "__main__":
    asyncio.run(run_dumper())
