<<<<<<< HEAD
// --- CONFIGURATION ---
const MQTT_HOST = window.location.hostname; 
const MQTT_PORT = 9001; // Port WebSocket de Mosquitto
const CLIENT_ID = "SanteOS_Front_" + Math.random().toString(16).substr(2, 5);

let mqttClient;
let currentPatientId = null;

// Liste synchronisée avec tes IDs de residents.csv
let PATIENTS = [
  { id:'101', name:'Dubois Martin', age:'67 ans', status:'stable', hr:0, ox:0, bp:'0/0', tmp:'0', diag:'Post-op', history: [] },
  { id:'102', name:'Lefevre Sophie', age:'54 ans', status:'stable', hr:0, ox:0, bp:'0/0', tmp:'0', diag:'Sepsis', history: [] },
  { id:'103', name:'Bernard Jean', age:'78 ans', status:'stable', hr:0, ox:0, bp:'0/0', tmp:'0', diag:'Pneumonie', history: [] },
  { id:'104', name:'Moreau Claire', age:'45 ans', status:'stable', hr:0, ox:0, bp:'0/0', tmp:'0', diag:'Trauma', history: [] },
  { id:'105', name:'Petit Robert', age:'82 ans', status:'stable', hr:0, ox:0, bp:'0/0', tmp:'0', diag:'Cardio', history: [] }
];

const LABELS  = { stable:'STABLE', urgent:'URGENT', critical:'CRITIQUE', dead:'ARRÊT' };
const TAG_CLS = { stable:'tag-stable', urgent:'tag-urgent', critical:'tag-critical', dead:'tag-dead' };
const PV_CLS  = { stable:'ok', urgent:'warn', critical:'crit', dead:'gone' };
const COLORS  = { stable:'#00a878', urgent:'#fd7e14', critical:'#e63946', dead:'#495057' };

// --- 1. CONNEXION AU BACKEND (MQTT) ---
function initMQTT() {
    mqttClient = new Paho.MQTT.Client(MQTT_HOST, MQTT_PORT, CLIENT_ID);

    mqttClient.onMessageArrived = (message) => {
        const topic = message.destinationName;
        const data = JSON.parse(message.payloadString);

        if (topic.includes("vitals")) {
            const resId = topic.split('/')[2];
            updatePatientVitals(resId, data);
        } else if (topic === "ehpad/alerts") {
            handleIncomingAlert(data);
        }
    };

    mqttClient.connect({
        onSuccess: () => {
            console.log("✅ Connecté au système de capteurs");
            mqttClient.subscribe("ehpad/residents/+/vitals");
            mqttClient.subscribe("ehpad/alerts");
        },
        onFailure: () => setTimeout(initMQTT, 5000),
        useSSL: false
    });
}

// --- 2. TRAITEMENT DES DONNÉES RÉELLES ---
function updatePatientVitals(id, data) {
    const p = PATIENTS.find(pt => pt.id === id);
    if (!p) return;

    p.hr = data.heart_rate;
    p.ox = data.spo2;
    p.bp = `${data.systolic_bp}/${data.diastolic_bp}`;
    p.tmp = data.temperature;

    renderGrid(PATIENTS);
    updateMapStatus();
    if (currentPatientId === id) refreshPanelUI(p);
}

function handleIncomingAlert(alert) {
    const p = PATIENTS.find(pt => pt.id === alert.res_id);
    if (!p) return;

    // Mapping des niveaux du Processor.py (1-5) vers le Front
    if (alert.level >= 4) p.status = 'critical';
    else if (alert.level >= 2) p.status = 'urgent';

    // Ajout du rapport IA (Mistral) dans l'historique
    const timeStr = new Date().toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});
    let log = `⚠️ ${alert.text}`;
    if (alert.llm_report) log += `<br><small><i>Rapport IA : ${alert.llm_report}</i></small>`;

    p.history.push({ time: timeStr, text: log });
    
    if (alert.level >= 4) showToast(`ALERTE CRITIQUE : Chambre ${alert.res_id}`);
    renderGrid(PATIENTS);
}

