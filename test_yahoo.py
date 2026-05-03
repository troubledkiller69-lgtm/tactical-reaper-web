import urllib.parse, requests, bs4
queries = [
    '"dxonline-apps"',
    '"dxonline-apps-s1-cloud.pscu.com"',
    '"dxonline-apps-s2-cloud.pscu.com"',
    'site:pscu.com',
    'inurl:dxonline-apps'
]
for query in queries:
    q = urllib.parse.quote(query)
    html = requests.get(f'https://search.yahoo.com/search?p={q}', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}).text
    soup = bs4.BeautifulSoup(html, 'html.parser')
    urls = []
    for a in soup.select('.compTitle h3 a'):
        href = a.get('href')
        if href and 'RU=' in href:
            try:
                actual_url = urllib.parse.unquote(href.split('RU=')[1].split('/RK=')[0])
                urls.append(actual_url)
            except:
                pass
    print(f"Query: {query}")
    print(f"Found: {len(urls)} urls")
    for u in urls[:5]:
        print("  ", u)
    print()
