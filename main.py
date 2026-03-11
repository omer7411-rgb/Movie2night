import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import urllib.parse

# 1. הגדרות עמוד
st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🎬", layout="wide")

# 2. עיצוב גרפי רספונסיבי מלא (מחשב + נייד)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; min-height: 280px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .movie-img { width: 220px; min-width: 220px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 24px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; line-height: 1.1; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    
    /* כפתורים בתוך הכרטיס */
    .btn-container { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
    .buy-btn {
        background-color: #f84444 !important; color: white !important;
        padding: 10px 20px; border-radius: 8px; text-decoration: none !important; 
        font-weight: bold; font-size: 1rem; text-align: center; flex: 1; min-width: 140px;
    }
    .cal-btn {
        background-color: #30363d !important; color: white !important;
        padding: 10px 20px; border-radius: 8px; text-decoration: none !important; 
        font-weight: bold; font-size: 1rem; text-align: center; flex: 1; min-width: 140px;
        border: 1px solid #484f58;
    }
    
    /* התאמה לנייד */
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; height: auto; min-height: unset; }
        .movie-img { width: 100%; height: 250px; border-left: none; border-bottom: 1px solid #30363d; }
        .btn-container { flex-direction: column; }
        .buy-btn, .cal-btn { width: 100%; }
        .movie-title { font-size: 1.5rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. פונקציות עזר ליומן
def generate_google_cal_link(title, iso_start):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    start_dt = iso_start.replace("-", "").replace(":", "")
    end_dt_obj = datetime.strptime(iso_start, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=2)
    end_dt = end_dt_obj.strftime("%Y%m%dT%H%M%S")
    params = {
        "text": f"הקרנה: {title}",
        "dates": f"{start_dt}/{end_dt}",
        "details": f"צפייה בסרט {title} בקולנוע יפו",
        "location": "קולנוע יפו, מרזוק ועזר 14, תל אביב יפו",
        "sf": "true", "output": "xml"
    }
    return base_url + "&" + urllib.parse.urlencode(params)

def create_ics_file(movies_list):
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Jaffa Cinema//HE\n"
    for m in movies_list:
        start = m['iso'].replace("-", "").replace(":", "")
        end_dt = datetime.strptime(m['iso'], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=2)
        end = end_dt.strftime("%Y%m%dT%H%M%S")
        ics_content += f"BEGIN:VEVENT\nSUMMARY:הקרנה: {m['title']}\nDTSTART:{start}\nDTEND:{end}\nLOCATION:קולנוע יפו\nDESCRIPTION:לינק לרכישה: {m['url']}\nEND:VEVENT\n"
    ics_content += "END:VCALENDAR"
    return ics_content

# 4. פונקציית הסריקה (Scraper)
async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("מתחבר לאתר קולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for i in range(8):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.5)
            
            movies_data = await page.evaluate('''() => {
                const res = [];
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                btns.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 55 && !txt.includes('/') && !txt.includes(':')) {
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
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d, month = match.group(1).split('/')
                    date_obj = datetime(curr_year, int(month), int(d))
                    iso_time = f"{curr_year}-{month.zfill(2)}-{d.zfill(2)}T{match.group(2)}:00"
                    uid = f"{m['title']}-{match.group(2)}-{match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": match.group(2), "date_str": f"{d.zfill(2)}/{month.zfill(2)}",
                            "day_name": days_map[date_obj.weekday()], "dt": date_obj, "iso": iso_time
                        })
                        seen.add(uid)
        finally: await browser.close()
    return results

# 5. ניהול אפליקציה
if "movies" not in st.session_state: st.session_state.movies = None

st.title("🎬 קולנוע יפו - לוח הקרנות")

if st.session_state.movies is None:
    if st.button("🚀 טען את כל ההקרנות", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_full_board(msg))
        st.rerun()
else:
    now = datetime.now()
    
    # סרגל צד עם כל הבקשות
    with st.sidebar:
        st.header("🔍 ניווט וסינון")
        view_mode = st.radio("בחר תצוגה:", ["רשימה", "חודש"])
        
        st.divider()
        all_titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_filter = st.selectbox("חפש שם סרט:", all_titles)
        time_filter = st.radio("מתי תרצו ללכת?", ["הכל", "היום", "7 ימים קרובים", "30 ימים קרובים"])
        
        st.divider()
        # לוגיקת סינון עבור הייצוא
        f_export = st.session_state.movies
        if movie_filter != "הכל": f_export = [m for m in f_export if m['title'] == movie_filter]
        
        ics_data = create_ics_file(f_export)
        st.download_button("📂 הורד הכל ליומן (ICS)", data=ics_data, file_name="jaffa_cinema.ics", mime="text/calendar", use_container_width=True)
        
        if st.button("🔄 עדכן נתונים (סריקה חדשה)", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # החלת סינונים על התצוגה
    f = st.session_state.movies
    if movie_filter != "הכל": f = [m for m in f if m['title'] == movie_filter]
    if time_filter == "היום": f = [m for m in f if m['dt'].date() == now.date()]
    elif time_filter == "7 ימים קרובים": f = [m for m in f if now.date() <= m['dt'].date() <= (now + timedelta(days=7)).date()]
    elif time_filter == "30 ימים קרובים": f = [m for m in f if now.date() <= m['dt'].date() <= (now + timedelta(days=30)).date()]
    
    f = sorted(f, key=lambda x: x['dt'])

    # תצוגה נבחרת
    if view_mode == "רשימה":
        st.write(f"נמצאו {len(f)} הקרנות")
        for m in f:
            cal_link = generate_google_cal_link(m['title'], m['iso'])
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | {m['time']}</div>
                        </div>
                        <div class="btn-container">
                            <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                            <a href="{cal_link}" target="_blank" class="cal-btn">📅 ליומן גוגל</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        calendar_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=calendar_events, options={
            "initialDate": now.strftime("%Y-%m-%d"),
            "locale": "he", "direction": "rtl", "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}
        })
