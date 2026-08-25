document.addEventListener("DOMContentLoaded", () => {
    loadData();
});

// Load local scan_results.json
async function loadData() {
    try {
        const res = await fetch("scan_results.json?t=" + new Date().getTime());
        if (!res.ok) throw new Error("scan_results.json not found.");
        const data = await res.json();
        
        renderAspects(data.aspect_events || []);
        renderResults(data.scan_results || []);
    } catch (err) {
        showStatus("No generated data found. Click 'Update Data' to run calculation engine.", "info");
    }
}

// Trigger Local Workflow Server via Button Press
async function triggerWorkflow() {
    const btn = document.getElementById("updateDataBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Engine...';
    showStatus("Running Swiss Ephemeris scanner engine. Please wait...", "info");

    try {
        const response = await fetch("/api/run-scan", { method: "POST" });
        const result = await response.json();

        if (response.ok) {
            showStatus("Data successfully updated!", "success");
            await loadData();
        } else {
            showStatus("Error: " + result.message, "danger");
        }
    } catch (err) {
        showStatus("Workflow Server offline. Please run 'run_workflow.bat' first.", "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-sync"></i> Update Data';
    }
}

function renderAspects(events) {
    const tbody = document.querySelector("#aspectsTable tbody");
    tbody.innerHTML = events.length ? "" : '<tr><td colspan="5" class="text-center">No events found.</td></tr>';
    events.forEach(e => {
        tbody.innerHTML += `<tr>
            <td>${e.date}</td>
            <td>${e.time}</td>
            <td>${e.planet1} (${e.zodiac1})</td>
            <td>${e.planet2} (${e.zodiac2})</td>
            <td>${e.aspect}</td>
        </tr>`;
    });
}

function renderResults(results) {
    const tbody = document.querySelector("#scanResultsTable tbody");
    tbody.innerHTML = results.length ? "" : '<tr><td colspan="6" class="text-center">No scanner results found.</td></tr>';
    results.forEach(r => {
        tbody.innerHTML += `<tr>
            <td><strong>${r.symbol}</strong></td>
            <td>${r.aspect_date}</td>
            <td>₹${r.close}</td>
            <td>+${r.pct_max}%</td>
            <td>${r.pct_min}%</td>
            <td><span class="${r.direction === 'UP' ? 'badge-up' : 'badge-down'}">${r.direction}</span></td>
        </tr>`;
    });
}

function showStatus(message, type) {
    const alert = document.getElementById("statusAlert");
    alert.className = `alert-box alert-${type}`;
    alert.innerText = message;
    alert.style.display = "block";
}
