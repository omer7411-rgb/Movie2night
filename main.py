import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - 🦖 הגרסה המלאה", page_icon="🦖", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    .movie-img { width: 180px; min-width: 180px; height: 260px; object-fit: cover; border-left: 1px solid #30363d; background: #000; }
    .movie-content { padding: 20px; flex-grow: 1; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; margin-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-decoration: none; margin-top: 15px; font-weight: bold;
    }
    .dino-track { font-family: monospace; font-size: 24px; color: #f84444; direction: ltr; text-align: center; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

async def run_cinema_scraper_pro(status_placeholder):
    results = []
    track_size = 25
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # שימוש ב-Viewport גדול כדי למנוע טעויות מיקום
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            status_placeholder.markdown("<div class='dino-track'>🦖 ___________ 🌐</div>", unsafe_allow_html=True)
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # שלב 1: גלילה עמוקה עם הדינוזאור
            for i in range(15):
                pos = i % track_size
                track = ["_"] * track_size
                track[pos] = "🦖"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(track)} <br> 📜 סורק לעומק... ({i+1}/15)</div>", unsafe_allow_html=True)
                
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(0.7)

            # שלב 2: איסוף נתונים גלובלי (אחרי שהכל נטען)
            status_placeholder.info("🎣 דג את כל הסרטים מהרשת...")
            
            movies_raw = await page.evaluate('''() => {
                const data = [];
                // מוצאים את כל כפתורי הרכישה כנקודות עוגן
                const buttons = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                
                buttons.forEach(btn => {
                    // מוצאים את הקונטיינר של Wix שעוטף את הסרט
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    
                    const img = container.querySelector('img');
                    let title = "";
                    let maxFS = 0;
                    
                    // מציאת הכותרת הכי גדולה בבלוק
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 60 && !txt.includes('/') && !txt.includes(':')) {
                            maxFS = fs;
                            title = txt;
                        }
                    });

                    if (title && title !== "קרא עוד") {
                        data.push({
                            title: title,
                            url: btn.href,
                            img: img ? img.src : "",
                            fullText: container.innerText
                        });
                    }
                });
                return data;
            }''')

            # שלב 3: עיבוד וניקוי ב-Python
            seen = set()
            for m in movies_raw:
                # חילוץ תאריך ושעה
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if time_match:
                    uid = f"{m['title']}-{time_match.group(2)}-{time_match.group(1)}"
                    if uid not in seen:
                        day, month = time_match.group(1).split('/')
                        results.append({
                            "title": m['title'],
                            "url": m['url'],
                            "img": m['img'],
                            "time": time_match.group(2),
                            "date": f"{day.zfill(2)}/{month.zfill(2)}",
                            "iso": f"2026-{month.zfill(2)}-{day.zfill(2)}T{time_match.group(2)}:00"
                        })
                        seen.add(uid)
                        
        finally:
            await browser.close()
    return results

# ניהול מצב
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - 🦖 Dino-Scanner")

if st.session_state.movies is None:
    status_msg = st.empty()
    if st.button("🚀 שחרר את הדינוזאור לחיפוש!", type="primary"):
        st.session_state.movies = asyncio.run(run_cinema_scraper_pro(status_msg))
        st.rerun()
else:
    # ממשק חיפוש
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 חפש סרט...", "")
    with col2:
        dates = ["הכל"] + sorted(list(set(m['date'] for m in st.session_state.movies)))
        date_sel = st.selectbox("📅 תאריך", dates)
    with col3:
        if st.button("🔄 סריקה חדשה"):
            st.session_state.movies = None
            st.rerun()

    # פילטר
    filtered = [m for m in st.session_state.movies if 
                (search_term.lower() in m['title'].lower()) and 
                (date_sel == "הכל" or m['date'] == date_sel)]

    t1, t2 = st.tabs(["📋 רשימת סרטים", "📅 יומן חודשי"])
    
    with t1:
        st.write(f"נמצאו {len(filtered)} הקרנות")
        for m in filtered:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/180x260'}" class="movie-img">
                    <div class="movie-content">
                        <div class="movie-title">{m['title']}</div>
                        <div class="movie-meta">🗓️ {m['date']} | ⏰ {m['time']}</div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        cal_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in filtered]
        calendar(events=cal_events, options={"headerToolbar": {"right": "dayGridMonth"}})
