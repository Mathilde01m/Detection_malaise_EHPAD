const PATIENTS = [
  { id:'101', name:'Dubois Martin',  age:'67 ans', status:'stable',   hr:72,  ox:98, bp:'118/76', tmp:'37.1', admit:'22 avr', doc:'Dr. Morel',  diag:'Post-op cardiac', history: [] },
  { id:'102', name:'Lefevre Sophie', age:'54 ans', status:'critical', hr:138, ox:89, bp:'90/60',  tmp:'39.4', admit:'29 avr', doc:'Dr. Renard', diag:'Choc septique', history: [] },
  { id:'103', name:'Bernard Jean',   age:'78 ans', status:'urgent',   hr:101, ox:94, bp:'158/95', tmp:'38.7', admit:'28 avr', doc:'Dr. Morel',  diag:'Pneumonie', history: [] },
  { id:'104', name:'Moreau Claire',  age:'45 ans', status:'stable',   hr:68,  ox:99, bp:'122/80', tmp:'36.8', admit:'25 avr', doc:'Dr. Petit',  diag:'Fracture hanche', history: [] },
  { id:'105', name:'Petit Robert',   age:'82 ans', status:'dead',     hr:0,   ox:0,  bp:'—',      tmp:'—',    admit:'27 avr', doc:'Dr. Renard', diag:'Insuffisance cardiaque', history: [] },
  { id:'106', name:'Simon Anne',     age:'61 ans', status:'stable',   hr:74,  ox:97, bp:'130/84', tmp:'37.0', admit:'24 avr', doc:'Dr. Morel',  diag:'Diabète type 2', history: [] },
  { id:'107', name:'Laurent Paul',   age:'38 ans', status:'urgent',   hr:115, ox:92, bp:'145/90', tmp:'38.2', admit:'29 avr', doc:'Dr. Petit',  diag:'AVC ischémique', history: [] },
  { id:'108', name:'Garcia Elena',   age:'29 ans', status:'stable',   hr:65,  ox:99, bp:'110/70', tmp:'37.2', admit:'28 avr', doc:'Dr. Morel',  diag:'Appendicite post-op', history: [] }
];

const LABELS  = { stable:'STABLE', urgent:'URGENT', critical:'CRITIQUE', dead:'ARRÊT' };
const TAG_CLS = { stable:'tag-stable', urgent:'tag-urgent', critical:'tag-critical', dead:'tag-dead' };
const PV_CLS  = { stable:'ok', urgent:'warn', critical:'crit', dead:'gone' };
const COLORS  = { stable:'var(--accent)', urgent:'var(--warn)', critical:'var(--danger)', dead:'var(--dead)' };

let currentPatientId = null;

// --- INITIALISATION & LOGIN ---
function doLogin() {
  const uid = document.getElementById('uid').value;
  const init = uid.split(' ').map(w=>w[0]||'').join('').toUpperCase().slice(0,2);
  document.getElementById('user-init').textContent = init || 'DR';
  document.getElementById('login').classList.add('out');
  setTimeout(()=>{
    document.getElementById('login').style.display = 'none';
    document.getElementById('shell').classList.add('in');
  }, 400);
  renderGrid(PATIENTS);
  updateCounts(PATIENTS);
  // La carte est mise à jour dès la connexion
  updateMapStatus();
}

