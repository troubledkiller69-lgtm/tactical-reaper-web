import aiohttp
import asyncio
import logging
import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DXIdentifier:
    """
    High-Accuracy Identification for DXOnline (PSCU) platforms.
    Now with real-time link validation.
    """
    def __init__(self):
        self.api_url = "https://bin-ip-checker.p.rapidapi.com/"
        self.api_key = os.environ.get("RAPIDAPI_KEY")
        self.api_host = os.environ.get("RAPIDAPI_HOST")
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
            "Content-Type": "application/json"
        }

    def _generate_portal_link(self, bank_name: str) -> str:
        """
        Generates a potential DXOnline portal link based on bank name.
        """
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', bank_name.lower().replace("credit union", "").replace("fcu", ""))
        # DX portals often use this pattern
        return f"https://www.dxonline.com/{clean_name}/"

    async def _validate_link(self, url: str) -> bool:
        """
        Checks if the generated link is actually live.
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.head(url, allow_redirects=True) as response:
                    # PSCU portals usually return 200 or 302 to a login page
                    return response.status < 400
        except Exception:
            return False

    async def scan_bin(self, bin_number: str) -> Dict[str, Any]:
        """
        Surgically scans a BIN for DXOnline compatibility.
        """
        bin_number = bin_number.strip()[:6]
        if not bin_number.isdigit():
            return {"status": "error", "message": "Invalid BIN format."}

        if not self.api_key:
            return {"status": "error", "message": "RapidAPI Key not found in .env"}

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                params = {"bin": bin_number}
                async with session.get(self.api_url, params=params) as response:
                    if response.status != 200:
                        return {"status": "error", "message": f"API error {response.status}"}
                    
                    data = await response.json()
                    bin_data = data.get("BIN", {})
                    bank_info = bin_data.get("issuer", {})
                    bank_name = bank_info.get("name", "Unknown")
                    
                    if bank_name == "Unknown":
                        bank_name = data.get("bank", {}).get("name", "Unknown")

                    is_credit_union = "credit union" in bank_name.lower() or "fcu" in bank_name.lower()
                    is_us = bin_data.get("country", {}).get("alpha2") == "US"
                    
                    if not (is_credit_union and is_us):
                        return {
                            "status": "incompatible",
                            "bank": bank_name,
                            "reason": "Not a US Credit Union (DX Target Profile)"
                        }

                    portal_link = self._generate_portal_link(bank_name)
                    is_valid = await self._validate_link(portal_link)

                    return {
                        "status": "verified" if is_valid else "potential",
                        "bank": bank_name,
                        "scheme": bin_data.get("scheme", "Unknown").upper(),
                        "type": bin_data.get("type", "Unknown").capitalize(),
                        "level": bin_data.get("level", "Unknown"),
                        "country": bin_data.get("country", {}).get("name", "Unknown"),
                        "portal": portal_link if is_valid else "N/A (Link Invalid)",
                        "signature": "dxonline.pscu.com [LIVE_CHECKED]" if is_valid else "dxonline.pscu.com [OFFLINE/PRIVATE]",
                        "message": f"✅ Verified DX Partner: {bank_name}" if is_valid else f"⚠️ Potential DX Partner (Portal Link unreachable): {bank_name}"
                    }

        except Exception as e:
            logger.error("DX Precision Scan failed: %s", e)
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    async def test():
        scanner = DXIdentifier()
        res = await scanner.scan_bin("448590")
        print(res)
    
    asyncio.run(test())
