import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Navigation
html = html.replace("<a onclick=\"switchTab('logs')\" id=\"nav-logs\">LOGS</a>", "<a onclick=\"switchTab('tools')\" id=\"nav-tools\">TOOLS</a>")

# 2. Rename existing tab-dashboard to tab-tools
html = html.replace('<div id="tab-dashboard" class="tab-content active">', '<div id="tab-tools" class="tab-content">')

# 3. Create the new dashboard tab
new_dashboard = '''
        <div id="tab-dashboard" class="tab-content active">
            <div style="margin-top:2rem;">
                <h2 style="font-weight:900; letter-spacing:4px; margin-bottom:1.5rem;">OPERATIONAL OVERVIEW</h2>
                
                <!-- KPI Tier -->
                <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-bottom: 2rem;">
                    <div class="card" style="text-align: center;">
                        <div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">TOTAL USERS</div>
                        <div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">14,291</div>
                        <div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">+12% vs last week</div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">ACTIVE SESSIONS</div>
                        <div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">843</div>
                        <div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">+5% vs last week</div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">CONVERSION RATE</div>
                        <div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">3.4%</div>
                        <div style="color: var(--error); font-size: 0.6rem; margin-top: 0.5rem;">-0.2% vs last week</div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <div style="color: #555; font-size: 0.7rem; letter-spacing: 2px;">TOTAL REVENUE</div>
                        <div style="font-size: 2rem; color: #fff; margin-top: 0.5rem;">$128,450</div>
                        <div style="color: var(--success); font-size: 0.6rem; margin-top: 0.5rem;">+18% vs last week</div>
                    </div>
                </div>

                <!-- Visual Data Tier -->
                <div class="grid" style="grid-template-columns: 2fr 1fr; margin-bottom: 2rem;">
                    <div class="card">
                        <h3 style="margin-bottom: 1rem;">WEBSITE PERFORMANCE (TRAFFIC)</h3>
                        <div style="display: flex; align-items: flex-end; height: 150px; gap: 4px; padding-top: 20px; border-bottom: 1px solid #333;">
                            <div style="flex: 1; background: #222; height: 30%; transition: 0.3s;"></div>
                            <div style="flex: 1; background: #222; height: 50%;"></div>
                            <div style="flex: 1; background: #222; height: 40%;"></div>
                            <div style="flex: 1; background: #333; height: 70%;"></div>
                            <div style="flex: 1; background: #333; height: 60%;"></div>
                            <div style="flex: 1; background: var(--success); height: 90%; opacity: 0.8;"></div>
                            <div style="flex: 1; background: var(--success); height: 85%; opacity: 0.9;"></div>
                            <div style="flex: 1; background: #fff; height: 100%; box-shadow: 0 0 10px rgba(255,255,255,0.2);"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; color: #666; font-size: 0.55rem;">
                            <span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span><span>TODAY</span>
                        </div>
                    </div>
                    <div class="card">
                        <h3 style="margin-bottom: 1rem;">SYSTEM LOAD</h3>
                        <div style="position: relative; width: 120px; height: 120px; margin: 0 auto; border-radius: 50%; background: conic-gradient(var(--success) 78%, #222 0); display: flex; align-items: center; justify-content: center;">
                            <div style="width: 100px; height: 100px; background: #050505; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-direction: column;">
                                <span style="font-size: 1.5rem; color: #fff;">78%</span>
                                <span style="font-size: 0.5rem; color: #666;">CAPACITY</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Actionable Alerts Tier -->
                <div class="grid" style="grid-template-columns: 1fr 1fr;">
                    <div class="card">
                        <h3 style="margin-bottom: 1rem; color: var(--error);">ACTIONABLE ALERTS</h3>
                        <div style="border: 1px solid #333; padding: 0.8rem; margin-bottom: 0.5rem; background: #110000;">
                            <div style="color: var(--error); font-size: 0.7rem; font-weight: bold;">ANOMALY: LOW SALES CONVERSION</div>
                            <div style="color: #888; font-size: 0.6rem; margin-top: 0.3rem;">Checkout funnel drop-off increased by 14% in the last 2 hours.</div>
                            <a href="#" style="display: inline-block; margin-top: 0.5rem; font-size: 0.55rem; color: #fff; text-decoration: underline;">INVESTIGATE</a>
                        </div>
                        <div style="border: 1px solid #333; padding: 0.8rem; background: #111;">
                            <div style="color: #f39c12; font-size: 0.7rem; font-weight: bold;">TECHNICAL: API RATE LIMIT</div>
                            <div style="color: #888; font-size: 0.6rem; margin-top: 0.3rem;">Upstream provider (SMTP) approaching hourly threshold (92%).</div>
                            <a href="#" style="display: inline-block; margin-top: 0.5rem; font-size: 0.55rem; color: #fff; text-decoration: underline;">VIEW LOGS</a>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3 style="margin-bottom: 1rem;">USER ACTION ITEMS & PROJECTS</h3>
                        <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.65rem;">
                            <tr style="border-bottom: 1px solid #333; color: #666;">
                                <th style="padding: 0.5rem 0;">PROJECT</th>
                                <th style="padding: 0.5rem 0;">STATUS</th>
                                <th style="padding: 0.5rem 0; text-align: right;">ACTION</th>
                            </tr>
                            <tr style="border-bottom: 1px solid #222;">
                                <td style="padding: 0.5rem 0; color: #fff;">Reaper v7.2 Update</td>
                                <td style="padding: 0.5rem 0; color: #f39c12;">Pending QA</td>
                                <td style="padding: 0.5rem 0; text-align: right;"><a href="#" style="color: #888;">Review</a></td>
                            </tr>
                            <tr style="border-bottom: 1px solid #222;">
                                <td style="padding: 0.5rem 0; color: #fff;">Marketing Campaign</td>
                                <td style="padding: 0.5rem 0; color: var(--success);">Active</td>
                                <td style="padding: 0.5rem 0; text-align: right;"><a href="#" style="color: #888;">Edit</a></td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0; color: #fff;">Infrastructure Audit</td>
                                <td style="padding: 0.5rem 0; color: var(--error);">Overdue</td>
                                <td style="padding: 0.5rem 0; text-align: right;"><a href="#" style="color: #fff;">Start</a></td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
'''

html = html.replace('<div id="tab-tools" class="tab-content">', new_dashboard + '\n        <div id="tab-tools" class="tab-content">')

# 4. Remove Emojis
html = html.replace('<h3>💎 BIN INTEL</h3>', '<h3>BIN INTEL</h3>')
html = html.replace('<h3>📧 EMAIL FLOOD</h3>', '<h3>EMAIL FLOOD</h3>')
html = html.replace('<h3>📱 SMS BOMBER</h3>', '<h3>SMS BOMBER</h3>')
html = html.replace('<h3>🔍 CARRIER RECON</h3>', '<h3>CARRIER RECON</h3>')
html = html.replace('<h3>📥 BULK INPUT</h3>', '<h3>BULK INPUT</h3>')
html = html.replace('<h3>🛡️ STORM VAULT</h3>', '<h3>STORM VAULT</h3>')
html = html.replace('<h3>📍 GEO LOCATOR</h3>', '<h3>GEO LOCATOR</h3>')
html = html.replace('<h3>🔗 LINK TRACER</h3>', '<h3>LINK TRACER</h3>')

# 5. Remove Logs Tab div
logs_tab_regex = re.compile(r'<div id="tab-logs" class="tab-content">.*?</div>', re.DOTALL)
html = re.sub(logs_tab_regex, '', html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
