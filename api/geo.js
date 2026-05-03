export default async function handler(req, res) {
    const ip = req.query.ip;
    if (!ip) {
        return res.status(400).json({ error: 'IP parameter required' });
    }

    try {
        const response = await fetch(`https://ipwho.is/${ip}`);
        const data = await response.json();
        res.setHeader('Access-Control-Allow-Origin', '*');
        return res.status(200).json(data);
    } catch (err) {
        return res.status(500).json({ error: 'Upstream lookup failed', details: err.message });
    }
}