// --- 3. INTERFACE & NAVIGATION ---
function renderGrid(pts) {
    const grid = document.getElementById('grid');
    if (!grid) return;
    grid.innerHTML = pts.map(p => `
        <div class="pcard ${p.status}" onclick='openPanelById("${p.id}")'>
            <div class="pcard-top">
                <div class="pcard-room">${p.id}</div>
                <span class="pcard-tag ${TAG_CLS[p.status]}">${LABELS[p.status]}</span>
            </div>
            <div class="pcard-name">${p.name}</div>
            <div class="pcard-vitals">
                <div class="pv"><div class="pv-label">HR</div><div class="pv-val ${PV_CLS[p.status]}">${p.hr}</div></div>
                <div class="pv"><div class="pv-label">SpO2</div><div class="pv-val ${PV_CLS[p.status]}">${p.ox}%</div></div>
            </div>
        </div>
    `).join('');
}

function openPanelById(id) {
    const p = PATIENTS.find(pt => pt.id === id);
    if (p) openPanel(p);
}

function openPanel(p) {
    currentPatientId = p.id;
    document.getElementById('p-room').textContent = 'CHAMBRE ' + p.id;
    document.getElementById('p-name').textContent = p.name;
    refreshPanelUI(p);
    
    // Historique type Chat
    const chat = document.getElementById('chat-history');
    chat.innerHTML = p.history.map(m => `
        <div style="background:var(--surface2); padding:8px; border-radius:4px; border-left:3px solid var(--accent); margin-bottom:5px;">
            <div style="font-size:9px; color:var(--accent); font-weight:bold;">${m.time}</div>
            <div style="font-size:12px; color:var(--text);">${m.text}</div>
        </div>
    `).join('') || '<div style="text-align:center; padding-top:50px; color:var(--muted);">Aucun historique</div>';
    
    document.getElementById('panel').classList.add('show');
    document.getElementById('mask').classList.add('show');
    chat.scrollTop = chat.scrollHeight;
}

function refreshPanelUI(p) {
    const col = COLORS[p.status];
    document.getElementById('v-hr').innerHTML = `${p.hr}<span class="vb-unit">bpm</span>`;
    document.getElementById('v-ox').innerHTML = `${p.ox}<span class="vb-unit">%</span>`;
    document.getElementById('v-bp').innerHTML = `${p.bp}<span class="vb-unit">mmHg</span>`;
    document.getElementById('v-tmp').innerHTML = `${p.tmp}<span class="vb-unit">°C</span>`;
    document.querySelectorAll('.vb-val').forEach(el => el.style.color = col);
}

function saveIntervention() {
    const note = document.getElementById('note').value.trim();
    if (!note) return alert("Observation requise");

    // Envoyer l'acquittement au Backend (pour stopper l'escalade)
    const ack = { res_id: currentPatientId, staff: "Dr. Morel" };
    const msg = new Paho.MQTT.Message(JSON.stringify(ack));
    msg.destinationName = "ehpad/alerts/ack";
    mqttClient.send(msg);

    // Mettre à jour le local
    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    p.history.push({ time: new Date().toLocaleTimeString(), text: `✅ INTERVENTION : ${note}` });
    p.status = 'stable';
    
    closePanel();
    renderGrid(PATIENTS);
}

// --- FONCTIONS SYSTÈME ---
function doLogin() {
    document.getElementById('login').style.display = 'none';
    document.getElementById('shell').classList.add('in');
    initMQTT(); // On lance MQTT au login
    renderGrid(PATIENTS);
}

function setNav(btn, view) {
    document.querySelectorAll('.sb-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('view-grid').style.display = (view === 'grid') ? 'block' : 'none';
    document.getElementById('view-map').style.display = (view === 'map') ? 'block' : 'none';
    if(view === 'map') updateMapStatus();
}

function updateMapStatus() {
    PATIENTS.forEach(p => {
        const el = document.getElementById(`room-${p.id}`);
        if (el) {
            el.classList.remove('map-critical');
            const rect = el.querySelector('rect');
            if (p.status === 'critical') el.classList.add('map-critical');
            else if (p.status === 'urgent') rect.style.fill = 'rgba(253, 126, 20, 0.4)';
            else rect.style.fill = 'rgba(0, 168, 120, 0.1)';
        }
    });
}

function closePanel() { 
    document.getElementById('panel').classList.remove('show'); 
    document.getElementById('mask').classList.remove('show'); 
}

function showToast(m) {
    const t = document.getElementById('toast');
    t.innerHTML = m; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 4000);
}

setInterval(() => {
    const d = new Date();
    document.getElementById('clock').textContent = d.toLocaleTimeString('fr-FR');
}, 1000);
=======
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
>>>>>>> bcbc6c4b90b274ea40a14a828078403c56a12413
