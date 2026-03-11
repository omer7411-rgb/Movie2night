import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import urllib.parse
from itertools import groupby

# 1. הגדרות עמוד
st.set_page_config(page_title="קולנוע יפו - לוח הקרנות המלא", page_icon="🎬", layout="wide")

# 2. עיצוב גרפי משופר (כולל עיצוב לשורות זמנים)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; min-height: 280px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .movie-img { width: 220px; min-width: 220px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 24px; flex-grow: 1; display: flex; flex-direction: column; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin-bottom: 15px; line-height: 1.1; }
    
    .screening-row {
        background: #1c2128; border: 1px solid #30363d; border-radius: 8px;
        padding: 10px 15px; margin-bottom: 8px; display: flex;
        justify-content: space-between; align-items: center;
    }
    .screening-info { font-weight: bold; color: #e6edf3; }
    .screening-btns { display: flex; gap: 8px; }
    
    .mini-btn {
        padding: 4px 12px; border-radius: 6px; text-decoration: none !important;
        font-size: 0.85rem; font-weight: bold; transition: 0.2s;
    }
    .buy-mini { background: #f84444; color: white !important; }
    .cal-mini { background: #30363d; color: #adbac7 !important; border: 1px solid #444c56; }
    
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; }
        .movie-img { width: 100%; height: 250px; border-left: none; border-bottom: 1px solid #30363d; }
        .screening-row { flex-direction: column; gap: 10px; text-align: center; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. פונקציות עזר
def generate_google_cal_link(title, iso_start):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    start_dt = iso_start.replace("-", "").replace(":", "")
    end_dt_obj = datetime.strptime(iso_start, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=2)
    end_dt = end_dt_obj.strftime("%Y%m%dT%H%M%S")
    params = {
        "text": f"הקרנה: {title}",
        "dates": f"{start_dt}/{end_dt}",
        "location": "קולנוע יפו, מרזוק ועזר 14, תל אביב יפו",
        "sf": "true", "output": "xml"
    }
    return base_url + "&" + urllib.parse.urlencode(params)

# 4. סורק מעודכן - מוצא את כל המועדים
async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        try:
            status_placeholder.info("סורק את כל מועדי ההקרנות מהאתר...")
            await page.goto("https://www.jaffacinema.com/movies-all", wait_until="networkidle")
            
            for _ in range(10): 
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.4)
            
            movies_data = await page.evaluate('''() => {
                const res = [];
                const buyBtns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                buyBtns.forEach(btn => {
                    let container = btn.closest('[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 50 && !txt.includes('/') && !txt.includes(':')) {
                            maxFS = fs; title = txt;
                        }
                    });
                    res.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return res;
            }''')
            
            seen = set()
            curr_year = datetime.now().year
            for m in movies_data:
                # שינוי קריטי: findall מוצא את כל המועדים בתוך הכרטיס
                matches = re.findall(r'(\d{1,2}/\d{1,2})\s+(\d{1,2}:\d{2})', m['fullText'])
                for date_part, time_part in matches:
                    d, month = date_part.split('/')
                    uid = f"{m['title']}-{date_part}-{time_part}"
                    if uid not in seen:
                        try:
                            date_obj = datetime(curr_year, int(month), int(d))
                            iso_time = f"{curr_year}-{month.zfill(2)}-{d.zfill(2)}T{time_part}:00"
                            results.append({
                                "title": m['title'], "url": m['url'], "img": m['img'],
                                "time": time_part, "date_str": date_part,
                                "day_name": days_map[date_obj.weekday()], "dt": date_obj, "iso": iso_time
                            })
                            seen.add(uid)
                        except: continue
        finally: await browser.close()
    return results

# 5. ניהול אפליקציה
if "movies" not in st.session_state: st.session_state.movies = None

st.title("🎬 קולנוע יפו - לוח הקרנות מלא")

if st.session_state.movies is None:
    if st.button("🚀 טען את כל ההקרנות מהאתר", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_full_board(msg))
        st.rerun()
else:
    # סרגל צד
    with st.sidebar:
        st.header("🔍 סינון")
        view_mode = st.radio("תצוגה:", ["רשימה", "חודש"])
        if st.button("🔄 עדכן נתונים"):
            st.session_state.movies = None
            st.rerun()

    f = sorted(st.session_state.movies, key=lambda x: (x['title'], x['dt']))

    if view_mode == "רשימה":
        # קיבוץ לפי שם הסרט להצגה מאוחדת
        for title, group in groupby(f, key=lambda x: x['title']):
            screenings = list(group)
            img_url = screenings[0]['img']
            
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{img_url}" class="movie-img">
                    <div class="movie-content">
                        <div class="movie-title">{title}</div>
            """, unsafe_allow_html=True)
            
            for s in screenings:
                cal_link = generate_google_cal_link(s['title'], s['iso'])
                st.markdown(f"""
                    <div class="screening-row">
                        <div class="screening-info">יום {s['day_name']} {s['date_str']} בשעה {s['time']}</div>
                        <div class="screening-btns">
                            <a href="{s['url']}" target="_blank" class="mini-btn buy-mini">🎟️ כרטיסים</a>
                            <a href="{cal_link}" target="_blank" class="mini-btn cal-mini">📅 יומן</a>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)
    else:
        # תצוגת יומן (Calendar)
        calendar_events = [{"title": f"{m['title']} ({m['time']})", "start": m['iso'], "url": m['url']} for m in f]
        calendar(events=calendar_events, options={"locale": "he", "direction": "rtl"})
