from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import phonenumbers
from phonenumbers import carrier as pn_carrier

# ── US CARRIER → EMAIL GATEWAY MAP ──
CARRIER_GATEWAYS = {
    'AT&T':              {'sms': 'txt.att.net',                'mms': 'mms.att.net'},
    'T-Mobile':          {'sms': 'tmomail.net',                'mms': 'tmomail.net'},
    'Verizon':           {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Sprint':            {'sms': 'messaging.sprintpcs.com',    'mms': 'pm.sprint.com'},
    'US Cellular':       {'sms': 'email.uscc.net',             'mms': 'mms.uscc.net'},
    'Boost Mobile':      {'sms': 'sms.myboostmobile.com',      'mms': 'myboostmobile.com'},
    'Cricket':           {'sms': 'sms.cricketwireless.net',    'mms': 'mms.cricketwireless.net'},
    'Metro PCS':         {'sms': 'mymetropcs.com',             'mms': 'mymetropcs.com'},
    'Google Fi':         {'sms': 'msg.fi.google.com',          'mms': 'msg.fi.google.com'},
    'Consumer Cellular': {'sms': 'mailmymobile.net',           'mms': 'mailmymobile.net'},
    'Virgin Mobile':     {'sms': 'vmobl.com',                  'mms': 'vmpix.com'},
    'Republic Wireless': {'sms': 'text.republicwireless.com',  'mms': 'text.republicwireless.com'},
    'Xfinity Mobile':    {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Mint Mobile':       {'sms': 'tmomail.net',                'mms': 'tmomail.net'},
    'Visible':           {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
    'Straight Talk':     {'sms': 'vtext.com',                  'mms': 'mypixmessages.com'},
    'TracFone':          {'sms': 'mmst5.tracfone.com',         'mms': 'mmst5.tracfone.com'},
    'Ting':              {'sms': 'message.ting.com',            'mms': 'message.ting.com'},
    'C Spire':           {'sms': 'cspire1.com',                'mms': 'cspire1.com'},
    'Spectrum Mobile':   {'sms': 'vtext.com',                  'mms': 'vzwpix.com'},
}

# Fuzzy alias resolution — phonenumbers returns inconsistent names
CARRIER_ALIASES = {
    'at&t':                  'AT&T',
    'att':                   'AT&T',
    'at&t mobility':         'AT&T',
    'new cingular':          'AT&T',
    'cingular':              'AT&T',
    't-mobile':              'T-Mobile',
    't-mobile usa':          'T-Mobile',
    'metro by t-mobile':     'Metro PCS',
    'metropcs':              'Metro PCS',
    'verizon':               'Verizon',
    'verizon wireless':      'Verizon',
    'cellco partnership':    'Verizon',
    'cellco':                'Verizon',
    'sprint':                'Sprint',
    'sprint spectrum':       'Sprint',
    'us cellular':           'US Cellular',
    'united states cellular':'US Cellular',
    'boost mobile':          'Boost Mobile',
    'cricket':               'Cricket',
    'cricket communications':'Cricket',
    'google fi':             'Google Fi',
    'google':                'Google Fi',
    'consumer cellular':     'Consumer Cellular',
    'virgin mobile':         'Virgin Mobile',
    'republic wireless':     'Republic Wireless',
    'xfinity mobile':        'Xfinity Mobile',
    'comcast':               'Xfinity Mobile',
    'mint mobile':           'Mint Mobile',
    'visible':               'Visible',
    'straight talk':         'Straight Talk',
    'tracfone':              'TracFone',
    'ting':                  'Ting',
    'c spire':               'C Spire',
    'c-spire':               'C Spire',
    'page plus':             'Visible',
    'spectrum mobile':       'Spectrum Mobile',
    'charter':               'Spectrum Mobile',
}

def resolve_carrier(raw_name):
    if not raw_name:
        return None
    lower = raw_name.lower().strip()
    if raw_name in CARRIER_GATEWAYS:
        return raw_name
    if lower in CARRIER_ALIASES:
        return CARRIER_ALIASES[lower]
    for alias, canonical in CARRIER_ALIASES.items():
        if alias in lower or lower in alias:
            return canonical
    return None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            phone = params.get('phone', [None])[0]
            if not phone:
                self._json(400, {'error': 'Missing ?phone= parameter'})
                return
            self._lookup(phone)
        except Exception as e:
            self._json(500, {'error': str(e)})

    def do_POST(self):
        try:
            cl = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(cl).decode('utf-8'))
            phone = body.get('phone')
            if not phone:
                self._json(400, {'error': 'Missing phone in body'})
                return
            self._lookup(phone)
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _lookup(self, phone):
        try:
            number = phonenumbers.parse(phone, 'US')
        except Exception:
            self._json(400, {'error': 'Cannot parse phone number'})
            return

        if not phonenumbers.is_valid_number(number):
            self._json(400, {'error': 'Invalid phone number'})
            return

        raw_carrier = pn_carrier.name_for_number(number, 'en')
        canonical = resolve_carrier(raw_carrier)
        national = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
        digits = ''.join(filter(str.isdigit, national))

        result = {
            'phone': phone,
            'national': national,
            'digits': digits,
            'carrier_raw': raw_carrier or 'Unknown',
            'carrier': canonical or raw_carrier or 'Unknown',
            'resolved': canonical is not None and canonical in CARRIER_GATEWAYS,
        }

        if canonical and canonical in CARRIER_GATEWAYS:
            gw = CARRIER_GATEWAYS[canonical]
            result['sms_gateway'] = f"{digits}@{gw['sms']}"
            result['mms_gateway'] = f"{digits}@{gw['mms']}"
            result['sms_domain'] = gw['sms']
            result['mms_domain'] = gw['mms']

        # Always return full gateway map for manual override
        result['all_carriers'] = {k: v['sms'] for k, v in CARRIER_GATEWAYS.items()}
        self._json(200, result)

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
