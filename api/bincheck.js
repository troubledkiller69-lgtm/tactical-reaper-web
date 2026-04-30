export default async function handler(req, res) {
  const { bin } = req.query;
  if (!bin) return res.status(400).json({ error: 'BIN required' });

  try {
    const response = await fetch(`https://bin-ip-checker.p.rapidapi.com/?bin=${bin}`, {
      method: 'GET',
      headers: {
        'x-rapidapi-host': 'bin-ip-checker.p.rapidapi.com',
        'x-rapidapi-key': 'f1ec860047msh63c470a43018e13p1ac454jsne0f6f987b802'
      }
    });
    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: 'Lookup failed', details: error.message });
  }
}
