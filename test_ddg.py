import urllib.parse, requests, bs4
query = urllib.parse.quote('1199 SEIU FEDERAL CREDIT UNION credit card login')
html = requests.get(f'https://html.duckduckgo.com/html/?q={query}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}).text
print("DuckDuckGo" in html)
if "result__url" in html:
    print("Found results")
else:
    print("No results found in HTML")
