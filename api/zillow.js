export default async function handler(req, res) {
    const address = req.query.address;
    if (!address) {
        return res.status(400).json({ error: 'Address parameter required' });
    }

    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'identity',
        'Referer': 'https://www.zillow.com/',
    };

    try {
        // Step 1: Search Zillow autocomplete for the address
        const searchUrl = `https://www.zillowstatic.com/autocomplete/v3/suggestions?q=${encodeURIComponent(address)}&resultTypes=allAddress&resultCount=5`;
        const searchResp = await fetch(searchUrl, { headers });
        
        if (!searchResp.ok) {
            // Fallback: try the main search page
            const fallbackUrl = `https://www.zillow.com/homes/${encodeURIComponent(address)}_rb/`;
            const fallbackResp = await fetch(fallbackUrl, { headers });
            const html = await fallbackResp.text();
            
            // Try to extract __NEXT_DATA__ or preloaded data
            const nextDataMatch = html.match(/<script id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
            if (nextDataMatch) {
                try {
                    const nextData = JSON.parse(nextDataMatch[1]);
                    const searchResults = nextData?.props?.pageProps?.searchPageState?.cat1?.searchResults?.listResults || [];
                    if (searchResults.length > 0) {
                        const results = searchResults.slice(0, 5).map(r => ({
                            address: r.address || r.streetAddress || 'N/A',
                            city: r.addressCity || '',
                            state: r.addressState || '',
                            zip: r.addressZipcode || '',
                            price: r.price || r.unformattedPrice || 'N/A',
                            zestimate: r.zestimate || r.hdpData?.homeInfo?.zestimate || null,
                            rentZestimate: r.hdpData?.homeInfo?.rentZestimate || null,
                            beds: r.beds || r.hdpData?.homeInfo?.bedrooms || 'N/A',
                            baths: r.baths || r.hdpData?.homeInfo?.bathrooms || 'N/A',
                            sqft: r.area || r.hdpData?.homeInfo?.livingArea || 'N/A',
                            homeType: r.hdpData?.homeInfo?.homeType || 'N/A',
                            yearBuilt: r.hdpData?.homeInfo?.yearBuilt || 'N/A',
                            lotSize: r.hdpData?.homeInfo?.lotSize || null,
                            url: r.detailUrl ? `https://www.zillow.com${r.detailUrl}` : null,
                            zpid: r.zpid || r.hdpData?.homeInfo?.zpid || null,
                            status: r.statusText || r.statusType || 'N/A',
                            taxAssessment: r.hdpData?.homeInfo?.taxAssessedValue || null,
                            img: r.imgSrc || null,
                        }));
                        return res.status(200).json({ success: true, source: 'search', count: results.length, results });
                    }
                } catch(e) {}
            }

            // Secondary fallback: regex for data in the page
            const zestMatch = html.match(/"zestimate"\s*:\s*(\d+)/);
            const addrMatch = html.match(/"streetAddress"\s*:\s*"([^"]+)"/);
            const priceMatch = html.match(/"price"\s*:\s*(\d+)/);
            const bedsMatch = html.match(/"bedrooms"\s*:\s*(\d+)/);
            const bathsMatch = html.match(/"bathrooms"\s*:\s*([\d.]+)/);
            const sqftMatch = html.match(/"livingArea"\s*:\s*(\d+)/);
            const typeMatch = html.match(/"homeType"\s*:\s*"([^"]+)"/);
            const yearMatch = html.match(/"yearBuilt"\s*:\s*(\d+)/);
            const taxMatch = html.match(/"taxAssessedValue"\s*:\s*(\d+)/);
            const rentMatch = html.match(/"rentZestimate"\s*:\s*(\d+)/);
            const zpidMatch = html.match(/"zpid"\s*:\s*(\d+)/);

            if (zestMatch || priceMatch || addrMatch) {
                return res.status(200).json({
                    success: true,
                    source: 'regex_extract',
                    count: 1,
                    results: [{
                        address: addrMatch ? addrMatch[1] : address,
                        zestimate: zestMatch ? parseInt(zestMatch[1]) : null,
                        rentZestimate: rentMatch ? parseInt(rentMatch[1]) : null,
                        price: priceMatch ? parseInt(priceMatch[1]) : null,
                        beds: bedsMatch ? parseInt(bedsMatch[1]) : 'N/A',
                        baths: bathsMatch ? parseFloat(bathsMatch[1]) : 'N/A',
                        sqft: sqftMatch ? parseInt(sqftMatch[1]) : 'N/A',
                        homeType: typeMatch ? typeMatch[1] : 'N/A',
                        yearBuilt: yearMatch ? parseInt(yearMatch[1]) : 'N/A',
                        taxAssessment: taxMatch ? parseInt(taxMatch[1]) : null,
                        zpid: zpidMatch ? zpidMatch[1] : null,
                        url: zpidMatch ? `https://www.zillow.com/homedetails/${zpidMatch[1]}_zpid/` : null,
                    }]
                });
            }

            return res.status(404).json({ success: false, error: 'No property data found for this address' });
        }

        const searchData = await searchResp.json();
        const suggestions = searchData?.results || [];
        
        if (suggestions.length === 0) {
            return res.status(404).json({ success: false, error: 'No results found for this address' });
        }

        // Step 2: Get the first result's detail page
        const topResult = suggestions[0];
        const detailUrl = topResult.metaData?.url || topResult.display;
        
        if (!detailUrl) {
            return res.status(200).json({
                success: true,
                source: 'autocomplete',
                count: suggestions.length,
                results: suggestions.map(s => ({
                    address: s.display || 'N/A',
                    subtype: s.metaData?.subType || 'N/A',
                }))
            });
        }

        // Fetch detail page
        const fullUrl = detailUrl.startsWith('http') ? detailUrl : `https://www.zillow.com${detailUrl}`;
        const detailResp = await fetch(fullUrl, { headers });
        const detailHtml = await detailResp.text();

        // Extract data from __NEXT_DATA__ or inline scripts
        const nextDataMatch2 = detailHtml.match(/<script id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
        if (nextDataMatch2) {
            try {
                const nd = JSON.parse(nextDataMatch2[1]);
                const prop = nd?.props?.pageProps?.componentProps?.gdpClientCache;
                if (prop) {
                    const cacheKey = Object.keys(JSON.parse(prop))[0];
                    const propData = JSON.parse(prop)[cacheKey]?.property;
                    if (propData) {
                        return res.status(200).json({
                            success: true,
                            source: 'detail_page',
                            count: 1,
                            results: [{
                                address: propData.streetAddress || propData.address?.streetAddress || address,
                                city: propData.address?.city || '',
                                state: propData.address?.state || '',
                                zip: propData.address?.zipcode || '',
                                zestimate: propData.zestimate || null,
                                rentZestimate: propData.rentZestimate || null,
                                price: propData.price || null,
                                beds: propData.bedrooms || 'N/A',
                                baths: propData.bathrooms || 'N/A',
                                sqft: propData.livingArea || 'N/A',
                                homeType: propData.homeType || 'N/A',
                                yearBuilt: propData.yearBuilt || 'N/A',
                                lotSize: propData.lotSize || null,
                                taxAssessment: propData.taxAssessedValue || null,
                                zpid: propData.zpid || null,
                                url: fullUrl,
                                status: propData.homeStatus || 'N/A',
                            }]
                        });
                    }
                }
            } catch(e) {}
        }

        // Regex fallback on detail page
        const z2 = detailHtml.match(/"zestimate"\s*:\s*(\d+)/);
        const a2 = detailHtml.match(/"streetAddress"\s*:\s*"([^"]+)"/);
        const p2 = detailHtml.match(/"price"\s*:\s*(\d+)/);

        if (z2 || p2) {
            return res.status(200).json({
                success: true,
                source: 'detail_regex',
                count: 1,
                results: [{
                    address: a2 ? a2[1] : address,
                    zestimate: z2 ? parseInt(z2[1]) : null,
                    price: p2 ? parseInt(p2[1]) : null,
                }]
            });
        }

        return res.status(200).json({
            success: true,
            source: 'autocomplete_only',
            count: suggestions.length,
            results: suggestions.slice(0, 5).map(s => ({
                address: s.display || 'N/A',
            }))
        });

    } catch (err) {
        return res.status(500).json({ success: false, error: 'Zillow lookup failed', message: err.message });
    }
}
