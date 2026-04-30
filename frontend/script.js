// --- CONFIGURATION ---
const MQTT_HOST = window.location.hostname;
const MQTT_PORT = 9001;
const CLIENT_ID = "SanteOS_Front_" + Math.random().toString(16).substr(2, 5);

let mqttClient;
let currentPatientId  = null;
let familyResidentId  = null;

let PATIENTS = [];

const LABELS  = { stable:'STABLE', urgent:'URGENT', critical:'CRITIQUE', dead:'ARRÊT' };
const TAG_CLS = { stable:'tag-stable', urgent:'tag-urgent', critical:'tag-critical', dead:'tag-dead' };
const PV_CLS  = { stable:'ok', urgent:'warn', critical:'crit', dead:'gone' };
const COLORS  = { stable:'#00e5a0', urgent:'#ff9f0a', critical:'#ff3b30', dead:'#555' };

// --- 1. AUTHENTIFICATION ---
async function doLogin() {
    const email    = document.getElementById('uid').value.trim();
    const password = document.getElementById('pin').value.trim();
    const errEl    = document.getElementById('login-error');
    errEl.style.display = 'none';

    if (!email || !password) {
        errEl.textContent = 'Veuillez remplir tous les champs.';
        errEl.style.display = 'block';
        return;
    }

    try {
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!resp.ok) {
            errEl.textContent = 'Email ou mot de passe incorrect.';
            errEl.style.display = 'block';
            return;
        }

        const data = await resp.json();
        localStorage.setItem('ehpad_token', data.token);
        localStorage.setItem('ehpad_role',  data.role);
        localStorage.setItem('ehpad_name',  data.name);

        document.getElementById('login').style.display = 'none';

        if (data.role === 'family') {
            // Vue famille plein écran, totalement indépendante du shell staff
            document.getElementById('view-family').style.display = 'flex';
            loadFamilyView(data.token);
        } else {
            document.getElementById('shell').classList.add('in');
            const initials = data.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
            document.getElementById('user-init').textContent = initials;
            loadResidents().then(() => initMQTT());
        }

    } catch (e) {
        errEl.textContent = 'Erreur de connexion au serveur.';
        errEl.style.display = 'block';
    }
}

// --- 2. VUE FAMILLE ---
const REL_FR = {
    daughter:'Fille', son:'Fils', granddaughter:'Petite-fille',
    grandson:'Petit-fils', wife:'Épouse', husband:'Époux',
    sister:'Sœur', brother:'Frère', niece:'Nièce', nephew:'Neveu',
    friend:'Ami(e)', other:'Proche'
};

