import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; height: 230px;
    }
    .movie-img { width: 170px; min-width: 170px; height: 100%; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.7rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; width: fit-content;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_movies(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("מתחבר לאתר קולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for i in range(10):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.4)

            data = await page.evaluate('''() => {
                const res = [];
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                btns.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const t = el.innerText.trim();
                        if (fs > maxFS && t.length < 55 && !t.includes('/') && !t.includes(':') && t.length > 1) {
                            maxFS = fs; title = t;
                        }
                    });
                    res.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return res;
            }''')

            seen = set()
            for m in data:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d_s, m_s = match.group(1).split('/')
                    # שים לב: הגדרתי שנת 2026 כפי שביקשת
                    date_obj = datetime(2026, int(m_s), int(d_s))
                    uid = f"{m['title']}-{match.group(2)}-{match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": match.group(2), "date_str": f"{d_s.zfill(2)}/{m_s.zfill(2)}",
                            "day_name": days_map[date_obj.weekday()], "dt": date_obj,
                            "iso": f"2026-{m_s.zfill(2)}-{d_s.zfill(2)}T{match.group(2)}:00"
                        })
                        seen.add(uid)
        finally: await browser.close()
    return results

if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 לוח הקרנות מעודכן")

if st.session_state.movies is None:
    if st.button("🔄 טען נתונים", type="primary"):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_movies(msg))
        msg.empty()
        st.rerun()
else:
    # הגדרת יום נוכחי למרץ 2026
    current_date = "2026-03-11"
    
    with st.sidebar:
        st.header("מסננים")
        all_titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_filter = st.selectbox("בחר סרט:", all_titles)
        time_filter = st.selectbox("טווח זמן:", ["הכל", "היום", "השבוע", "החודש"])
        
        # בניית קובץ יומן
        ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for m in st.session_state.movies:
            ds = m['iso'].replace("-","").replace(":","")
            ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{ds}\nURL:{m['url']}\nEND:VEVENT\n"
        ical += "END:VCALENDAR"
        st.download_button("📥 ייצוא ליומן גוגל", ical, "cinema_jaffa.ics")

    # לוגיקת סינון
    f = st.session_state.movies
    if movie_filter != "הכל": f = [m for m in f if m['title'] == movie_filter]
    
    t1, t2 = st.tabs(["📋 רשימת סרטים", "📅 לוח שנה"])
    
    with t1:
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | שעה: {m['time']}</div>
                        </div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        # יצירת אירועים ליומן
        calendar_events = []
        for m in f:
            calendar_events.append({
                "title": m['title'],
                "start": m['iso'],
                "url": m['url'],
                "color": "#f84444"
            })
        
        # הגדרות היומן - חשוב להגדיר initialDate כדי שיראה את מרץ 2026
        calendar_options = {
            "initialDate": current_date,
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
            "locale": "he",
            "direction": "rtl"
        }
        
        calendar(events=calendar_events, options=calendar_options)

    if st.button("🔄 סריקה חדשה"):
        st.session_state.movies = None
        st.rerun()
