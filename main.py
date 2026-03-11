import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - 🦖 יציב", page_icon="🦖", layout="wide")

# עיצוב CSS מתוקן לסימני פיסוק ותמונות
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    .dino-track { 
        font-family: monospace; font-size: 28px; color: #f84444; 
        direction: ltr; text-align: center; margin: 20px 0;
    }
    .dino-flip { display: inline-block; transform: scaleX(-1); }

    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; height: 220px;
        text-align: right;
    }
    .movie-img { 
        width: 160px; min-width: 160px; height: 100%; 
        object-fit: cover; border-left: 1px solid #30363d; 
    }
    .movie-content { 
        padding: 20px; flex-grow: 1; 
        display: flex; flex-direction: column; 
        justify-content: space-between;
    }
    .movie-title { color: #f84444; font-size: 1.6rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; direction: rtl; unicode-bidi: embed; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; width: fit-content;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_jaffa_final(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            for i in range(12):
                track = ["_"] * 20
                track[i % 20] = "<span class='dino-flip'>🦖</span>"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(track)}<br>הדינוזאור סורק...</div>", unsafe_allow_html=True)
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.5)

            data = await page.evaluate('''() => {
                const res = [];
                document.querySelectorAll('a').forEach(btn => {
                    if (btn.innerText.includes('לרכישת')) {
                        let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                        const img = container.querySelector('img');
                        let title = ""; let maxFS = 0;
                        container.querySelectorAll('*').forEach(el => {
                            const fs = parseFloat(window.getComputedStyle(el).fontSize);
                            if (fs > maxFS && el.innerText.length < 50 && !el.innerText.includes('/') && !el.innerText.includes(':')) {
                                maxFS = fs; title = el.innerText.trim();
                            }
                        });
                        res.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                    }
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

# יצירת יומן
def make_ical(movies):
    ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
    for m in movies:
        ds = m['iso'].replace("-", "").replace(":", "")
        ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{ds}\nURL:{m['url']}\nEND:VEVENT\n"
    ical += "END:VCALENDAR"
    return ical

# ניהול מצב האפליקציה
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - 🦖 הממשק הסופי")

if st.session_state.movies is None:
    placeholder = st.empty()
    if st.button("🚀 שחרר את הדינוזאור!", type="primary"):
        st.session_state.movies = asyncio.run(scrape_jaffa_final(placeholder))
        st.rerun()
else:
    today = datetime(2026, 3, 11)
    
    # חיפוש וסינון
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        # שימוש ב-key כדי למנוע קריסה של הכפתור
        search_val = st.selectbox("🔍 בחר סרט:", titles, key="movie_search")
    with col2:
        period = st.selectbox("📅 טווח זמן:", ["הכל", "היום", "השבוע", "החודש"], key="period_search")
    with col3:
        st.download_button("🗓️ ייצוא ליומן", make_ical(st.session_state.movies), "jaffa.ics")

    # פילטור הנתונים
    f = st.session_state.movies
    if search_val != "הכל": f = [m for m in f if m['title'] == search_val]
    if period == "היום": f = [m for m in f if m['dt'].date() == today.date()]
    elif period == "השבוע": f = [m for m in f if today <= m['dt'] <= today + timedelta(days=7)]
    elif period == "החודש": f = [m for m in f if m['dt'].month == today.month]

    t1, t2 = st.tabs(["📋 רשימה", "📅 לוח שנה"])
    
    with t1:
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | {m['time']}</div>
                        </div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        evs = [{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in f]
        calendar(events=evs, options={"locale": "he", "direction": "rtl"})

    if st.button("🔄 סריקה חדשה"):
        st.session_state.movies = None
        st.rerun()
