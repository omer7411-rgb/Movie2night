import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🎬", layout="wide")

# עיצוב שחור אלגנטי (Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .movie-card {
        background-color: #1c1f26;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #30363d;
        transition: transform 0.2s;
        direction: rtl;
    }
    .movie-card:hover { transform: scale(1.01); border-color: #FF4B4B; }
    .movie-title { color: #ffffff; font-size: 1.6rem; font-weight: bold; margin-bottom: 8px; }
    .movie-meta { color: #a1a1a1; font-size: 1rem; }
    a { text-decoration: none; color: inherit; }
    </style>
    """, unsafe_allow_html=True)

async def get_movies_fixed():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(8000)
            
            blocks = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, section'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.includes('/') && t.includes(':') && t.length > 30);
            }''')
            
            seen_combinations = set()
            for block in blocks:
                # זיהוי זמן ותאריך
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+)\s*(\d{1,2}:\d{2})', block)
                if time_match:
                    date_str, day_str, hour_str = time_match.groups()
                    lines = [l.strip() for l in block.split('\n') if len(l.strip()) > 2]
                    
                    # שיפור זיהוי שם הסרט: מדלגים על שורות עם "/" (מדינה/שנה)
                    movie_title = "סרט ללא שם"
                    for line in lines:
                        if "/" not in line and ":" not in line and "לרכישת" not in line:
                            movie_title = line
                            break
                    
                    unique_id = f"{movie_title}-{hour_str}-{date_str}"
                    if unique_id not in seen_combinations:
                        day, month = date_str.split('/')
                        results.append({
                            "title": movie_title,
                            "start": f"2026-{month.zfill(2)}-{day.zfill(2)}T{hour_str}:00",
                            "day": day_str,
                            "display_date": date_str,
                            "time": hour_str
                        })
                        seen_combinations.add(unique_id)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח הקרנות קולנוע יפו")

if "movies" not in st.session_state:
    st.session_state.movies = []

if st.button("🔄 רענן לוח הקרנות", type="primary"):
    with st.spinner("מעדכן נתונים..."):
        st.session_state.movies = asyncio.run(get_movies_fixed())

if st.session_state.movies:
    # יומן חודשי בעיצוב כהה
    st.subheader("🗓️ מבט חודשי")
    calendar_events = [{"title": m['title'], "start": m['start'], "backgroundColor": "#FF4B4B"} for m in st.session_state.movies]
    calendar(events=calendar_events, options={"direction": "rtl", "themeSystem": "standard"})

    st.divider()
    
    # רשימת הסרטים
    st.subheader("🍿 מה מקרינים?")
    for m in st.session_state.movies:
        # כל הכרטיסייה היא קישור לחיץ לאתר
        st.markdown(f"""
            <a href="https://www.jaffacinema.com/" target="_blank">
                <div class="movie-card">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-meta">📅 {m['day']} ({m['display_date']}) | ⏰ {m['time']}</div>
                </div>
            </a>
        """, unsafe_allow_html=True)
        
        # כפתור וואטסאפ מתחת לכל סרט
        msg = urllib.parse.quote(f"בא לך לראות את '{m['title']}' בקולנוע יפו? {m['day']} ב-{m['time']}")
        st.link_button(f"🟢 שתף בוואטסאפ: {m['title']}", f"https://wa.me/?text={msg}")
