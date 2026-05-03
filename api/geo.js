export default async function handler(req, res) {
    const ip = req.query.ip;
    if (!ip) {
        return res.status(400).json({ error: 'IP parameter required' });
    }

    try {
        const response = await fetch(`http://ip-api.com/json/${ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query`);
        const data = await response.json();
        
        // Normalize to a consistent format
        if (data.status === 'success') {
            return res.status(200).json({
                success: true,
                ip: data.query,
                type: 'IPv4',
                country: data.country,
                country_code: data.countryCode,
                region: data.regionName,
                city: data.city,
                postal: data.zip,
                latitude: data.lat,
                longitude: data.lon,
                timezone: { id: data.timezone },
                connection: {
                    isp: data.isp,
                    org: data.org,
                    asn: data.as
                }
            });
        } else {
            return res.status(400).json({ success: false, message: data.message || 'Lookup failed' });
        }
    } catch (err) {
        return res.status(500).json({ success: false, error: 'Upstream lookup failed', message: err.message });
    }
}
