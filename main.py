import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar
from datetime import datetime

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🍿", layout="wide")

# עיצוב CSS משודרג - צבעים שמחים יותר
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .movie-card {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border-right: 5px solid #FF4B4B;
        direction: rtl;
    }
    .movie-title { color: #2c3e50; font-size: 1.5rem; font-weight: bold; margin-bottom: 5px; }
    .movie-meta { color: #7f8c8d; font-size: 1rem; }
    </style>
    """, unsafe_allow_html=True)

if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_movies_clean():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(8000)
            
            data = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, section'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.includes('/') && t.includes(':') && t.length > 20);
            }''')
            
            seen_combinations = set()
            
            for block in data:
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+)\s*(\d{1,2}:\d{2})', block)
                if time_match:
                    date_str, day_str, hour_str = time_match.groups()
                    
                    # חילוץ שם הסרט - לוקחים את השורה הכי קצרה ובולטת בתחילת הבלוק
                    lines = [l for l in block.split('\n') if len(l.strip()) > 2]
                    title = lines[0] if lines else "סרט לא ידוע"
                    
                    # ניקוי כפילויות לפי שם ושעה
                    unique_id = f"{title}-{hour_str}-{date_str}"
                    if unique_id not in seen_combinations:
                        # המרת תאריך לפורמט יומן (נניח שנת 2026 לפי ההקשר)
                        day, month = date_str.split('/')
                        iso_date = f"2026-{month.zfill(2)}-{day.zfill(2)}"
                        
                        results.append({
                            "title": title,
                            "start": f"{iso_date}T{hour_str}:00",
                            "day": day_str,
                            "display_date": date_str,
                            "time": hour_str
                        })
                        seen_combinations.add(unique_id)
        except Exception as e:
            st.error(f"שגיאה: {e}")
        finally:
            await browser.close()
    return results

st.title("🍿 קולנוע יפו - הלוח המעוצב")

if "movies" not in st.session_state:
    st.session_state.movies = []

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🔄 רענן נתונים", type="primary", use_container_width=True):
        with st.spinner("דג סרטים..."):
            st.session_state.movies = asyncio.run(get_movies_clean())

if st.session_state.movies:
    # --- תצוגת יומן (Google Calendar Style) ---
    st.subheader("🗓️ יומן הקרנות חודשי")
    calendar_events = [
        {"title": m['title'], "start": m['start'], "backgroundColor": "#FF4B4B"} 
        for m in st.session_state.movies
    ]
    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        "initialView": "dayGridMonth",
        "direction": "rtl",
    }
    calendar(events=calendar_events, options=calendar_options)

    st.divider()

    # --- תצוגת רשימה מעוצבת ---
    st.subheader("🎬 רשימת סרטים")
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <div class="movie-title">{m['title']}</div>
                <div class="movie-meta">🗓️ {m['day']} ({m['display_date']}) | ⏰ {m['time']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        msg = f"בא לך לסרט? {m['title']} ב-{m['time']} ({m['display_date']})"
        st.link_button(f"🟢 שלח וואטסאפ על {m['title']}", f"https://wa.me/?text={urllib.parse.quote(msg)}")
