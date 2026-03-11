import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import urllib.parse
from collections import defaultdict

# 1. הגדרות עמוד
st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🎬", layout="wide")

# 2. עיצוב גרפי (מקיף את כל המצבים)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; min-height: 250px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .movie-img { width: 200px; min-width: 200px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin-bottom: 15px; border-bottom: 2px solid #f84444; display: inline-block; width: fit-content; }
    .date-group { margin-bottom: 12px; background: #1c2128; padding: 12px; border-radius: 8px; border: 1px solid #30363d; }
    .date-header { color: #8b949e; font-size: 1rem; font-weight: bold; margin-bottom: 10px; }
    .showtimes-container { display: flex; flex-wrap: wrap; gap: 8px; }
    .showtime-box {
        background: #2d333b; border: 1px solid #444c56; border-radius: 6px;
        padding: 6px 10px; min-width: 95px; text-align: center;
    }
    .time-label { font-weight: bold; font-size: 1.1rem; color: #ffffff; }
    .action-links { display: flex; justify-content: space-around; font-size: 0.8rem; margin-top: 5px; border-top: 1px solid #444c56; padding-top: 4px; gap: 10px;}
    .action-links a { color: #f84444; text-decoration: none; font-weight: bold; }
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; }
        .movie-img { width: 100%; height: 250px; border-left: none; border-bottom: 1px solid #30363d; }
    }
    </style>
    """, unsafe_allow_html=True)

def generate_google_cal_link(title, iso_start):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    start_dt = iso_start.replace("-", "").replace(":", "")
    end_dt_obj = datetime.strptime(iso_start, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=2)
    end_dt = end_dt_obj.strftime("%Y%m%dT%H%M%S")
    params = {"text": f"הקרנה: {title}", "dates": f"{start_dt}/{end_dt}", "location": "קולנוע יפו", "sf": "true", "output": "xml"}
    return base_url + "&" + urllib.parse.urlencode(params)

def create_ics_file(movies_list):
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Jaffa Cinema//HE\n"
    for m in movies_list:
        start = m['iso'].replace("-", "").replace(":", "")
        end_dt = datetime.strptime(m['iso'], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=2)
        end = end_dt.strftime("%Y%m%dT%H%M%S")
        ics_content += f"BEGIN:VEVENT\nSUMMARY:הקרנה: {m['title']}\nDTSTART:{start}\nDTEND:{end}\nLOCATION:קולנוע יפו\nDESCRIPTION:לרכישה: {m['url']}\nEND:VEVENT\n"
    ics_content += "END:VCALENDAR"
    return ics_content

async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("טוען נתונים מקולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for i in range(8):
                await page.evaluate("window.scrollBy(0, 1000)"); await asyncio.sleep(0.5)
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
            curr_year = 2026
            for m in movies_data:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d, month = match.group(1).split('/')
                    date_obj = datetime(curr_year, int(month), int(d))
                    iso_time = f"{curr_year}-{month.zfill(2)}-{d.zfill(2)}T{match.group(2)}:00"
                    results.append({"title": m['title'], "url": m['url'], "img": m['img'], "time": match.group(2), "date_str": f"{d.zfill(2)}/{month.zfill(2)}", "day_name": days_map[date_obj.weekday()], "dt": date_obj, "iso": iso_time})
        finally: await browser.close()
    return results

if "movies" not in st.session_state: st.session_state.movies = None

st.title("🎬 קולנוע יפו - לוח הקרנות")

if st.session_state.movies is None:
    if st.button("🚀 טען את כל ההקרנות", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_full_board(msg))
        st.rerun()
else:
    now = datetime(2026, 3, 11)
    with st.sidebar:
        st.header("⚙️ הגדרות")
        view_mode = st.radio("תצוגה:", ["רשימה", "חודש"])
        st.divider()
        movie_filter = st.selectbox("סרט:", ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies))))
        time_filter = st.radio("זמן:", ["הכל", "היום", "7 ימים", "30 ימים"])
        st.divider()
        
        # סינון לצורך ייצוא
        f_exp = st.session_state.movies
        if movie_filter != "הכל": f_exp = [m for m in f_exp if m['title'] == movie_filter]
        if time_filter == "היום": f_exp = [m for m in f_exp if m['dt'].date() == now.date()]
        
        st.download_button("📂 ייצא הכל ליומן (ICS)", data=create_ics_file(f_exp), file_name="jaffa_cinema.ics", mime="text/calendar", use_container_width=True)
        if st.button("🔄 רענן נתונים", use_container_width=True):
            st.session_state.movies = None; st.rerun()

    # החלת סינונים
    f = st.session_state.movies
    if movie_filter != "הכל": f = [m for m in f if m['title'] == movie_filter]
    if time_filter == "היום": f = [m for m in f if m['dt'].date() == now.date()]
    elif time_filter == "7 ימים": f = [m for m in f if now.date() <= m['dt'].date() <= (now + timedelta(days=7)).date()]
    elif time_filter == "30 ימים": f = [m for m in f if now.date() <= m['dt'].date() <= (now + timedelta(days=30)).date()]
    f = sorted(f, key=lambda x: x['dt'])

    if view_mode == "רשימה":
        movie_groups = defaultdict(lambda: defaultdict(list))
        movie_images = {}
        for m in f:
            movie_groups[m['title']][(m['date_str'], m['day_name'])].append(m)
            movie_images[m['title']] = m['img']
        
        for title in sorted(movie_groups.keys()):
            img_url = movie_images[title]
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{img_url}" class="movie-img">
                    <div class="movie-content">
                        <div class="movie-title">{title}</div>
                        {"".join([f'''
                            <div class="date-group">
                                <div class="date-header">📅 יום {d_name} | {d_str}</div>
                                <div class="showtimes-container">
                                    {"".join([f"""
                                        <div class="showtime-box">
                                            <div class="time-label">{s['time']}</div>
                                            <div class="action-links">
                                                <a href="{s['url']}" target="_blank">🎟️ קנה</a>
                                                <a href="{generate_google_cal_link(title, s['iso'])}" target="_blank">📅 יומן</a>
                                            </div>
                                        </div>
                                    """ for s in sorted(times, key=lambda x: x['time'])])}
                                </div>
                            </div>
                        ''' for (d_str, d_name), times in sorted(movie_groups[title].items(), key=lambda x: datetime.strptime(x[0][0], "%d/%m"))])}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        calendar_events = [{"title": f"{m['time']} - {m['title']}", "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=calendar_events, options={"initialDate": "2026-03-11", "locale": "he", "direction": "rtl", "initialView": "dayGridMonth"})
