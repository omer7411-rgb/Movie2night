import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - Pro", page_icon="🎬", layout="wide")

# עיצוב CSS - תיקון כפתורים ותמונות
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; height: 250px;
    }
    .movie-img { 
        width: 190px; min-width: 190px; height: 100%; 
        object-fit: cover; border-left: 1px solid #30363d; 
    }
    .movie-content { 
        padding: 20px; flex-grow: 1; 
        display: flex; flex-direction: column; 
        justify-content: space-between; text-align: right;
    }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; line-height: 1.2; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; font-weight: bold; margin-top: 5px; }
    
    /* יישור כפתור הרכישה */
    .buy-container { margin-top: auto; padding-top: 15px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 12px 35px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; font-size: 1rem; text-align: center;
    }
    .buy-btn:hover { background: #ff5f5f !important; }
    </style>
    """, unsafe_allow_html=True)

async def scrape_jaffa_cinema_sidebar(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("מתחבר לאתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for i in range(12): 
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.5)

            movies_raw = await page.evaluate('''() => {
                const data = [];
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                btns.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fs > maxFS && el.innerText.length < 55 && !el.innerText.includes('/') && !el.innerText.includes(':')) {
                            maxFS = fs; title = el.innerText.trim();
                        }
                    });
                    data.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return data;
            }''')

            seen = set()
            for m in movies_raw:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d, month = match.group(1).split('/')
                    date_obj = datetime(2026, int(month), int(d))
                    uid = f"{m['title']}-{match.group(2)}-{match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": match.group(2), "date_str": f"{d.zfill(2)}/{month.zfill(2)}",
                            "day_name": days_map[date_obj.weekday()], "dt": date_obj,
                            "iso": f"2026-{month.zfill(2)}-{d.zfill(2)}T{match.group(2)}:00"
                        })
                        seen.add(uid)
        finally: await browser.close()
    return results

if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 לוח הקרנות קולנוע יפו")

if st.session_state.movies is None:
    if st.button("🚀 טען סרטים", type="primary"):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_jaffa_cinema_sidebar(msg))
        st.rerun()
else:
    # הגדרות זמן וסרגל צד
    today = datetime(2026, 3, 11)
    
    with st.sidebar:
        st.header("🔍 חיפוש וסינון")
        
        # חיפוש לפי שם סרט
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_sel = st.selectbox("בחר שם סרט:", titles)
        
        # סינון לפי תאריך
        time_sel = st.selectbox("טווח זמן:", ["הכל", "היום", "השבוע", "החודש"])
        
        st.divider()
        
        # כפתור ייצוא
        ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for m in st.session_state.movies:
            ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{m['iso'].replace('-','').replace(':','')}\nURL:{m['url']}\nEND:VEVENT\n"
        ical += "END:VCALENDAR"
        st.download_button("🗓️ הורד יומן (ICS)", ical, "jaffa.ics", use_container_width=True)
        
        if st.button("🔄 רענן נתונים", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # לוגיקת סינון
    f = st.session_state.movies
    if movie_sel != "הכל": f = [m for m in f if m['title'] == movie_sel]
    if time_sel == "היום": f = [m for m in f if m['dt'].date() == today.date()]
    elif time_sel == "השבוע": f = [m for m in f if today <= m['dt'] <= today + timedelta(days=7)]
    elif time_sel == "החודש": f = [m for m in f if m['dt'].month == today.month]

    t1, t2 = st.tabs(["📋 רשימת סרטים", "📅 לוח שנה"])
    
    with t1:
        st.write(f"מציג {len(f)} הקרנות")
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | {m['time']}</div>
                        </div>
                        <div class="buy-container">
                            <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ רכישת כרטיסים</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        # לוח שנה מסונכרן למרץ 2026
        evs = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=evs, options={
            "initialDate": "2026-03-11",
            "locale": "he",
            "direction": "rtl",
            "initialView": "dayGridMonth"
        })
