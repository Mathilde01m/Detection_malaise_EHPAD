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
const COLORS  = { stable:'#00e5a0', urgent:'#ff9f0a', critical:'#ff3b30', dead:'#555' };

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
        updateMapStatus();
    } catch (e) {
        console.error('Impossible de charger les résidents depuis FastAPI :', e);
        document.getElementById('grid').innerHTML =
            '<p style="color:var(--danger); padding:20px;">Erreur de connexion à l\'API.</p>';
    }
}

function riskToStatus(score) {
    if (!score)     return 'stable';
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
        onFailure: (err) => {
            console.warn('MQTT échec connexion, retry dans 5s', err);
            setTimeout(initMQTT, 5000);
        },
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

    if (alert.level >= 4) showToast(`🚨 ALERTE CRITIQUE — Chambre ${p.room}`);

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
    document.getElementById('p-room').textContent      = 'CHAMBRE ' + p.room;
    document.getElementById('p-name').textContent      = p.name;
    document.getElementById('p-room-info').textContent = p.room;
    document.getElementById('p-doc').textContent       = document.getElementById('uid').value || 'Dr. —';

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

    const noteEl = document.getElementById('note');
    noteEl.value = '';
    // Entrée = valider (Shift+Entrée = saut de ligne normal)
    noteEl.onkeydown = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveIntervention();
        }
    };

    // Cacher le bandeau d'avertissement à l'ouverture
    document.getElementById('panel-warning').style.display = 'none';

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

// --- 8. VALIDATION INTERVENTION ---
function saveIntervention() {
    const note = document.getElementById('note').value.trim();
    if (!note) {
        // Faire clignoter le champ plutôt qu'une alerte popup
        const noteEl = document.getElementById('note');
        noteEl.style.borderColor = 'var(--danger)';
        noteEl.placeholder = '⚠️ Note obligatoire avant de valider...';
        noteEl.focus();
        setTimeout(() => {
            noteEl.style.borderColor = '';
            noteEl.placeholder = 'Saisir une observation... ↵ Entrée pour valider';
        }, 2000);
        return;
    }

    const staff = document.getElementById('uid').value || 'Soignant';
    const ack   = { res_id: currentPatientId, staff };
    const msg   = new Paho.MQTT.Message(JSON.stringify(ack));
    msg.destinationName = 'ehpad/alerts/ack';
    mqttClient.send(msg);

    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    if (p) {
        p.history.push({ time: new Date().toLocaleTimeString('fr-FR'), text: `✅ INTERVENTION : ${note}` });
        p.status = 'stable';
    }

    closePanel();
    renderGrid(PATIENTS);
    updateCounters();
    updateMapStatus();
    showToast('✓ INTERVENTION ENREGISTRÉE');
}

// --- 9. CARTE ---
function updateMapStatus() {
    PATIENTS.forEach(p => {
        const el = document.getElementById(`room-${p.room}`);
        if (!el) return;
        el.classList.remove('map-stable', 'map-urgent', 'map-critical');
        if (p.status === 'critical' || p.status === 'dead') {
            el.classList.add('map-critical');
        } else if (p.status === 'urgent') {
            el.classList.add('map-urgent');
        } else {
            el.classList.add('map-stable');
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

// Fermeture forcée (depuis saveIntervention après validation)
function closePanel() {
    currentPatientId = null;
    document.getElementById('panel').classList.remove('show');
    document.getElementById('mask').classList.remove('show');
    document.getElementById('panel-warning').style.display = 'none';
}

// Tentative de fermeture : bloquée si patient urgent/critique sans intervention
function tryClosePanel() {
    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    if (p && (p.status === 'urgent' || p.status === 'critical')) {
        // Bloquer et afficher le bandeau d'avertissement
        const warn = document.getElementById('panel-warning');
        warn.style.display = 'block';
        // Faire trembler le panneau pour attirer l'attention
        const panel = document.getElementById('panel');
        panel.style.animation = 'none';
        panel.classList.add('panel-shake');
        setTimeout(() => panel.classList.remove('panel-shake'), 500);
        // Mettre le focus sur la note
        document.getElementById('note').focus();
        return;
    }
    closePanel();
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
    document.getElementById('clock').textContent = new Date().toLocaleTimeString('fr-FR');
}, 1000);