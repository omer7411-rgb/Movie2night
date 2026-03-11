import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

# הגדרת עמוד חובה בראש הקוד
st.set_page_config(page_title="קולנוע יפו - הגרסה היציבה", page_icon="🦖", layout="wide")

# עיצוב CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    .movie-img { width: 180px; min-width: 180px; height: 250px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 20px; flex-grow: 1; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.7rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1rem; margin-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 8px 20px; border-radius: 6px; text-decoration: none; margin-top: 15px; font-weight: bold;
    }
    .dino-track { font-family: monospace; font-size: 24px; color: #f84444; direction: ltr; text-align: center; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

async def run_dino_scraper(status_placeholder):
    results = []
    track_size = 20
    async with async_playwright() as p:
        # הפעלה במצב headless
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה ודינוזאור
            for i in range(12):
                pos = i % track_size
                track = ["_"] * track_size
                track[pos] = "🦖"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(track)}<br>🦖 הדינוזאור אוסף את הסרטים...</div>", unsafe_allow_html=True)
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.6)

            # שליפת נתונים
            movies_raw = await page.evaluate('''() => {
                const data = [];
                const buttons = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                buttons.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fs > maxFS && el.innerText.length < 50 && !el.innerText.includes('/') && !el.innerText.includes(':')) {
                            maxFS = fs; title = el.innerText.trim();
                        }
                    });
                    data.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return data;
            }''')

            seen = set()
            for m in movies_raw:
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if time_match and m['title']:
                    uid = f"{m['title']}-{time_match.group(2)}-{time_match.group(1)}"
                    if uid not in seen:
                        day, month = time_match.group(1).split('/')
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": time_match.group(2), "date": f"{day.zfill(2)}/{month.zfill(2)}",
                            "iso": f"2026-{month.zfill(2)}-{day.zfill(2)}T{time_match.group(2)}:00"
                        })
                        seen.add(uid)
        finally:
            await browser.close()
    return results

# ניהול מצב האפליקציה (Session State)
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - 🦖 Dino-App")

# כפתור הסריקה
if st.session_state.movies is None:
    status_msg = st.empty()
    if st.button("🚀 הפעל סריקה ודינוזאור", type="primary"):
        with st.spinner("הדינוזאור מתכונן..."):
            st.session_state.movies = asyncio.run(run_dino_scraper(status_msg))
            st.rerun()
else:
    # ממשק סינון וחיפוש
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 חפש שם של סרט...", "")
    with col2:
        dates = ["הכל"] + sorted(list(set(m['date'] for m in st.session_state.movies)))
        date_sel = st.selectbox("📅 בחר תאריך", dates)
    with col3:
        if st.button("🔄 סריקה חדשה"):
            st.session_state.movies = None
            st.rerun()

    # סינון
    filtered = [m for m in st.session_state.movies if 
                (search.lower() in m['title'].lower()) and 
                (date_sel == "הכל" or m['date'] == date_sel)]

    tab1, tab2 = st.tabs(["📋 רשימה", "📅 לוח שנה"])
    
    with tab1:
        for m in filtered:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/180x250'}" class="movie-img">
                    <div class="movie-content">
                        <div class="movie-title">{m['title']}</div>
                        <div class="movie-meta">⏰ {m['time']} | 📅 {m['date']}</div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמנת כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in filtered]
        calendar(events=events, options={"headerToolbar": {"right": "dayGridMonth"}})
