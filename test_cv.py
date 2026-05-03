import urllib.parse, requests, bs4
query = urllib.parse.quote('site:fiserv.com "CardValet"')
html = requests.get(f'https://search.yahoo.com/search?p={query}', headers={'User-Agent': 'Mozilla/5.0'}).text
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
for u in urls:
    print(u)
