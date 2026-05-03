import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Remove Conversion Rate block
conversion_rate_regex = re.compile(r'<div class="card" style="text-align: center;">\s*<div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">CONVERSION RATE</div>.*?</div>', re.DOTALL)
html = re.sub(conversion_rate_regex, '', html, count=1)

# Modify Total Revenue to 0 and remove the growth sub-text
revenue_regex = re.compile(r'<div class="card" style="text-align: center;">\s*<div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">TOTAL REVENUE</div>.*?</div>', re.DOTALL)
new_revenue_block = '''<div class="card" style="text-align: center;">
                        <div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">TOTAL REVENUE</div>
                        <div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">$0</div>
                        <div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">Real-time earnings</div>
                    </div>'''
html = re.sub(revenue_regex, new_revenue_block, html, count=1)

# Add IDs to Total Users and Active Sessions for JS targeting
html = html.replace('<div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">14,291</div>', '<div id="stat-users" style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">...</div>')
html = html.replace('<div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">843</div>', '<div id="stat-sessions" style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">...</div>')
html = html.replace('<div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">+12% vs last week</div>', '<div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">Active Keys</div>')
html = html.replace('<div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">+5% vs last week</div>', '<div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">Active Keys</div>')


# Inject the JS function
fetch_script = '''
        async function fetchDashboardStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                if(response.ok) {
                    document.getElementById('stat-users').innerText = data.active_keys;
                    document.getElementById('stat-sessions').innerText = data.active_keys;
                } else {
                    document.getElementById('stat-users').innerText = 'ERR';
                    document.getElementById('stat-sessions').innerText = 'ERR';
                }
            } catch (e) {
                document.getElementById('stat-users').innerText = '0';
                document.getElementById('stat-sessions').innerText = '0';
            }
        }
        
        // Call it immediately if we are on the dashboard
        document.addEventListener("DOMContentLoaded", () => {
            fetchDashboardStats();
        });
'''
# inject before closing </script> or just before </body>
html = html.replace('</body>', fetch_script + '\n</body>')

# Make sure switchTab also calls it
html = html.replace("document.getElementById(`tab-${tabId}`).classList.add('active');", "document.getElementById(`tab-${tabId}`).classList.add('active');\n            if(tabId === 'dashboard') fetchDashboardStats();")


with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
