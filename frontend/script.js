// --- CONFIGURATION ---
const MQTT_HOST = window.location.hostname;
const MQTT_PORT = 9001;
const CLIENT_ID = "SanteOS_Front_" + Math.random().toString(16).substr(2, 5);

let mqttClient;
let currentPatientId = null; 

let PATIENTS = [];

const LABELS  = { stable:'STABLE', urgent:'URGENT', critical:'CRITIQUE', dead:'ARRÊT' };
const TAG_CLS = { stable:'tag-stable', urgent:'tag-urgent', critical:'tag-critical', dead:'tag-dead' };
const PV_CLS  = { stable:'ok', urgent:'warn', critical:'crit', dead:'gone' };
const COLORS  = { stable:'#00a878', urgent:'#fd7e14', critical:'#e63946', dead:'#495057' };

// --- 1. CHARGEMENT INITIAL DEPUIS FASTAPI ---
async function loadResidents() {
    try {
        const resp = await fetch('/api/residents');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        PATIENTS = data.map(r => ({
            id:      r.id,
            room:    String(r.chambre),
            name:    r.nom || `Résident ${r.id}`,
            age:     '--',
            status:  riskToStatus(r.risk_score),
            hr:      r.heart_rate  ?? 0,
            ox:      r.spo2        ?? 0,
            bp:      r.tension     ?? '--/--',
            tmp:     r.temperature ?? '--',
            diag:    r.pathologie  ?? '--',
            history: []
        }));

        renderGrid(PATIENTS);
        updateCounters();
    } catch (e) {
        console.error('Impossible de charger les résidents depuis FastAPI :', e);
        document.getElementById('grid').innerHTML =
            '<p style="color:var(--danger); padding:20px;">Erreur de connexion à l\'API.</p>';
    }
}

function riskToStatus(score) {
    if (!score)    return 'stable';
    if (score >= 4) return 'critical';
    if (score >= 2) return 'urgent';
    return 'stable';
}

// --- 2. CONNEXION MQTT ---
function initMQTT() {
    mqttClient = new Paho.MQTT.Client(MQTT_HOST, MQTT_PORT, CLIENT_ID);

    mqttClient.onConnectionLost = () => {
        console.warn('MQTT déconnecté — reconnexion dans 5s');
        setTimeout(initMQTT, 5000);
    };

    mqttClient.onMessageArrived = (message) => {
        const topic = message.destinationName;
        let data;
        try { data = JSON.parse(message.payloadString); } catch { return; }

        if (topic.includes('/vitals')) {
            const resId = topic.split('/')[2]; 
            updatePatientVitals(resId, data);
        } else if (topic === 'ehpad/alerts') {
            handleIncomingAlert(data);
        }
    };

    mqttClient.connect({
        onSuccess: () => {
            console.log('✅ Connecté au broker MQTT');
            mqttClient.subscribe('ehpad/residents/+/vitals');
            mqttClient.subscribe('ehpad/alerts');
        },
        onFailure: () => setTimeout(initMQTT, 5000),
        useSSL: false
    });
}

// --- 3. MISE À JOUR CONSTANTES TEMPS RÉEL ---
function updatePatientVitals(resId, data) {
    const p = PATIENTS.find(pt => pt.id === resId);
    if (!p) return;

    p.hr  = data.heart_rate;
    p.ox  = data.spo2;
    p.bp  = `${data.systolic_bp}/${data.diastolic_bp}`;
    p.tmp = data.temperature;

    renderGrid(PATIENTS);
    updateCounters();
    updateMapStatus();
    if (currentPatientId === resId) refreshPanelUI(p);
}

// --- 4. ALERTES IA ---
function handleIncomingAlert(alert) {
    const p = PATIENTS.find(pt => pt.id === alert.res_id);
    if (!p) return;

    if (alert.level >= 4)      p.status = 'critical';
    else if (alert.level >= 2) p.status = 'urgent';

    const timeStr = new Date().toLocaleTimeString('fr-FR', { hour:'2-digit', minute:'2-digit' });
    let log = `⚠️ ${alert.text}`;
    if (alert.llm_report) log += `<br><small><i>Rapport IA : ${alert.llm_report}</i></small>`;
    p.history.push({ time: timeStr, text: log });

    if (alert.level >= 4) showToast(`ALERTE CRITIQUE — Chambre ${p.room}`);

    renderGrid(PATIENTS);
    updateCounters();
    updateMapStatus();
}

