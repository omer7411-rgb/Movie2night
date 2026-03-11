import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# הגדרת עמוד חובה
st.set_page_config(page_title="קולנוע יפו - 🦖 הגרסה היציבה", page_icon="🦖", layout="wide")

# עיצוב CSS מתקדם לתיקון סימני פיסוק ותמונות
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* דינוזאור רץ ומסתכל ימינה */
    .dino-track { 
        font-family: monospace; font-size: 28px; color: #f84444; 
        direction: ltr; text-align: center; margin: 20px 0;
    }
    .dino-flip { display: inline-block; transform: scaleX(-1); }

    /* כרטיסיית סרט משופרת */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; height: 230px;
        text-align: right;
    }
    .movie-img { 
        width: 170px; min-width: 170px; height: 100%; 
        object-fit: cover; border-left: 1px solid #30363d; 
    }
    .movie-content { 
        padding: 20px; flex-grow: 1; 
        display: flex; flex-direction: column; 
        justify-content: space-between;
    }
    .movie-title { color: #f84444; font-size: 1.7rem; font-weight: 900; margin: 0; line-height: 1.2; }
    
    /* תיקון סימני פיסוק בעברית */
    .movie-meta { 
        color: #8b949e; font-size: 1.1rem; font-weight: bold;
        direction: rtl; unicode-bidi: plaintext;
    }
    
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; width: fit-content; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_jaffa_final_boss(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            # גלילה מסיבית לטעינת כל הלוח
            for i in range(15):
                pos = i % 25
                track = ["_"] * 25
                track[pos] = "<span class='dino-flip'>🦖</span>"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(track)}<br>🦖 הדינוזאור סורק את כל הלוח...</div>", unsafe_allow_html=True)
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(0.6)

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

def get_ical_data(movies):
    ical = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//JaffaCinema//HE\n"
    for m in movies:
        ds = m['iso'].replace("-", "").replace(":", "")
        ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{ds}\nURL:{m['url']}\nEND:VEVENT\n"
    ical += "END:VCALENDAR"
    return ical

# ניהול המצב ב-Session
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - 🦖 אפליקציית הלוח")

if st.session_state.movies is None:
    place = st.empty()
    if st.button("🚀 שחרר את הדינוזאור לסריקה!", type="primary", key="start_btn"):
        st.session_state.movies = asyncio.run(scrape_jaffa_final_boss(place))
        st.rerun()
else:
    # תאריך נוכחי (סימולציה למרץ)
    today = datetime(2026, 3, 11)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        options = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_filter = st.selectbox("🔍 חפש סרט:", options, key="search_box")
    with col2:
        time_filter = st.selectbox("📅 טווח זמן:", ["הכל", "היום", "השבוע", "החודש"], key="time_box")
    with col3:
        st.download_button("🗓️ ייצוא ליומן גוגל", get_ical_data(st.session_state.movies), "jaffa_cinema.ics", key="dl_btn")

    # פילטור
    f = st.session_state.movies
    if movie_filter != "הכל": f = [m for m in f if m['title'] == movie_filter]
    if time_filter == "היום": f = [m for m in f if m['dt'].date() == today.date()]
    elif time_filter == "השבוע": f = [m for m in f if today <= m['dt'] <= today + timedelta(days=7)]
    elif time_filter == "החודש": f = [m for m in f if m['dt'].month == today.month]

    t1, t2 = st.tabs(["📋 רשימת הקרנות", "📅 תצוגת חודש מלאה"])
    
    with t1:
        st.write(f"נמצאו {len(f)} הקרנות תואמות")
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | שעה: {m['time']} &rlm;!</div>
                        </div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמנת כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        evs = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in f]
        calendar(events=evs, options={"locale": "he", "direction": "rtl", "initialView": "dayGridMonth"})

    if st.button("🔄 סריקה חדשה מהתחלה", key="reset_btn"):
        st.session_state.movies = None
        st.rerun()
