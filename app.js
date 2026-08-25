// State Management
let computedAspectEvents = [];
let chartInstance = null;

// Zodiac Names
const ZODIACS = [
    "Aries", "Taurus", "Gemini", "Cancer", 
    "Leo", "Virgo", "Libra", "Scorpio", 
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
];

// Aspect Definitions in Degrees
const ASPECT_DEGREES = {
    "Conjunction": 0,
    "Sextile": 60,
    "Square": 90,
    "Trine": 120,
    "Opposition": 180
};

// Switch Sidebar Tabs
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    event.currentTarget.classList.add('active');

    if (tabId === 'charts') {
        renderAspectChart();
    }
}

// Convert Ecliptic Longitude to Zodiac Sign Name
function getZodiacSign(longitude) {
    const index = Math.floor(longitude / 30) % 12;
    return ZODIACS[index];
}

// Aspect Calculation Engine using Astronomy Engine JS
function calculateAspects() {
    const p1Name = document.getElementById('planet1').value;
    const p2Name = document.getElementById('planet2').value;
    const aspectType = document.getElementById('aspectType').value;
    const years = parseInt(document.getElementById('yearsBack').value);

    const targetAngle = ASPECT_DEGREES[aspectType];
    const events = [];

    const now = new Date();
    const daysRange = years * 365;

    let prevMatch = false;

    for (let d = -daysRange; d <= 30; d += 2) { // Step every 2 days for performance
        const checkDate = new Date(now.getTime() + d * 86400000);
        
        // Calculate Geocentric Positions
        const pos1 = Astronomy.Ecliptic(Astronomy.GeoVector(Astronomy.Body[p1Name], checkDate, true));
        const pos2 = Astronomy.Ecliptic(Astronomy.GeoVector(Astronomy.Body[p2Name], checkDate, true));

        const lon1 = pos1.elon;
        const lon2 = pos2.elon;

        let diff = Math.abs(lon1 - lon2) % 360;
        if (diff > 180) diff = 360 - diff;

        // Check if within 2.5 degrees orb
        const isMatch = Math.abs(diff - targetAngle) <= 2.5;

        if (isMatch && !prevMatch) {
            events.push({
                date: checkDate.toISOString().split('T')[0],
                planet1: p1Name,
                zodiac1: getZodiacSign(lon1),
                planet2: p2Name,
                zodiac2: getZodiacSign(lon2),
                aspect: aspectType
            });
        }
        prevMatch = isMatch;
    }

    computedAspectEvents = events;
    renderAspectsTable(events);
    
    // Enable Scan Button
    const scanBtn = document.getElementById('runScanBtn');
    const statusInfo = document.getElementById('aspectStatusInfo');
    scanBtn.disabled = false;
    statusInfo.innerText = `Ready to scan across ${events.length} aspect start dates.`;
}

// Populate Aspects Output Table
function renderAspectsTable(events) {
    const tbody = document.querySelector('#aspectsTable tbody');
    tbody.innerHTML = '';

    if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No aspect events matched the criteria.</td></tr>';
        return;
    }

    events.forEach(e => {
        const row = `<tr>
            <td>${e.date}</td>
            <td>${e.planet1}</td>
            <td>${e.zodiac1}</td>
            <td>${e.planet2}</td>
            <td>${e.zodiac2}</td>
            <td>${e.aspect}</td>
        </tr>`;
        tbody.innerHTML += row;
    });
}

// Client-Side Stock Scanner Simulation (Simulates Parquet Scan)
function runStockScan() {
    const tbody = document.querySelector('#scanResultsTable tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Scanning target data...</td></tr>';

    setTimeout(() => {
        tbody.innerHTML = '';
        const mockSymbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"];
        
        computedAspectEvents.forEach(e => {
            mockSymbols.forEach(sym => {
                const maxReturn = (Math.random() * 15 - 5).toFixed(2);
                const minReturn = (Math.random() * -12).toFixed(2);
                const direction = maxReturn > 8 ? "UP" : (minReturn < -8 ? "DOWN" : "NEUTRAL");

                if (direction !== "NEUTRAL") {
                    const row = `<tr>
                        <td><strong>${sym}</strong></td>
                        <td>${e.date}</td>
                        <td>₹${(Math.random() * 2000 + 500).toFixed(2)}</td>
                        <td>+${maxReturn}%</td>
                        <td>${minReturn}%</td>
                        <td><span class="${direction === 'UP' ? 'badge-up' : 'badge-down'}">${direction}</span></td>
                    </tr>`;
                    tbody.innerHTML += row;
                }
            });
        });
    }, 600);
}

// Render Interactive Performance Chart
function renderAspectChart() {
    const ctx = document.getElementById('aspectChart').getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = computedAspectEvents.map(e => e.date);
    const mockPerformance = labels.map(() => (Math.random() * 20 - 10).toFixed(2));

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['No Events'],
            datasets: [{
                label: 'Average Price Reaction (%)',
                data: mockPerformance.length ? mockPerformance : [0],
                backgroundColor: mockPerformance.map(v => v >= 0 ? '#00c896' : '#ff5252')
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#ffffff' } }
            },
            scales: {
                x: { ticks: { color: '#8a99ad' }, grid: { color: '#233554' } },
                y: { ticks: { color: '#8a99ad' }, grid: { color: '#233554' } }
            }
        }
    });
}
