import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - Mobile Pro", page_icon="🎬", layout="wide")

# CSS מותאם לנייד ולגרפיקה משופרת
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט רספונסיבי */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    
    /* עיצוב למחשב */
    @media (min-width: 768px) {
        .movie-card { height: 250px; }
        .movie-img { width: 200px; min-width: 200px; height: 100%; object-fit: cover; }
    }
    
    /* עיצוב לנייד */
    @media (max-width: 767px) {
        .movie-card { flex-direction: column; height: auto; }
        .movie-img { width: 100%; height: 200px; border-left: none; border-bottom: 1px solid #30363d; }
        .movie-title { font-size: 1.5rem !important; }
    }

    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; margin-top: 5px; }
    
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; text-align: center; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_jaffa_final(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        try:
            status_placeholder.info("סורק את האתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for _ in range(12):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.6)
            
            data = await page.evaluate('''() => {
                const res = [];
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                btns.forEach(btn => {
                    let box = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = box.querySelector('img');
                    let title = ""; let maxFS = 0;
                    box.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fs > maxFS && el.innerText.length < 50 && !el.innerText.includes(':')) {
                            maxFS = fs; title = el.innerText.trim();
                        }
                    });
                    res.push({ title, url: btn.href, img: img ? img.src : "", fullText: box.innerText });
                });
                return res;
            }''')

            seen = set()
            for m in data:
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

if "movies" not in st.session_state: st.session_state.movies = None
if "view_mode" not in st.session_state: st.session_state.view_mode = "רשימה"

st.title("🎬 קולנוע יפו")

if st.session_state.movies is None:
    if st.button("🚀 טען לוח הקרנות", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_jaffa_final(msg))
        st.rerun()
else:
    with st.sidebar:
        st.header("🔍 חיפוש")
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_sel = st.selectbox("בחר סרט:", titles)
        
        st.divider()
        st.subheader("תצוגה")
        # כפתור שמחליף מצבי תצוגה
        if st.button("📅 עבור לתצוגת חודש" if st.session_state.view_mode == "רשימה" else "📋 עבור לתצוגת רשימה"):
            st.session_state.view_mode = "חודש" if st.session_state.view_mode == "רשימה" else "רשימה"
            st.rerun()
        
        st.divider()
        # כפתור ייצוא ליומן גוגל (קובץ ICS)
        ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for m in st.session_state.movies:
            ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{m['iso'].replace('-','').replace(':','')}\nURL:{m['url']}\nEND:VEVENT\n"
        ical += "END:VCALENDAR"
        st.download_button("🗓️ הורד ליומן גוגל", ical, "jaffa_cinema.ics", use_container_width=True)
        
        if st.button("🔄 עדכן נתונים", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # סינון תוצאות
    f = st.session_state.movies
    if movie_sel != "הכל": f = [m for m in f if m['title'] == movie_sel]

    # הצגת התוכן לפי המצב שנבחר
    if st.session_state.view_mode == "רשימה":
        st.subheader(f"רשימת הקרנות ({len(f)})")
        for m in f:
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
        st.subheader("לוח הקרנות חודשי - מרץ 2026")
        evs = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=evs, options={"initialDate": "2026-03-01", "locale": "he", "direction": "rtl", "initialView": "dayGridMonth"})
