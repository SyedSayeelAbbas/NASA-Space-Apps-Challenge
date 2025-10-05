let map = null;
let marker = null;

document.getElementById('dateInput').value = new Date().toISOString().split('T')[0];

const METRICS = [
    { id: 'hot', key: 'very_hot', label: 'Very hot', color: '#ff6b6b' },
    { id: 'cold', key: 'very_cold', label: 'Very cold', color: '#6b9bff' },
    { id: 'wet', key: 'very_wet', label: 'Very wet', color: '#70d6ff' },
    { id: 'windy', key: 'very_windy', label: 'Very windy', color: '#7dd3c0' },
    { id: 'uncomfortable', key: 'uncomfortable', label: 'Uncomfortable', color: '#ff9ff3' }
];

async function checkWeather() {
    const city = document.getElementById("cityInput").value || "Karachi";
    const pin = document.getElementById("pinInput").value;
    const date = document.getElementById("dateInput").value;
    const selected = Array.from(document.querySelectorAll('.checkbox-item input:checked')).map(cb => cb.id);

    const lat_lon = pin ? pin.trim() : null;
    document.body.classList.add('loading');

    try {
        const resp = await fetch("/check", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city, date, selected_metrics: selected, lat_lon })
        });

        if (!resp.ok) throw new Error(`Server ${resp.status}`);
        const data = await resp.json();

        // UPDATE MAP VIEW AND MARKER WITH ACTUAL CITY NAME
        if (data.coords && data.coords.length === 2) {
            const [lat, lon] = data.coords;
            if (map) {
                map.setView([lat, lon], 10);
                
                // Remove existing marker if any
                if (marker) {
                    map.removeLayer(marker);
                }
                
                const displayName = data.city || city || 'Selected Location';
                marker = L.marker([lat, lon]).addTo(map)
                    .bindPopup(displayName)
                    .openPopup();
            }
        }

        const barChart = document.getElementById("barChart");
        barChart.innerHTML = '';
        const useDefs = (selected.length === 0) ? METRICS : METRICS.filter(m => selected.includes(m.id));

        useDefs.forEach((m) => {
            const prob = (data.probabilities && typeof data.probabilities[m.key] === 'number') ? data.probabilities[m.key] : 0;
            const barItem = document.createElement('div');
            barItem.className = 'bar-item';
            barItem.innerHTML = `
                <div class="bar" style="height: ${prob}%; background: ${m.color};"></div>
                <span class="bar-label">${m.label}</span>
                <div style="font-size:12px;color:#333;margin-top:6px">${prob}%</div>
            `;
            barChart.appendChild(barItem);
        });

        drawLineChart(data.time_series || []);

        const hp = (data.probabilities && data.probabilities.very_hot) ? data.probabilities.very_hot : 0;
        const wp = (data.probabilities && data.probabilities.very_wet) ? data.probabilities.very_wet : 0;
        const actualCity = data.city || city || 'Selected Location';
        
        document.getElementById("infoCard").innerHTML = `
            <div class="info-icons">🔥💧</div>
            <div class="info-text">
                <h3>${hp}% Very Hot</h3>
                <p>For ${actualCity} on ${date}, there's ${hp}% chance of extreme heat (>40°C) and ${wp}% chance of heavy rain.</p>
            </div>
        `;

    } catch (err) {
        console.error(err);
        alert(`Oops: ${err.message}. Try a past date or change city/coords.`);
    } finally {
        document.body.classList.remove('loading');
    }
}

