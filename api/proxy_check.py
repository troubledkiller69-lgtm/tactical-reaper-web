import asyncio
import aiohttp
import time
import re
from curl_cffi import requests as curl_requests

class AsyncProxyChecker:
    def __init__(self, proxies, timeout=10, concurrency=500):
        self.proxies = proxies
        self.timeout = timeout
        self.concurrency = concurrency
        self.results = []
        self.test_url = "http://httpbin.org/get"
        
    def get_scamalytics_score(self, ip):
        try:
            url = f"https://scamalytics.com/ip/{ip}"
            # Use curl_cffi to bypass Cloudflare
            resp = curl_requests.get(url, impersonate="chrome120", timeout=10)
            if resp.status_code == 200:
                # Look for "Fraud Score: <num>"
                match = re.search(r'Fraud Score: (\d+)', resp.text)
                if match:
                    return int(match.group(1))
        except: pass
        return "N/A"

    async def check_proxy(self, session, proxy_str):
        if "://" in proxy_str:
            proxy_url = proxy_str
        else:
            proxy_url = f"http://{proxy_str}"

        start_time = time.time()
        try:
            async with session.get(self.test_url, proxy=proxy_url, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    latency = int((time.time() - start_time) * 1000)
                    
                    origin = data.get('origin', '')
                    headers = data.get('headers', {})
                    
                    anonymity = "Elite"
                    if proxy_url.split("//")[1].split(":")[0] in origin:
                        if 'X-Forwarded-For' in headers or 'Via' in headers:
                            anonymity = "Transparent"
                        else:
                            anonymity = "Anonymous"
                    
                    # Geolocation check
                    country, region, city, ip = "N/A", "N/A", "N/A", None
                    try:
                        async with session.get("http://ip-api.com/json/", proxy=proxy_url, timeout=5) as geo_res:
                            if geo_res.status == 200:
                                geo_data = await geo_res.json()
                                country = geo_data.get('country', 'N/A')
                                region = geo_data.get('regionName', 'N/A')
                                city = geo_data.get('city', 'N/A')
                                ip = geo_data.get('query')
                    except: pass

                    # Scamalytics Fraud Score
                    fraud_score = "N/A"
                    if ip:
                        fraud_score = await asyncio.to_thread(self.get_scamalytics_score, ip)

                    return {
                        "proxy": proxy_str,
                        "status": "Live",
                        "latency": latency,
                        "anonymity": anonymity,
                        "protocol": proxy_url.split("://")[0],
                        "country": country,
                        "region": region,
                        "city": city,
                        "fraud_score": fraud_score
                    }
        except: pass
        
        return {
            "proxy": proxy_str,
            "status": "Dead",
            "latency": -1,
            "anonymity": "N/A",
            "protocol": "N/A",
            "country": "N/A",
            "region": "N/A",
            "city": "N/A",
            "fraud_score": "N/A"
        }

    async def run(self):
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_proxy(session, p) for p in self.proxies]
            self.results = await asyncio.gather(*tasks)
        return self.results

if __name__ == "__main__":
    proxies = ["1.1.1.1:80", "8.8.8.8:8080"]
    checker = AsyncProxyChecker(proxies)
    results = asyncio.run(checker.run())
    print(results)
