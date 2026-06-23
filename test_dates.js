const fs = require('fs');
const https = require('https');

https.get("https://query1.finance.yahoo.com/v8/finance/chart/1757.HK?interval=1d&range=1y", {
  headers: {
    'User-Agent': 'Mozilla/5.0'
  }
}, (res) => {
  let data = '';
  res.on('data', d => data += d);
  res.on('end', () => {
    const json = JSON.parse(data);
    const result = json.chart.result[0];
    const timestamps = result.timestamp;
    
    let lastDate = null;
    let duplicateFound = false;
    
    for (let i = 0; i < timestamps.length; i++) {
        const date = new Date(timestamps[i] * 1000);
        const timeString = date.toISOString().split('T')[0];
        
        if (timeString === lastDate) {
           console.log("DUPLICATE FOUND!", timeString);
           duplicateFound = true;
        } else if (lastDate && timeString < lastDate) {
           console.log("OUT OF ORDER!", lastDate, timeString);
        }
        lastDate = timeString;
    }
    
    if (!duplicateFound) console.log("All dates are unique and strictly ascending.");
  });
});
