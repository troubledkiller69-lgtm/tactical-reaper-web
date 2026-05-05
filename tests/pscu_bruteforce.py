import requests, bs4, concurrent.futures

def check_server(i):
    url = f"https://dxonline-apps-s{i}-cloud.pscu.com/Consumer/Home/Index"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if r.status_code == 200:
            soup = bs4.BeautifulSoup(r.text, 'html.parser')
            title = soup.title.string if soup.title else 'No Title'
            return (i, True, title.strip(), len(r.text))
        return (i, False, f"HTTP {r.status_code}", 0)
    except Exception as e:
        return (i, False, str(e), 0)

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(check_server, range(1, 30)))

for res in sorted(results):
    if res[1]:
        print(f"s{res[0]} -> ALIVE | Title: '{res[2]}' | Size: {res[3]} bytes")
