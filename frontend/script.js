document.getElementById('login-form').addEventListener('submit', (e) => {
    e.preventDefault();
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('dashboard').classList.remove('hidden');
    selectSector('A');
});

const states = [
    { label: 'Stable', class: 'state-stable', bg: 'bg-stable' },
    { label: 'Urgent', class: 'state-urgent', bg: 'bg-urgent' },
    { label: 'Critique', class: 'state-critical', bg: 'bg-critical' },
    { label: 'Décès', class: 'state-dead', bg: 'bg-dead' }
];

function selectSector(id) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id === 'A' ? 'btn-a' : 'btn-b').classList.add('active');
    document.getElementById('plan-container').classList.add('hidden');
    document.getElementById('patient-container').classList.remove('hidden');
    
    const container = document.getElementById('patient-container');
    container.innerHTML = '';
    
    for (let i = 1; i <= 6; i++) {
        // Aléatoire pour la démo, mais en prod ce serait lié à une base de données
        const randomState = states[Math.floor(Math.random() * states.length)];
        const name = `CHAMBRE ${id}-${100 + i}`;
        
        const card = document.createElement('div');
        card.className = `card ${randomState.class}`;
        card.innerHTML = `
            <strong>${name}</strong><br>
            <span class="status-badge ${randomState.bg}">${randomState.label}</span>
        `;
        card.onclick = () => openDrawer(name, randomState);
        container.appendChild(card);
    }
}

function openDrawer(name, state) {
    document.getElementById('drawer-name').innerText = name;
    
    // Ajustement des constantes selon l'état
    let hr = Math.floor(Math.random() * (90 - 60) + 60);
    let ox = Math.floor(Math.random() * (100 - 96) + 96);
    
    if(state.label === 'Critique') { hr = 142; ox = 88; }
    if(state.label === 'Décès') { hr = 0; ox = 0; }

    document.getElementById('drawer-vitals').innerHTML = `
        <div class="vital-box"><strong>${hr}</strong><small>BPM</small></div>
        <div class="vital-box"><strong>${ox}%</strong><small>SPO2</small></div>
    `;
    
    document.getElementById('side-drawer').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
}

function closeDrawer() {
    document.getElementById('side-drawer').classList.add('hidden');
    document.getElementById('overlay').classList.add('hidden');
}

function showPlan() {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById('btn-plan').classList.add('active');
    document.getElementById('patient-container').classList.add('hidden');
    document.getElementById('plan-container').classList.remove('hidden');
}

function validateCare() {
    alert("Intervention enregistrée.");
    closeDrawer();
}