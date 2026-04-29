let isCareValidated = false;

document.addEventListener('DOMContentLoaded', () => {
    // Login
    document.getElementById('login-form').addEventListener('submit', (e) => {
        e.preventDefault();
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        renderSector('A');
    });

    // Navigation Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelector('.tab.active').classList.remove('active');
            tab.classList.add('active');
            const sector = tab.dataset.sector;
            if(sector === 'PLAN') {
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

function renderSector(id) {
    const container = document.getElementById('patient-container');
    container.innerHTML = '';
    for(let i=1; i<=6; i++) {
        const risk = Math.floor(Math.random() * 100);
        const bpm = 65 + Math.floor(Math.random() * 30);
        const spo2 = 94 + Math.floor(Math.random() * 5);
        const tension = (12 + Math.floor(Math.random() * 3)) + "/" + (7 + Math.floor(Math.random() * 2));
        const temp = (36.5 + (Math.random() * 1)).toFixed(1);
        
        const card = document.createElement('div');
        card.className = `card ${risk > 80 ? 'status-high' : ''}`;
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px">
                <strong style="font-size:18px">Chambre ${id}-${100+i}</strong>
                <span style="background:${risk > 80 ? '#FEE2E2' : '#ECFDF5'}; color:${risk > 80 ? 'var(--danger)' : '#059669'}; padding:5px 10px; border-radius:10px; font-size:12px; font-weight:800">${risk}% Risk IA</span>
            </div>
            <div class="card-vitals" style="display:grid; grid-template-columns: 1fr 1fr; gap:10px">
                <div class="vital-box" style="padding:10px"><strong>${bpm}</strong><small>BPM</small></div>
                <div class="vital-box" style="padding:10px"><strong>${spo2}%</strong><small>SpO2</small></div>
            </div>
        `;
        card.onclick = () => openDrawer(`Chambre ${id}-${100+i}`, {risk, bpm, spo2, tension, temp});
        container.appendChild(card);
    }
}

function openDrawer(name, data) {
    isCareValidated = false;
    document.getElementById('side-drawer').classList.remove('hidden');
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('drawer-name').innerText = name;
    
    // Reset validation UI
    const banner = document.getElementById('care-banner');
    banner.style.background = "#FEF2F2"; banner.style.color = "#991B1B"; banner.innerText = "⚠️ INTERVENTION NON VALIDÉE";
    document.getElementById('soignant-note').value = "";
    document.getElementById('soignant-note').disabled = false;

    document.getElementById('drawer-vitals').innerHTML = `
        <div class="vital-box" style="grid-column: span 2; padding:30px; border: 2px solid var(--primary); background: #EEF2FF">
            <small style="color:var(--primary)">Score Prédictif IA</small><strong>${data.risk}%</strong>
        </div>
        <div class="vital-box"><strong>${data.bpm}</strong><small>BPM (Pouls)</small></div>
        <div class="vital-box"><strong>${data.spo2}%</strong><small>SpO2 (Sat.)</small></div>
        <div class="vital-box"><strong>${data.tension}</strong><small>Tension (mmHg)</small></div>
        <div class="vital-box"><strong>${data.temp}°C</strong><small>Température</small></div>
    `;
    switchDrawerTab('vitals');
}

function validateCare() {
    const note = document.getElementById('soignant-note').value;
    if(note.length < 10) {
        alert("🔒 Erreur : Rapport de soin trop court (10 car. min).");
        return;
    }
    isCareValidated = true;
    const banner = document.getElementById('care-banner');
    banner.innerText = "✅ INTERVENTION VALIDÉE & ARCHIVÉE";
    banner.style.background = "#ECFDF5";
    banner.style.color = "#065F46";
    document.getElementById('soignant-note').disabled = true;
}

// ... garder les fonctions closeDrawer, switchDrawerTab, updateHeatmap identiques ...