async function loadFamilyView(token) {
    try {
        const resp = await fetch('/api/my-resident', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error();
        const r = await resp.json();

        familyResidentId = r.id;

        // Header
        const prenom = (localStorage.getItem('ehpad_name') || '').split(' ')[0];
        const relFr  = REL_FR[r.relationship] || r.relationship || 'Proche';
        document.getElementById('fam-greeting').textContent = `Bonjour, ${prenom}`;
        document.getElementById('fam-relation').textContent  = `${relFr} — Chambre ${r.chambre}`;

        updateFamilyVitals(r);
        initMQTTFamily(r.id, r.chambre);

    } catch (e) {
        document.getElementById('view-family').innerHTML =
            '<p style="color:var(--danger);padding:60px;text-align:center;font-family:var(--mono);">Impossible de charger les données de votre proche.</p>';
    }
}

function updateFamilyVitals(r) {
    const status = riskToStatus(r.risk_score ?? 0);

    document.getElementById('fam-room').textContent = r.chambre ?? '—';
    document.getElementById('fam-hr').innerHTML  = `${r.heart_rate ?? '—'}<span class="fam-unit">bpm</span>`;
    document.getElementById('fam-ox').innerHTML  = `${r.spo2 ?? '—'}<span class="fam-unit">%</span>`;
    document.getElementById('fam-tmp').innerHTML = `${r.temperature ?? '—'}<span class="fam-unit">°C</span>`;

    const stateEl = document.getElementById('fam-status');
    stateEl.textContent = LABELS[status];
    stateEl.style.color = COLORS[status];

    const tag = document.getElementById('fam-tag');
    tag.textContent = LABELS[status];
    tag.className   = `fam-status-badge ${TAG_CLS[status]}`;

    const bar = document.getElementById('fam-status-bar');
    bar.className = `fam-status-bar bar-${status}`;

    const now = new Date().toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    document.getElementById('fam-last-update').textContent = `Dernière mise à jour : ${now}`;
}

function initMQTTFamily(resId, chambre) {
    mqttClient = new Paho.MQTT.Client(MQTT_HOST, MQTT_PORT, CLIENT_ID);
    mqttClient.onConnectionLost = () => setTimeout(() => initMQTTFamily(resId, chambre), 5000);
    mqttClient.onMessageArrived = (message) => {
        const topic = message.destinationName;
        let data;
        try { data = JSON.parse(message.payloadString); } catch { return; }
        if (topic.includes(`/residents/${resId}/vitals`)) {
            updateFamilyVitals({
                chambre:     chambre,
                heart_rate:  data.heart_rate,
                spo2:        data.spo2,
                temperature: data.temperature,
                risk_score:  data.risk_score ?? 0
            });
        }
    };
    mqttClient.connect({
        onSuccess: () => mqttClient.subscribe(`ehpad/residents/${resId}/vitals`),
        onFailure: () => setTimeout(() => initMQTTFamily(resId, chambre), 5000),
        useSSL: false
    });
}

function doLogout() {
    localStorage.removeItem('ehpad_token');
    localStorage.removeItem('ehpad_role');
    localStorage.removeItem('ehpad_name');
    if (mqttClient) { try { mqttClient.disconnect(); } catch(e){} }
    document.getElementById('view-family').style.display = 'none';
    document.getElementById('shell').classList.remove('in');
    document.getElementById('login').style.display = 'flex';
    document.getElementById('uid').value = '';
    document.getElementById('pin').value = '';
}

// --- 3. CHARGEMENT RÉSIDENTS (SOIGNANTS) ---
async function loadResidents() {
    const token = localStorage.getItem('ehpad_token');
    try {
        const resp = await fetch('/api/residents', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        PATIENTS = data.map(r => ({
            id:       r.id,
            room:     String(r.chambre),
            name:     r.nom || `Résident ${r.id}`,
            age:      '--',
            status:   riskToStatus(r.risk_score),
            hr:       r.heart_rate  ?? 0,
            ox:       r.spo2        ?? 0,
            bp:       r.tension     ?? '--/--',
            tmp:      r.temperature ?? '--',
            diag:     r.pathologie  ?? '--',
            history:  [],
            aiLevel:  0,
            aiText:   '',
            aiReport: ''
        }));

        renderGrid(PATIENTS);
        updateCounters();
        updateMapStatus();
    } catch (e) {
        console.error('Impossible de charger les résidents :', e);
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

// --- 4. CONNEXION MQTT (SOIGNANTS) ---
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

// --- 5. MISE À JOUR CONSTANTES ---
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

// --- 6. ALERTES IA ---
function handleIncomingAlert(alert) {
    const p = PATIENTS.find(pt => pt.id === alert.res_id);
    if (!p) return;

    if (alert.level >= 4)      p.status = 'critical';
    else if (alert.level >= 2) p.status = 'urgent';

<<<<<<< HEAD
    // Stocker la prédiction IA
=======
>>>>>>> front2
    p.aiLevel = alert.level;
    p.aiText  = alert.text;
    if (alert.llm_report) p.aiReport = alert.llm_report;

    const timeStr = new Date().toLocaleTimeString('fr-FR', { hour:'2-digit', minute:'2-digit' });
    let log = `⚠️ ${alert.text}`;
    if (alert.llm_report) log += `<br><small><i>Rapport IA : ${alert.llm_report}</i></small>`;
    p.history.push({ time: timeStr, text: log });

    if (alert.level >= 4) showToast(`🚨 ALERTE CRITIQUE — Chambre ${p.room}`);

    renderGrid(PATIENTS);
    updateCounters();
    updateMapStatus();
    if (currentPatientId === p.id) refreshAIPanel(p);
}

// --- 7. RENDU GRILLE ---
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
            ${p.aiLevel > 0 ? `
            <div class="pcard-ai ai-lvl-${p.aiLevel}">
                <span class="ai-badge">IA · NIV.${p.aiLevel}</span>
                <span class="ai-card-text">${p.aiText}</span>
            </div>` : ''}
        </div>
    `).join('');
}

// --- 8. COMPTEURS ---
function updateCounters() {
    document.getElementById('cnt-stable').textContent   = PATIENTS.filter(p => p.status === 'stable').length;
    document.getElementById('cnt-urgent').textContent   = PATIENTS.filter(p => p.status === 'urgent').length;
    document.getElementById('cnt-critical').textContent = PATIENTS.filter(p => p.status === 'critical').length;
    document.getElementById('cnt-dead').textContent     = PATIENTS.filter(p => p.status === 'dead').length;
    document.getElementById('cnt-total').textContent    = PATIENTS.length;
}

// --- 9. PANNEAU PATIENT ---
function openPanelById(id) {
    const p = PATIENTS.find(pt => pt.id === id);
    if (p) openPanel(p);
}

function openPanel(p) {
    currentPatientId = p.id;
    document.getElementById('p-room').textContent      = 'CHAMBRE ' + p.room;
    document.getElementById('p-name').textContent      = p.name;
    document.getElementById('p-room-info').textContent = p.room;
    document.getElementById('p-doc').textContent       = localStorage.getItem('ehpad_name') || 'Dr. —';

    const ptag = document.getElementById('p-tag');
    ptag.textContent = LABELS[p.status];
    ptag.className   = `pcard-tag ${TAG_CLS[p.status]}`;

    refreshPanelUI(p);
    refreshAIPanel(p);

    const chat = document.getElementById('chat-history');
    chat.innerHTML = p.history.map(m => `
        <div style="background:var(--surface2); padding:8px; border-radius:4px; border-left:3px solid var(--accent); margin-bottom:5px;">
            <div style="font-size:9px; color:var(--accent); font-weight:bold;">${m.time}</div>
            <div style="font-size:12px; color:var(--text);">${m.text}</div>
        </div>
    `).join('') || '<div style="text-align:center; padding-top:50px; color:var(--muted);">Aucun historique</div>';

    const noteEl = document.getElementById('note');
    noteEl.value = '';
    noteEl.onkeydown = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            saveIntervention();
        }
    };

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

function refreshAIPanel(p) {
    const lvlEl    = document.getElementById('ai-level');
    const textEl   = document.getElementById('ai-text');
    const reportEl = document.getElementById('ai-report');
    if (!lvlEl) return;

    if (p.aiLevel > 0) {
        lvlEl.textContent  = `NIVEAU ${p.aiLevel} / 5`;
        lvlEl.className    = `ai-level-val ai-lvl-${p.aiLevel}`;
        textEl.textContent = p.aiText || '—';
        reportEl.innerHTML = p.aiReport
            ? `<i>${p.aiReport}</i>`
            : '<span style="color:var(--muted)">En attente (seuil non atteint pour rapport Mistral)</span>';
    } else {
        lvlEl.textContent  = 'AUCUNE ALERTE';
        lvlEl.className    = 'ai-level-val';
        textEl.textContent = '—';
        reportEl.innerHTML = '<span style="color:var(--muted)">Surveillance normale</span>';
    }
}

<<<<<<< HEAD
// --- 8. VALIDATION INTERVENTION ---
=======
// --- 10. VALIDATION INTERVENTION ---
>>>>>>> front2
function saveIntervention() {
    const note = document.getElementById('note').value.trim();
    if (!note) {
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

    const staff = localStorage.getItem('ehpad_name') || 'Soignant';
    const ack   = { res_id: currentPatientId, staff };
    const msg   = new Paho.MQTT.Message(JSON.stringify(ack));
    msg.destinationName = 'ehpad/alerts/ack';
    mqttClient.send(msg);

    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    if (p) {
        p.history.push({ time: new Date().toLocaleTimeString('fr-FR'), text: `✅ INTERVENTION : ${note}` });
        p.status   = 'stable';
        p.aiLevel  = 0;
        p.aiText   = '';
        p.aiReport = '';
    }

    closePanel();
    renderGrid(PATIENTS);
    updateCounters();
    updateMapStatus();
    showToast('✓ INTERVENTION ENREGISTRÉE');
}

// --- 11. CARTE ---
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

// --- 12. NAVIGATION ---
function setNav(btn, view) {
    document.querySelectorAll('.sb-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('view-grid').style.display = (view === 'grid') ? 'block' : 'none';
    document.getElementById('view-map').style.display  = (view === 'map')  ? 'block' : 'none';
    if (view === 'map') updateMapStatus();
}

// --- 13. RECHERCHE ---
function filterCards(value) {
    const q = value.toLowerCase().trim();
    if (!q) { renderGrid(PATIENTS); return; }
    const filtered = PATIENTS.filter(p =>
        p.room.includes(q) || p.name.toLowerCase().includes(q)
    );
    renderGrid(filtered);
}

// --- 14. UTILITAIRES ---
function addPatient() {
    alert('Fonctionnalité disponible en mode administrateur uniquement.');
}

function closePanel() {
    currentPatientId = null;
    document.getElementById('panel').classList.remove('show');
    document.getElementById('mask').classList.remove('show');
    document.getElementById('panel-warning').style.display = 'none';
}

function tryClosePanel() {
    const p = PATIENTS.find(pt => pt.id === currentPatientId);
    if (p && (p.status === 'urgent' || p.status === 'critical')) {
        const warn = document.getElementById('panel-warning');
        warn.style.display = 'block';
        const panel = document.getElementById('panel');
        panel.classList.add('panel-shake');
        setTimeout(() => panel.classList.remove('panel-shake'), 500);
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

setInterval(() => {
    document.getElementById('clock').textContent = new Date().toLocaleTimeString('fr-FR');
}, 1000);