function drawLineChart(ts) {
    const svg = document.getElementById('lineChart');
    const viewW = 500, viewH = 200;
    svg.innerHTML = '';

    if (!ts || ts.length === 0) {
        svg.innerHTML = `<text x="20" y="${viewH / 2}" fill="#999">No time-series data</text>`;
        return;
    }

    const last = ts.slice(-6);
    const leftPad = 40, rightPad = 20, topPad = 20, bottomPad = 30;
    const width = viewW - leftPad - rightPad;
    const height = viewH - topPad - bottomPad;
    const n = last.length;
    const xFor = (i) => leftPad + (n === 1 ? width / 2 : (i * (width / (n - 1))));

    const maxHot = Math.max(...last.map(p => p.hot || 0), 1);
    const maxWet = Math.max(...last.map(p => p.wet || 0), 1);

    const buildPath = (arr, maxVal) => {
        return arr.map((v, i) => {
            const x = xFor(i);
            const ratio = (maxVal === 0) ? 0 : (v / maxVal);
            const y = topPad + (height - ratio * height);
            return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
        }).join(' ');
    };

    const hotPath = buildPath(last.map(p => p.hot || 0), maxHot);
    const wetPath = buildPath(last.map(p => p.wet || 0), maxWet);

    svg.innerHTML += `<line x1="${leftPad}" y1="${topPad}" x2="${leftPad}" y2="${topPad + height}" stroke="#eee"/>`;
    svg.innerHTML += `<path d="${hotPath}" stroke="#ff6b6b" stroke-width="3" fill="none"/>`;
    svg.innerHTML += `<path d="${wetPath}" stroke="#70d6ff" stroke-width="3" fill="none"/>`;

    last.forEach((p, i) => {
        const x = xFor(i);
        const yHot = topPad + (height - ((p.hot || 0) / maxHot) * height);
        const yWet = topPad + (height - ((p.wet || 0) / maxWet) * height);
        svg.innerHTML += `<circle cx="${x}" cy="${yHot}" r="3" fill="#ff6b6b"></circle>`;
        svg.innerHTML += `<circle cx="${x}" cy="${yWet}" r="3" fill="#70d6ff"></circle>`;
        svg.innerHTML += `<text x="${x}" y="${topPad + height + 18}" font-size="11" text-anchor="middle" fill="#666">${p.date}</text>`;
    });

    svg.innerHTML += `<rect x="${viewW - 140}" y="${topPad}" width="10" height="10" fill="#ff6b6b"></rect>`;
    svg.innerHTML += `<text x="${viewW - 124}" y="${topPad + 9}" font-size="11" fill="#333">Temp (°C)</text>`;
    svg.innerHTML += `<rect x="${viewW - 140}" y="${topPad + 18}" width="10" height="10" fill="#70d6ff"></rect>`;
    svg.innerHTML += `<text x="${viewW - 124}" y="${topPad + 27}" font-size="11" fill="#333">Rain (mm)</text>`;
}

/* ---------- File downloads ---------- */
async function downloadCSV() {
    try {
        const city = document.getElementById("cityInput").value || "Karachi";
        const date = document.getElementById("dateInput").value;
        const resp = await fetch("/download/csv", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city, date })
        });
        if (!resp.ok) throw new Error('CSV download failed');

        const blob = await resp.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${city}_weather.csv`;
        link.click();
    } catch (e) {
        alert("CSV download not available on this backend.");
        console.error(e);
    }
}

async function downloadJSON() {
    try {
        const city = document.getElementById("cityInput").value || "Karachi";
        const date = document.getElementById("dateInput").value;
        const resp = await fetch("/download/json", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city, date })
        });
        if (!resp.ok) throw new Error('JSON download failed');

        const blob = await resp.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${city}_weather.json`;
        link.click();
    } catch (e) {
        alert("JSON download not available on this backend.");
        console.error(e);
    }
}

/* ---------- Map Initialization ---------- */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map
    map = L.map('map').setView([24.86, 67.00], 10);

    // OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Add initial marker for Karachi
    marker = L.marker([24.86, 67.00]).addTo(map)
        .bindPopup('Karachi')
        .openPopup();

    // On map click: set pin + update input field
    map.on('click', function(e) {
        const lat = e.latlng.lat.toFixed(5);
        const lon = e.latlng.lng.toFixed(5);

        if (marker) map.removeLayer(marker);
        marker = L.marker([lat, lon]).addTo(map)
            .bindPopup(`Selected Location: ${lat}, ${lon}`)
            .openPopup();

        document.getElementById('pinInput').value = `${lat},${lon}`;
        
        // Clear city input when user clicks on map
        document.getElementById('cityInput').value = '';
    });
});
