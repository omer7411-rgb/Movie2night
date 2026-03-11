import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - 🦖 הגרסה המושלמת", page_icon="🦖", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* עיצוב הדינוזאור והמסלול */
    .dino-track { 
        font-family: monospace; 
        font-size: 28px; 
        color: #f84444; 
        direction: ltr; 
        text-align: center; 
        margin: 20px 0;
    }
    .dino-flip { 
        display: inline-block; 
        transform: scaleX(-1); /* הופך את הדינוזאור שיסתכל ימינה */
    }

    /* עיצוב כרטיסי הסרטים */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; height: 220px;
    }
    .movie-img { 
        width: 160px; min-width: 160px; height: 100%; 
        object-fit: cover; /* התמונה ממלאת את הריבוע בלי להימתח */
        border-left: 1px solid #30363d; 
    }
    .movie-content { 
        padding: 20px; flex-grow: 1; 
        display: flex; flex-direction: column; 
        justify-content: space-between; text-align: right; 
    }
    .movie-title { color: #f84444; font-size: 1.6rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; font-weight: bold; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-decoration: none; 
        font-weight: bold; width: fit-content;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_cinema_final(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    track_size = 25
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # ריצת הדינוזאור
            for i in range(15):
                pos = i % track_size
                track = ["_"] * track_size
                # הדינוזאור עטוף ב-span שעושה לו Flip
                track[pos] = "<span class='dino-flip'>🦖</span>"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(track)}<br>🦖 הדינוזאור רץ לאסוף סרטים...</div>", unsafe_allow_html=True)
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.7)

            data_raw = await page.evaluate('''() => {
                const results = [];
                const buttons = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                buttons.forEach(btn => {
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
                    results.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return results;
            }''')

            seen = set()
            for m in data_raw:
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

def get_ical(movies):
    ical = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Jaffa//HE\n"
    for m in movies:
        ds = m['iso'].replace("-", "").replace(":", "")
        ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{ds}\nURL:{m['url']}\nEND:VEVENT\n"
    ical += "END:VCALENDAR"
    return ical

# לוגיקת אפליקציה
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - 🦖 הממשק המקצועי")

if st.session_state.movies is None:
    status = st.empty()
    if st.button("🚀 שחרר את הדינוזאור!", type="primary"):
        st.session_state.movies = asyncio.run(scrape_cinema_final(status))
        st.rerun()
else:
    # היום: 11/03/2026
    today = datetime(2026, 3, 11)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        search = st.selectbox("🔍 חפש סרט ברשימה:", titles)
    with col2:
        period = st.selectbox("📅 טווח זמן:", ["הכל", "היום", "השבוע", "החודש"])
    with col3:
        st.download_button("🗓️ ייצוא ליומן", get_ical(st.session_state.movies), "jaffa.ics")

    # סינון
    f = st.session_state.movies
    if search != "הכל": f = [m for m in f if m['title'] == search]
    if period == "היום": f = [m for m in f if m['dt'].date() == today.date()]
    elif period == "השבוע": f = [m for m in f if today <= m['dt'] <= today + timedelta(days=7)]
    elif period == "החודש": f = [m for m in f if m['dt'].month == today.month]

    t1, t2 = st.tabs(["📋 רשימת סרטים", "📅 תצוגת חודש"])
    
    with t1:
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/160x220'}" class="movie-img">
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
        events = [{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in f]
        calendar(events=events, options={"locale": "he", "direction": "rtl"})

    if st.button("🔄 סריקה חדשה"):
        st.session_state.movies = None
        st.rerun()