// --- 5. RENDU GRILLE ---
function renderGrid(pts) {
    const grid = document.getElementById('grid');
    if (!grid) return;

    if (pts.length === 0) {
        grid.innerHTML = '<p style="color:var(--muted); padding:20px;">Aucun résident trouvé.</p>';
        return;
    }

    grid.innerHTML = pts.map(p => `
        <div class="pcard ${p.status}" onclick='openPanelById("${p.id}")'>
            <div class="pcard-top">
                <div class="pcard-room">${p.room}</div>
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

// --- 6. COMPTEURS ---
function updateCounters() {
    document.getElementById('cnt-stable').textContent   = PATIENTS.filter(p => p.status === 'stable').length;
    document.getElementById('cnt-urgent').textContent   = PATIENTS.filter(p => p.status === 'urgent').length;
    document.getElementById('cnt-critical').textContent = PATIENTS.filter(p => p.status === 'critical').length;
    document.getElementById('cnt-dead').textContent     = PATIENTS.filter(p => p.status === 'dead').length;
    document.getElementById('cnt-total').textContent    = PATIENTS.length;
}

// --- 7. PANNEAU PATIENT ---
function openPanelById(id) {
    const p = PATIENTS.find(pt => pt.id === id);
    if (p) openPanel(p);
}

function openPanel(p) {
    currentPatientId = p.id;
    document.getElementById('p-room').textContent  = 'CHAMBRE ' + p.room;
    document.getElementById('p-room-info').textContent = p.room; 
    document.getElementById('p-name').textContent  = p.name;
    document.getElementById('p-doc').textContent   = document.getElementById('uid').value || 'Dr. —';

    const ptag = document.getElementById('p-tag');
    ptag.textContent = LABELS[p.status];
    ptag.className   = `pcard-tag ${TAG_CLS[p.status]}`;

    refreshPanelUI(p);

    const chat = document.getElementById('chat-history');
    chat.innerHTML = p.history.map(m => `
        <div style="background:var(--surface2); padding:8px; border-radius:4px; border-left:3px solid var(--accent); margin-bottom:5px;">
            <div style="font-size:9px; color:var(--accent); font-weight:bold;">${m.time}</div>
            <div style="font-size:12px; color:var(--text);">${m.text}</div>
        </div>
    `).join('') || '<div style="text-align:center; padding-top:50px; color:var(--muted);">Aucun historique</div>';

    // Reset du champ obligatoire
    const noteField = document.getElementById('note');
    noteField.value = '';
    noteField.style.borderColor = "var(--border)";

    document.getElementById('panel').classList.add('show');
    document.getElementById('mask').classList.add('show');
    chat.scrollTop = chat.scrollHeight;
}

function refreshPanelUI(p) {
    const col = COLORS[p.status];
    document.getElementById('v-hr').innerHTML  = `${p.hr}<span class="vb-unit">bpm</span>`;
    document.getElementById('v-ox').innerHTML  = `${p.ox}<span class="vb-unit">%</span>`;
    document.getElementById('v-bp').innerHTML  = `${p.bp}<span class="vb-unit">mmHg</span>`;
    document.getElementById('v-tmp').innerHTML = `${p.tmp}<span class="vb-unit">°C</span>`;
    document.querySelectorAll('.vb-val').forEach(el => el.style.color = col);
}

// --- 8. VALIDATION ET SÉCURITÉ ---
function saveIntervention() {
    const noteField = document.getElementById('note');
    const noteText = noteField.value.trim();

    if (noteText === "") {
        noteField.style.borderColor = "var(--danger)";
        alert("⚠️ ACTION REQUISE : Saisie obligatoire pour valider l'intervention.");
        return;
    }

    const docName = document.getElementById('uid').value || "Dr. Morel";
    const timeStr = new Date().toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'});
    
    // On enregistre dans l'historique local pour cette session
    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    if(p) p.history.push({ time: timeStr, text: `✅ Intervention (${docName}) : ${noteText}` });

    console.log("Validation intervention pour :", currentPatientId);

    const toast = document.getElementById('toast');
    toast.innerHTML = "✓ INTERVENTION ENREGISTRÉE";
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
        noteField.value = ""; // Vider permet de fermer
        closePanel(true); // Argument true pour forcer la fermeture après succès
    }, 1500);
}

function closePanel(force = false) {
    const noteField = document.getElementById('note');
    const noteText = noteField.value.trim();
    const panel = document.getElementById('panel');

    // Si on essaie de fermer sans note (et sans avoir cliqué sur VALIDER)
    if (!force && panel.classList.contains('show') && noteText === "") {
        noteField.style.borderColor = "var(--danger)";
        noteField.focus();
        alert("🔒 SÉCURITÉ : Vous devez noter votre intervention avant de quitter.");
        return;
    }

    panel.classList.remove('show');
    document.getElementById('mask').classList.remove('show');
}

// --- 9. CARTE ---
function updateMapStatus() {
    PATIENTS.forEach(p => {
        const el = document.getElementById(`room-${p.room}`); 
        if (!el) return;
        const rect = el.querySelector('rect');
        el.classList.remove('map-critical');
        if (p.status === 'critical') {
            el.classList.add('map-critical');
            rect.style.fill = 'rgba(230, 57, 70, 0.4)';
        } else if (p.status === 'urgent') {
            rect.style.fill = 'rgba(253, 126, 20, 0.4)';
        } else {
            rect.style.fill = 'rgba(0, 168, 120, 0.1)';
        }
    });
}

function selectRoom(room) {
    const p = PATIENTS.find(pt => pt.room === room);
    if (p) openPanel(p);
}

// --- 10. NAVIGATION ---
function setNav(btn, view) {
    document.querySelectorAll('.sb-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('view-grid').style.display = (view === 'grid') ? 'block' : 'none';
    document.getElementById('view-map').style.display  = (view === 'map')  ? 'block' : 'none';
    if (view === 'map') updateMapStatus();
}

// --- 11. RECHERCHE ---
function filterCards(value) {
    const q = value.toLowerCase().trim();
    if (!q) { renderGrid(PATIENTS); return; }
    const filtered = PATIENTS.filter(p =>
        p.room.includes(q) || p.name.toLowerCase().includes(q)
    );
    renderGrid(filtered);
}

// --- 12. UTILITAIRES ---
function addPatient() {
    alert('Fonctionnalité disponible en mode administrateur uniquement.');
}

function showToast(m) {
    const t = document.getElementById('toast');
    t.innerHTML = m;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 4000);
}

// --- DÉMARRAGE ---
function doLogin() {
    document.getElementById('login').style.display = 'none';
    document.getElementById('shell').classList.add('in');
    loadResidents().then(() => initMQTT());
}

setInterval(() => {
    // Correction de l'horloge pour éviter le plantage
    document.getElementById('clock').textContent = new Date().toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}, 1000);