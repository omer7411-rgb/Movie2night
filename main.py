import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
import pandas as pd

st.set_page_config(page_title="קולנוע יפו - מהדורת הדינוזאור", page_icon="🦖", layout="wide")

# עיצוב האפליקציה
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    .movie-img { width: 180px; min-width: 180px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 20px; flex-grow: 1; }
    .movie-title { color: #f84444; font-size: 1.7rem; font-weight: 900; margin: 0; }
    .movie-meta { color: #8b949e; font-size: 1rem; margin-top: 10px; font-weight: bold; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 8px 20px; border-radius: 6px; text-decoration: none; margin-top: 15px; font-weight: bold;
    }
    .dino-track { font-family: monospace; font-size: 20px; color: #f84444; }
    </style>
    """, unsafe_allow_html=True)

async def scrape_cinema_with_dino(status_placeholder):
    results = []
    # מסלול הדינוזאור
    track = ["_"] * 20
    dino_pos = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # עדכון דינוזאור רץ בזמן הטעינה
            for i in range(5):
                dino_pos = i % 20
                current_track = list(track)
                current_track[dino_pos] = "🦖"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(current_track)} 🌐 מתחבר...</div>", unsafe_allow_html=True)
                if i == 0: await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
                await asyncio.sleep(0.5)

            # גלילה עם דינוזאור
            for i in range(10):
                dino_pos = (5 + i) % 20
                current_track = list(track)
                current_track[dino_pos] = "🦖"
                status_placeholder.markdown(f"<div class='dino-track'>{''.join(current_track)} 📜 גולל ומחפש סרטים...</div>", unsafe_allow_html=True)
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.8)
            
            movies_raw = await page.evaluate('''() => {
                const items = [];
                const buttons = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                buttons.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fs > maxFS && el.innerText.length < 50 && !el.innerText.includes('/') && !el.innerText.includes(':')) {
                            maxFS = fs; title = el.innerText.trim();
                        }
                    });
                    items.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return items;
            }''')

            seen = set()
            for m in movies_raw:
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if time_match and m['title']:
                    uid = f"{m['title']}-{time_match.group(2)}-{time_match.group(1)}"
                    if uid not in seen:
                        day, month = time_match.group(1).split('/')
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": time_match.group(2), "date": f"{day.zfill(2)}/{month.zfill(2)}",
                            "iso": f"2026-{month.zfill(2)}-{day.zfill(2)}T{time_match.group(2)}:00"
                        })
                        seen.add(uid)
        finally: await browser.close()
    return results

def create_ical(movies):
    ical = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Jaffa Cinema//HE\n"
    for m in movies:
        dt_str = m['iso'].replace("-", "").replace(":", "")
        ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{dt_str}\nURL:{m['url']}\nEND:VEVENT\n"
    ical += "END:VCALENDAR"
    return ical

st.title("🎬 קולנוע יפו - 🦖 Dino-Scan")

if "movies" not in st.session_state:
    status_msg = st.empty()
    if st.button("🚀 שחרר את הדינוזאור לסרוק!", type="primary"):
        st.session_state.movies = asyncio.run(scrape_cinema_with_dino(status_msg))
        status_msg.success(f"🦖 הדינוזאור חזר עם {len(st.session_state.movies)} סרטים!")
        st.rerun()
else:
    # כלי חיפוש וייצוא
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 חפש סרט...", placeholder="הקלד שם סרט...")
    with col2:
        date_list = ["הכל"] + sorted(list(set(m['date'] for m in st.session_state.movies)))
        date_filter = st.selectbox("📅 תאריך", date_list)
    with col3:
        st.download_button("🗓️ הורד ליומן", data=create_ical(st.session_state.movies), file_name="movies.ics")

    filtered = [m for m in st.session_state.movies if (search.lower() in m['title'].lower()) and (date_filter == "הכל" or m['date'] == date_filter)]

    t1, t2 = st.tabs(["📋 רשימה", "📅 יומן חודשי"])
    
    with t1:
        for m in filtered:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/180x250'}" class="movie-img">
                    <div class="movie-content">
                        <div class="movie-title">{m['title']}</div>
                        <div class="movie-meta">📅 {m['date']} | ⏰ {m['time']}</div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        calendar_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in filtered]
        calendar(events=calendar_events, options={"headerToolbar": {"right": "dayGridMonth"}})