// --- NAVIGATION ---
function setNav(btn, view) {
  document.querySelectorAll('.sb-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  
  // Basculement des vues
  document.getElementById('view-grid').style.display = (view === 'grid') ? 'block' : 'none';
  document.getElementById('view-map').style.display = (view === 'map') ? 'block' : 'none';
  
  const titles = { grid:'Patients', map:'Plan Ehpad', alerts:'Alertes actives', stats:'Statistiques' };
  document.getElementById('view-title').textContent = titles[view] || view;
  
  // Mise à jour de la carte quand on l'affiche
  if(view === 'map') updateMapStatus();
}

// --- LOGIQUE PATIENTS & GRILLE ---
function renderGrid(pts) {
  document.getElementById('grid').innerHTML = pts.map(p => {
    const vc = PV_CLS[p.status];
    return `<div class="pcard ${p.status}" onclick='openPanel(${JSON.stringify(p)})'>
      <div class="pcard-top">
        <div class="pcard-room">${p.id}</div>
        <span class="pcard-tag ${TAG_CLS[p.status]}">${LABELS[p.status]}</span>
      </div>
      <div class="pcard-name">${p.name}</div>
      <div class="pcard-info">${p.age} · ${p.diag}</div>
      <div class="pcard-vitals">
        <div class="pv"><div class="pv-label">HR</div><div class="pv-val ${vc}">${p.hr}</div></div>
        <div class="pv"><div class="pv-label">SpO₂</div><div class="pv-val ${vc}">${p.ox}%</div></div>
        <div class="pv"><div class="pv-label">PA</div><div class="pv-val ${vc}">${p.bp}</div></div>
      </div>
    </div>`;
  }).join('');
}

function updateCounts(pts) {
  ['stable','urgent','critical','dead'].forEach(s =>
    document.getElementById('cnt-'+s).textContent = pts.filter(p=>p.status===s).length
  );
  document.getElementById('cnt-total').textContent = pts.length;
}

function filterCards(q) {
  const f = q.toLowerCase();
  const pts = PATIENTS.filter(p => p.id.includes(f) || p.name.toLowerCase().includes(f) || p.diag.toLowerCase().includes(f));
  renderGrid(pts);
  updateCounts(pts);
}

// --- LOGIQUE PLAN (MAP) ---
// MODIFICATION ICI : Coloration selon le degré d'urgence
function updateMapStatus() {
  PATIENTS.forEach(p => {
    const roomElement = document.getElementById(`room-${p.id}`);
    if (roomElement) {
      // Nettoyage des états précédents
      roomElement.classList.remove('map-critical');
      const rect = roomElement.querySelector('rect');
      
      // Application de la couleur selon le statut (degré d'urgence)
      if (p.status === 'critical') {
        // Rouge + Animation (géré par CSS .map-critical)
        roomElement.classList.add('map-critical');
        rect.style.fill = ''; // On laisse le CSS gérer
      } else if (p.status === 'urgent') {
        // Orange
        rect.style.fill = 'rgba(255, 159, 10, 0.5)'; // Orange transparent
        rect.style.stroke = 'var(--warn)';
      } else if (p.status === 'dead') {
        // Gris
        rect.style.fill = 'rgba(85, 85, 85, 0.5)';
        rect.style.stroke = 'var(--dead)';
      } else {
        // Stable (Vert)
        rect.style.fill = 'rgba(0, 229, 160, 0.2)'; // Vert très transparent
        rect.style.stroke = 'var(--accent)';
      }
    }
  });
}

function selectRoom(roomId) {
  const patient = PATIENTS.find(p => p.id === roomId);
  if (patient) openPanel(patient);
}

// --- LOGIQUE PANEL & CHAT ---
function openPanel(p) {
  currentPatientId = p.id;
  const col = COLORS[p.status];
  
  document.getElementById('p-room').textContent = 'CHAMBRE ' + p.id;
  document.getElementById('p-name').textContent = p.name;
  document.getElementById('p-tag').textContent = LABELS[p.status];
  document.getElementById('p-tag').className = 'pcard-tag ' + TAG_CLS[p.status];
  
  ['v-hr','v-ox','v-bp','v-tmp'].forEach(id => document.getElementById(id).style.color = col);
  
  document.getElementById('v-hr').innerHTML  = p.hr  + '<span class="vb-unit">bpm</span>';
  document.getElementById('v-ox').innerHTML  = p.ox  + '<span class="vb-unit">%</span>';
  document.getElementById('v-bp').innerHTML  = p.bp  + '<span class="vb-unit">mmHg</span>';
  document.getElementById('v-tmp').innerHTML = p.tmp + '<span class="vb-unit">°C</span>';
  
  document.getElementById('p-age').textContent   = p.age;
  document.getElementById('p-admit').textContent = p.admit;
  document.getElementById('p-doc').textContent   = p.doc;
  document.getElementById('p-diag').textContent  = p.diag;

  // Affichage de l'historique
  const patientData = PATIENTS.find(pt => pt.id === p.id);
  const chatHistory = document.getElementById('chat-history');
  chatHistory.innerHTML = '';
  
  if (patientData.history.length === 0) {
    chatHistory.innerHTML = `<div style="color: var(--muted); font-size: 11px; text-align: center; margin-top: 70px; font-style:italic;">Aucune observation pour le moment</div>`;
  } else {
    patientData.history.forEach(msg => {
      chatHistory.innerHTML += `
        <div style="background: var(--surface2); border: 1px solid var(--border); padding: 8px; border-radius: 4px; border-left: 3px solid var(--accent);">
          <div style="font-family: var(--mono); font-size: 9px; color: var(--accent); margin-bottom: 4px; font-weight:bold;">[${msg.time}]</div>
          <div style="font-size: 12px; color: var(--text); line-height: 1.4;">${msg.text}</div>
        </div>
      `;
    });
    setTimeout(() => { chatHistory.scrollTop = chatHistory.scrollHeight; }, 100);
  }

  document.getElementById('note').value = '';
  document.getElementById('panel').classList.add('show');
  document.getElementById('mask').classList.add('show');
}

function closePanel() {
  document.getElementById('panel').classList.remove('show');
  document.getElementById('mask').classList.remove('show');
  currentPatientId = null;
}

function saveIntervention() {
  const noteContent = document.getElementById('note').value.trim();

  // VALIDATION OBLIGATOIRE
  if (noteContent === "") {
    alert("⚠ SAISIE OBLIGATOIRE : Vous devez rédiger une observation pour clôturer l'intervention.");
    document.getElementById('note').focus();
    return;
  }

  const now = new Date();
  const timeStr = now.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit'}) + ' ' + 
                  now.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});

  const patientIndex = PATIENTS.findIndex(pt => pt.id === currentPatientId);
  if (patientIndex !== -1) {
    // Ajout à l'historique
    PATIENTS[patientIndex].history.push({
      time: timeStr,
      text: noteContent
    });
  }

  closePanel();
  // Mise à jour de la carte après enregistrement (si le statut a changé)
  updateMapStatus(); 
  const t = document.getElementById('toast');
  t.innerHTML = `✓ OBSERVATION ENREGISTRÉE À ${now.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'})}`;
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 2500);
}

// --- UTILITAIRES ---
function addPatient() {
  alert("Accès restreint : Administration requise pour admission.");
}

setInterval(()=>{
  const d = new Date();
  document.getElementById('clock').textContent =
    String(d.getHours()).padStart(2,'0') + ':' +
    String(d.getMinutes()).padStart(2,'0') + ':' +
    String(d.getSeconds()).padStart(2,'0');
}, 1000);

document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('login').style.display !== 'none') doLogin();
});