const API_BASE = '/api';
let state = {
    currentSeries: null,
    currentChapter: null,
    chapters: [],
    pages: [],
    history: JSON.parse(localStorage.getItem('manga_history') || '{}'),
    settings: JSON.parse(localStorage.getItem('reader_settings') || '{"mode": "vertical"}')
};

// Init
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
    // عرض التحميل
    grid.innerHTML = Array(6).fill('<div class="manga-card skeleton" style="height:200px"></div>').join('');
    
    try {
        const res = await fetch(`${API_BASE}/series?q=${query}`);
        
        // التحقق من أن السيرفر رد بنجاح
        if (!res.ok) {
            throw new Error(`Server Error: ${res.status}`);
        }

        const data = await res.json();
        
        // إذا لم توجد نتائج
        if (data.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">لا توجد مانجا مضافة حالياً.</div>';
            return;
        }

        grid.innerHTML = data.map(s => `
            <div class="manga-card" onclick="openSeries('${s.id}', '${s.title}')">
                <img src="${s.cover_url}" loading="lazy" onerror="this.src='https://via.placeholder.com/200x300?text=No+Image'">
                <div class="manga-title">${s.title}</div>
            </div>
        `).join('');

    } catch (e) { 
        console.error(e);
        // عرض الخطأ للمستخدم بدلاً من التحميل الأبدي
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: #ff5555; padding: 20px; border: 1px solid #ff5555; border-radius: 8px;">
                <h3>حدث خطأ في الاتصال 🔴</h3>
                <p>${e.message}</p>
                <button class="btn" onclick="location.reload()" style="background:#333; color:white; margin-top:10px">إعادة المحاولة</button>
            </div>
        `;
    }
}

async function openSeries(id, title) {
    state.currentSeries = { id, title };
    switchView('chapters-view');
    document.getElementById('series-title').innerText = title;
    document.getElementById('chapters-list').innerHTML = '<div class="skeleton" style="height:50px; margin-bottom:10px"></div>'.repeat(5);

    const res = await fetch(`${API_BASE}/chapters/${id}`);
    state.chapters = await res.json();
    
    const history = state.history[id] || {};
    
    document.getElementById('chapters-list').innerHTML = state.chapters.map(c => {
        const isRead = history.lastChapter === c.id ? 'style="color:var(--primary)"' : '';
        return `
        <div class="btn" style="background:#222; margin-bottom:8px; display:flex; justify-content:space-between; text-align:right" 
             onclick="loadChapter('${c.id}')" ${isRead}>
             <span>${c.title || 'فصل ' + c.chapter_number}</span>
             <small>#${c.chapter_number}</small>
        </div>`;
    }).join('');
}

async function loadChapter(chapterId) {
    switchView('reader-view');
    const container = document.getElementById('reader-container');
    container.innerHTML = '<div style="padding:50px; text-align:center">جاري التحميل...</div>';
    
    try {
        const res = await fetch(`${API_BASE}/pages/${chapterId}`);
        const data = await res.json();
        state.pages = data.pages;
        state.currentChapter = data; // includes next/prev logic

        renderPages();
        saveProgress(state.currentSeries.id, chapterId, 1);
    } catch (e) {
        container.innerHTML = 'خطأ في التحميل <button onclick="location.reload()">إعادة</button>';
    }
}

function renderPages() {
    const container = document.getElementById('reader-container');
    container.className = state.settings.mode; // vertical or horizontal-rtl
    
    container.innerHTML = state.pages.map((url, i) => `
        <img src="${url}" loading="${i < 3 ? 'eager' : 'lazy'}" data-idx="${i}">
    `).join('');

    // Intersection Observer for Page Number
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const idx = parseInt(entry.target.dataset.idx) + 1;
                document.getElementById('page-indicator').innerText = `${idx} / ${state.pages.length}`;
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('#reader-container img').forEach(img => observer.observe(img));
}

// --- Navigation & UX ---

function switchView(viewId) {
    document.querySelectorAll('.view').forEach(el => el.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');
    document.getElementById('header').style.display = viewId === 'reader-view' ? 'none' : 'block';
}

function goBack() {
    switchView('home-view');
}

function exitReader() {
    switchView('chapters-view');
}

function saveProgress(seriesId, chapterId, page) {
    state.history[seriesId] = { lastChapter: chapterId, page: page, time: Date.now() };
    localStorage.setItem('manga_history', JSON.stringify(state.history));
}

// --- Settings ---

function toggleSettings() {
    document.getElementById('settings-modal').classList.toggle('hidden');
}

function changeMode(mode) {
    state.settings.mode = mode;
    localStorage.setItem('reader_settings', JSON.stringify(state.settings));
    renderPages(); // Re-render to apply class
}

function applySettings() {
    const radios = document.getElementsByName('mode');
    radios.forEach(r => { if(r.value === state.settings.mode) r.checked = true; });
}