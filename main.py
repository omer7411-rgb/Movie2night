import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הגרסה החכמה", page_icon="🎬", layout="wide")

# עיצוב שחור יוקרתי (Dark Cinema)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418;
        border-radius: 20px;
        padding: 0px;
        margin-bottom: 25px;
        border: 1px solid #2d3139;
        overflow: hidden;
        direction: rtl;
    }
    .card-header { padding: 20px; border-bottom: 1px solid #2d3139; background: #1a1e24; }
    .movie-title { color: #f84444; font-size: 1.9rem; font-weight: 900; }
    .movie-info { padding: 20px; color: #ced4da; font-size: 1.1rem; }
    .buy-link {
        display: block; width: 100%; text-align: center;
        background: #f84444; color: white !important;
        padding: 12px; font-weight: bold; text-decoration: none;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_expert_data():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000) # זמן לטעינת התמונות והשכבות
            
            # לוגיקת דייג לפי מבנה ויזואלי (CSS Computed Styles)
            movies = await page.evaluate('''() => {
                const cards = [];
                // מחפשים אלמנטים שסביר להניח שהם כותרות על תמונות (גודל פונט גדול, צבע לבן, מיקום מוחלט)
                const allElements = document.querySelectorAll('h1, h2, h3, span, div');
                
                // Wix בד"כ שמה סרטים בתוך 'item-data-inner' או מבנה דומה
                document.querySelectorAll('[data-testid="mesh-container-content"], section').forEach(section => {
                    const text = section.innerText || "";
                    if (text.includes('/') && text.includes(':')) {
                        // זיהוי הכותרת הכי בולטת בבלוק (הפונט הכי גדול)
                        let bestTitle = "";
                        let maxFontSize = 0;
                        
                        section.querySelectorAll('*').forEach(el => {
                            const style = window.getComputedStyle(el);
                            const fontSize = parseFloat(style.fontSize);
                            const isWhite = style.color === 'rgb(255, 255, 255)';
                            const content = el.innerText.trim();
                            
                            // שם סרט הוא בד"כ לבן, גדול, ולא מכיל סימנים טכניים
                            if (fontSize > maxFontSize && content.length > 1 && content.length < 40 && !content.includes('/') && !content.includes(':')) {
                                maxFontSize = fontSize;
                                bestTitle = content;
                            }
                        });

                        const link = section.querySelector('a[href*="tickets"], a[href*="event"]');
                        if (bestTitle && bestTitle !== "קרא עוד") {
                            cards.push({
                                title: bestTitle,
                                fullText: text,
                                url: link ? link.href : "https://www.jaffacinema.com/"
                            });
                        }
                    }
                });
                return cards;
            }''')

            seen = set()
            for m in movies:
                # חילוץ זמן מהטקסט המלא של הבלוק
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['fullText'])
                if time_match:
                    date_val, day_val, hour_val = time_match.groups()
                    unique_id = f"{m['title']}-{hour_val}"
                    if unique_id not in seen:
                        # תיקון תאריך "היום" לערך מספרי אם צריך
                        clean_day = "יום רביעי" if "היום" in day_val else day_val
                        
                        results.append({
                            "title": m['title'],
                            "time": hour_val,
                            "day": clean_day,
                            "date": date_val,
                            "url": m['url'],
                            "iso": f"2026-{date_val.split('/')[1].zfill(2)}-{date_val.split('/')[0].zfill(2)}T{hour_val}:00"
                        })
                        seen.add(unique_id)
        finally:
            await browser.close()
    return results

st.title("🍿 קולנוע יפו - לוח הקרנות חכם")

if st.button("🚀 סרוק לפי עיצוב (Visual Scan)", type="primary"):
    st.session_state.movies = asyncio.run(get_cinema_expert_data())

if "movies" in st.session_state and st.session_state.movies:
    # תצוגת לוח שנה
    events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in st.session_state.movies]
    calendar(events=events, options={"direction": "rtl", "initialView": "dayGridMonth"})

    st.divider()

    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <div class="card-header">
                    <div class="movie-title">{m['title']}</div>
                </div>
                <div class="movie-info">
                    🗓️ {m['day']} ({m['date']}) <br>
                    ⏰ שעה: <b>{m['time']}</b>
                </div>
                <a href="{m['url']}" target="_blank" class="buy-link">🎟️ הזמנת כרטיסים</a>
            </div>
        """, unsafe_allow_html=True)
