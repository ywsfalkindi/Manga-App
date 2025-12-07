// ================================================
// FILE: static/app.js
// ================================================
const API_BASE = '/api';
let state = {
    currentSeries: null,
    currentChapter: null,
    chapters: [],
    pages: [],
    history: JSON.parse(localStorage.getItem('manga_history') || '{}'),
    settings: JSON.parse(localStorage.getItem('reader_settings') || '{"mode": "vertical"}')
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
        window.Telegram.WebApp.setHeaderColor('#0a0a0a');
    }
    loadSeries();
    applySettings();
    
    document.getElementById('search').addEventListener('input', (e) => {
        clearTimeout(window.searchTimer);
        window.searchTimer = setTimeout(() => loadSeries(e.target.value), 500);
    });
});

// --- Core Functions ---

async function loadSeries(query = "") {
    const grid = document.getElementById('series-grid');
    grid.innerHTML = Array(6).fill('<div class="manga-card skeleton" style="height:200px"></div>').join('');
    
    try {
        const res = await fetch(`${API_BASE}/series?q=${query}`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        const data = await res.json();
        
        if (data.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">لا توجد نتائج.</div>';
            return;
        }

        grid.innerHTML = data.map(s => `
            <div class="manga-card" onclick="openSeries('${s.id}', '${s.title}')">
                <img src="${s.cover_url}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x300?text=No+Img'">
                <div class="manga-title">${s.title}</div>
            </div>
        `).join('');

    } catch (e) { 
        grid.innerHTML = `<div style="text-align:center; grid-column:1/-1; color:#ff5555">خطأ في الاتصال: ${e.message}</div>`;
    }
}

async function openSeries(id, title) {
    state.currentSeries = { id, title };
    switchView('chapters-view');
    document.getElementById('series-title').innerText = title;
    document.getElementById('chapters-list').innerHTML = '<div class="skeleton" style="height:50px; margin-bottom:10px"></div>'.repeat(3);

    try {
        const res = await fetch(`${API_BASE}/chapters/${id}`);
        state.chapters = await res.json();
        
        const history = state.history[id] || {};
        
        document.getElementById('chapters-list').innerHTML = state.chapters.map(c => {
            const isRead = history.lastChapter === c.id;
            const statusIcon = isRead ? '<span style="color:var(--primary); font-size:0.8em"> (واصل القراءة)</span>' : '';
            
            return `
            <div class="btn" style="background:#222; margin-bottom:8px; display:flex; justify-content:space-between; text-align:right" 
                 onclick="loadChapter('${c.id}', ${c.chapter_number})">
                 <span>${c.title || `فصل ${c.chapter_number}`} ${statusIcon}</span>
                 <small style="color:#666">#${c.chapter_number}</small>
            </div>`;
        }).join('');
    } catch(e) {
        alert("فشل تحميل الفصول");
    }
}

async function loadChapter(chapterId, chapNum) {
    switchView('reader-view');
    const container = document.getElementById('reader-container');
    container.innerHTML = '<div style="padding:50px; text-align:center">جاري جلب الصفحات...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/pages/${chapterId}`);
        if (!res.ok) throw new Error("Chapter API Error");
        
        const data = await res.json();
        state.pages = data.pages;
        state.currentChapter = { ...data, id: chapterId, chapter_number: chapNum };

        renderPages();
    } catch (e) {
        container.innerHTML = `<div style="text-align:center; padding:20px">حدث خطأ <br> <button class="btn" onclick="loadChapter('${chapterId}')">إعادة المحاولة</button></div>`;
    }
}

function renderPages() {
    const container = document.getElementById('reader-container');
    container.className = state.settings.mode;
    
    // تحديد الصفحة المحفوظة سابقاً
    const hist = state.history[state.currentSeries.id];
    const savedPageIdx = (hist && hist.lastChapter === state.currentChapter.id) ? hist.lastPage : -1;

    // === تحسين 3: معالجة الصور المكسورة + الانتقال الذكي للصفحة ===
    container.innerHTML = state.pages.map((url, i) => {
        // إذا كانت هذه هي الصفحة المحفوظة، نضيف حدث onload للانتقال إليها فوراً
        const scrollAttr = (i === savedPageIdx) ? 'onload="this.scrollIntoView({block: \'start\'})"' : '';
        
        return `
        <div style="position:relative; width:100%; display:flex; justify-content:center;">
            <img src="${url}" 
                 loading="${i < 3 || i === savedPageIdx ? 'eager' : 'lazy'}" 
                 data-idx="${i}" 
                 class="manga-page"
                 ${scrollAttr}
                 onerror="this.onerror=null; this.src='https://via.placeholder.com/600x800?text=Error+Tap+Reload'; this.onclick=function(){location.reload()}"
            >
        </div>`;
    }).join('');

    // إضافة أزرار التنقل السفلية
    const navDiv = document.createElement('div');
    navDiv.className = 'chapter-nav';
    navDiv.innerHTML = `
        <button class="btn" onclick="navChapter('${state.currentChapter.prev_chapter}')" 
            ${!state.currentChapter.prev_chapter ? 'disabled style="opacity:0.3"' : ''}>السابق</button>
        <button class="btn" onclick="exitReader()">القائمة</button>
        <button class="btn" onclick="navChapter('${state.currentChapter.next_chapter}')"
            ${!state.currentChapter.next_chapter ? 'disabled style="opacity:0.3"' : ''}>التالي</button>
    `;
    container.appendChild(navDiv);

    setupObserver();
    // احتياطي في حال فشل onload
    if (savedPageIdx > 0) setTimeout(restoreProgress, 500);
}

function setupObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const idx = parseInt(entry.target.dataset.idx);
                document.getElementById('page-indicator').innerText = `${idx + 1} / ${state.pages.length}`;
                saveProgress(state.currentSeries.id, state.currentChapter.id, idx);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.manga-page').forEach(img => observer.observe(img));
}

function restoreProgress() {
    const hist = state.history[state.currentSeries.id];
    if (hist && hist.lastChapter === state.currentChapter.id && hist.lastPage > 0) {
        const target = document.querySelector(`img[data-idx="${hist.lastPage}"]`);
        if (target) {
            target.scrollIntoView({ behavior: 'auto', block: 'start' });
        }
    }
}

function navChapter(targetId) {
    if (targetId && targetId !== 'null') {
        loadChapter(targetId);
    }
}

// --- Helper Functions ---

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');
    document.getElementById('header').style.display = viewId === 'reader-view' ? 'none' : 'block';
    window.scrollTo(0, 0);
}

function goBack() { switchView('home-view'); }
function exitReader() { switchView('chapters-view'); }

function saveProgress(seriesId, chapterId, pageIdx) {
    state.history[seriesId] = { 
        lastChapter: chapterId, 
        lastPage: pageIdx, 
        timestamp: Date.now() 
    };
    localStorage.setItem('manga_history', JSON.stringify(state.history));
}

function toggleSettings() {
    document.getElementById('settings-modal').classList.toggle('hidden');
}

function changeMode(mode) {
    state.settings.mode = mode;
    localStorage.setItem('reader_settings', JSON.stringify(state.settings));
    renderPages();
}

function applySettings() {
    const radios = document.getElementsByName('mode');
    radios.forEach(r => { if(r.value === state.settings.mode) r.checked = true; });
}