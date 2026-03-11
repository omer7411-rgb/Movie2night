import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# הגדרת דף
st.set_page_config(page_title="קולנוע יפו - הגרסה הסופית", page_icon="🎬", layout="wide")

# CSS מותאם לנייד, כפתורי רכישה וגרפיקה
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט רספונסיבי */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    
    @media (min-width: 768px) {
        .movie-card { height: 250px; }
        .movie-img { width: 200px; min-width: 200px; height: 100%; object-fit: cover; border-left: 1px solid #30363d; }
    }
    
    @media (max-width: 767px) {
        .movie-card { flex-direction: column; height: auto; }
        .movie-img { width: 100%; height: 220px; border-bottom: 1px solid #30363d; }
    }

    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; line-height: 1.1; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; font-weight: bold; margin-top: 5px; }
    
    .buy-btn {
        display: block; background-color: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; text-decoration: none !important; 
        font-weight: bold; text-align: center; margin-top: 15px; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_jaffa_cinema_complete(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        try:
            status_placeholder.info("מתחבר לאתר וטוען את כל הלוח...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה יסודית לטעינת כל הלוח של Wix
            for i in range(15):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.6)
                status_placeholder.text(f"סורק סרטים... ({i+1}/15)")

            data = await page.evaluate('''() => {
                const movies = [];
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                btns.forEach(btn => {
                    let box = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = box.querySelector('img');
                    let title = ""; let maxFS = 0;
                    box.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const t = el.innerText.trim();
                        if (fs > maxFS && t.length < 50 && !t.includes('/') && !t.includes(':')) {
                            maxFS = fs; title = t;
                        }
                    });
                    movies.push({ title, url: btn.href, img: img ? img.src : "", fullText: box.innerText });
                });
                return movies;
            }''')

            seen = set()
            for m in data:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d_s, m_s = match.group(1).split('/')
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

# ניהול מצב (State)
if "movies" not in st.session_state: st.session_state.movies = None
if "view" not in st.session_state: st.session_state.view = "רשימה"

st.title("🎬 לוח הקרנות - קולנוע יפו")

if st.session_state.movies is None:
    if st.button("🚀 טען את כל הסרטים", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_jaffa_cinema_complete(msg))
        st.rerun()
else:
    # סרגל צד עם כל הבקשות שלך
    with st.sidebar:
        st.header("🔍 חיפוש")
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_sel = st.selectbox("חפש סרט:", titles)
        
        st.divider()
        st.subheader("תצוגה")
        # כפתור החלפת תצוגה
        if st.button("📅 עבור לתצוגת חודש" if st.session_state.view == "רשימה" else "📋 עבור לתצוגת רשימה", use_container_width=True):
            st.session_state.view = "חודש" if st.session_state.view == "רשימה" else "רשימה"
            st.rerun()
        
        st.divider()
        # כפתור ייצוא ליומן גוגל
        ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for m in st.session_state.movies:
            ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{m['iso'].replace('-','').replace(':','')}\nURL:{m['url']}\nEND:VEVENT\n"
        ical += "END:VCALENDAR"
        st.download_button("🗓️ ייצוא ליומן גוגל", ical, "jaffa_cinema.ics", use_container_width=True)
        
        if st.button("🔄 רענן נתונים", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # סינון
    filtered = st.session_state.movies
    if movie_sel != "הכל": filtered = [m for m in filtered if m['title'] == movie_sel]

    # תצוגת התוכן
    if st.session_state.view == "רשימה":
        st.subheader(f"נמצאו {len(filtered)} הקרנות")
        for m in filtered:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | {m['time']}</div>
                        </div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ רכישת כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # תצוגת חודש מלאה
        st.subheader("לוח הקרנות חודשי - מרץ 2026")
        calendar_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in filtered]
        calendar(events=calendar_events, options={
            "initialDate": "2026-03-01",
            "locale": "he",
            "direction": "rtl",
            "initialView": "dayGridMonth"
        })
