document.addEventListener("DOMContentLoaded", () => {
    loadDashboardData();
});

async function loadDashboardData() {
    try {
        const response = await fetch("scan_results.json");
        if (!response.ok) throw new Error("Local data file not found.");
        
        const data = await response.json();
        
        renderAspectsTable(data.aspect_events);
        renderScanResultsTable(data.scan_results);
        
        console.log(`Data updated as of: ${data.generated_at}`);
    } catch (err) {
        console.error("Failed to load JSON data:", err);
    }
}

function renderAspectsTable(events) {
    const tbody = document.querySelector("#aspectsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    events.forEach(e => {
        tbody.innerHTML += `
            <tr>
                <td>${e.date}</td>
                <td>${e.time}</td>
                <td>${e.planet1} (${e.zodiac1})</td>
                <td>${e.planet2} (${e.zodiac2})</td>
                <td>${e.aspect}</td>
            </tr>`;
    });
}

function renderScanResultsTable(results) {
    const tbody = document.querySelector("#scanResultsTable tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    results.forEach(r => {
        const badgeClass = r.direction === "UP" ? "badge-up" : "badge-down";
        tbody.innerHTML += `
            <tr>
                <td><strong>${r.symbol}</strong></td>
                <td>${r.aspect_date}</td>
                <td>₹${r.close}</td>
                <td>+${r.pct_max}%</td>
                <td>${r.pct_min}%</td>
                <td><span class="${badgeClass}">${r.direction}</span></td>
            </tr>`;
    });
}
