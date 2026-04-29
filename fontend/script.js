let isCareValidated = false;

const API_URL = "http://localhost:8000";

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        renderSector('A');
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelector('.tab.active').classList.remove('active');
            tab.classList.add('active');

            const sector = tab.dataset.sector;

            if (sector === 'PLAN') {
                document.getElementById('patient-container').classList.add('hidden');
                document.getElementById('plan-container').classList.remove('hidden');
                updateHeatmap();
            } else {
                document.getElementById('plan-container').classList.add('hidden');
                document.getElementById('patient-container').classList.remove('hidden');
                renderSector(sector);
            }
        };
    });
});

async function renderSector(id) {
    const container = document.getElementById('patient-container');
    container.innerHTML = '<p>Chargement des résidents...</p>';

    try {
        const response = await fetch(`${API_URL}/residents`);

        if (!response.ok) {
            throw new Error("Erreur API");
        }

        const residents = await response.json();

        const filteredResidents = residents.filter(resident => {
            return resident.secteur === id;
        });

        container.innerHTML = '';

        if (filteredResidents.length === 0) {
            container.innerHTML = '<p>Aucun résident trouvé pour ce secteur.</p>';
            return;
        }

        filteredResidents.forEach(resident => {
            const risk = resident.risk_score ?? 0;
            const bpm = resident.heart_rate ?? "--";
            const spo2 = resident.spo2 ?? "--";
            const tension = resident.tension ?? "--/--";
            const temp = resident.temperature ?? "--";

            const card = document.createElement('div');

            card.className = `card ${risk > 80 ? 'status-high' : ''}`;

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px">
                    <strong style="font-size:18px">Chambre ${resident.chambre}</strong>
                    <span style="background:${risk > 80 ? '#FEE2E2' : '#ECFDF5'}; color:${risk > 80 ? 'var(--danger)' : '#059669'}; padding:5px 10px; border-radius:10px; font-size:12px; font-weight:800">
                        ${risk}% Risk IA
                    </span>
                </div>

                <div class="card-vitals" style="display:grid; grid-template-columns: 1fr 1fr; gap:10px">
                    <div class="vital-box" style="padding:10px">
                        <strong>${bpm}</strong>
                        <small>BPM</small>
                    </div>

                    <div class="vital-box" style="padding:10px">
                        <strong>${spo2}%</strong>
                        <small>SpO2</small>
                    </div>
                </div>
            `;

            card.onclick = () => openDrawer(`Chambre ${resident.chambre}`, {
                risk,
                bpm,
                spo2,
                tension,
                temp
            });

            container.appendChild(card);
        });

    } catch (error) {
        console.error(error);
        container.innerHTML = `
            <p style="color:red; font-weight:bold">
                Impossible de charger les données depuis FastAPI.
            </p>
            <p>Vérifie que ton backend est lancé sur http://localhost:8000</p>
        `;
    }
}

function openDrawer(name, data) {
    isCareValidated = false;

    document.getElementById('side-drawer').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('drawer-name').innerText = name;

    const banner = document.getElementById('care-banner');
    banner.style.background = "#FEF2F2";
    banner.style.color = "#991B1B";
    banner.innerText = "⚠️ INTERVENTION NON VALIDÉE";

    document.getElementById('soignant-note').value = "";
    document.getElementById('soignant-note').disabled = false;

    document.getElementById('drawer-vitals').innerHTML = `
        <div class="vital-box" style="grid-column: span 2; padding:30px; border: 2px solid var(--primary); background: #EEF2FF">
            <small style="color:var(--primary)">Score Prédictif IA</small>
            <strong>${data.risk}%</strong>
        </div>

        <div class="vital-box">
            <strong>${data.bpm}</strong>
            <small>BPM (Pouls)</small>
        </div>

        <div class="vital-box">
            <strong>${data.spo2}%</strong>
            <small>SpO2 (Sat.)</small>
        </div>

        <div class="vital-box">
            <strong>${data.tension}</strong>
            <small>Tension (mmHg)</small>
        </div>

        <div class="vital-box">
            <strong>${data.temp}°C</strong>
            <small>Température</small>
        </div>
    `;

    switchDrawerTab('vitals');
}

function validateCare() {
    const note = document.getElementById('soignant-note').value;

    if (note.length < 10) {
        alert("🔒 Erreur : Rapport de soin trop court (10 caractères minimum).");
        return;
    }

    isCareValidated = true;

    const banner = document.getElementById('care-banner');
    banner.innerText = "✅ INTERVENTION VALIDÉE & ARCHIVÉE";
    banner.style.background = "#ECFDF5";
    banner.style.color = "#065F46";

    document.getElementById('soignant-note').disabled = true;
}

function closeDrawer() {
    document.getElementById('side-drawer').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function switchDrawerTab(tabName) {
    document.getElementById('tab-vitals').classList.add('hidden');
    document.getElementById('tab-soins').classList.add('hidden');

    document.getElementById('btn-tab-vitals').classList.remove('active');
    document.getElementById('btn-tab-soins').classList.remove('active');

    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    document.getElementById(`btn-tab-${tabName}`).classList.add('active');
}

async function updateHeatmap() {
    try {
        const response = await fetch(`${API_URL}/residents`);
        const residents = await response.json();

        updateSectorRisk('A', residents);
        updateSectorRisk('B', residents);

    } catch (error) {
        console.error(error);
    }
}

function updateSectorRisk(sector, residents) {
    const sectorResidents = residents.filter(r => r.secteur === sector);

    if (sectorResidents.length === 0) {
        document.querySelector(`#map-sector-${sector} .zone-risk`).innerText = "--%";
        return;
    }

    const averageRisk = Math.round(
        sectorResidents.reduce((sum, r) => sum + (r.risk_score ?? 0), 0) / sectorResidents.length
    );

    document.querySelector(`#map-sector-${sector} .zone-risk`).innerText = `${averageRisk}%`;
}

function selectSector(sector) {
    document.getElementById('plan-container').classList.add('hidden');
    document.getElementById('patient-container').classList.remove('hidden');

    document.querySelector('.tab.active').classList.remove('active');
    document.querySelector(`[data-sector="${sector}"]`).classList.add('active');

    renderSector(sector);
}