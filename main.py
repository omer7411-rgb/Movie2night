import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🍿", layout="wide")

# עיצוב לילה קולנועי
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid #2d3139;
        direction: rtl;
        transition: 0.3s;
    }
    .card-content { padding: 25px; }
    .movie-title { color: #f84444; font-size: 2rem; font-weight: 900; margin-bottom: 5px; }
    .movie-desc { color: #ced4da; font-size: 1rem; line-height: 1.5; margin-bottom: 15px; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; border-top: 1px solid #2d3139; padding-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444; color: white !important;
        padding: 10px 20px; border-radius: 8px; font-weight: bold; text-decoration: none; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_data():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            
            # גלילה למטה כדי לטעון את כל הסרטים
            for _ in range(5):
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(1000)
            
            # סריקת בלוקים משופרת
            movies_data = await page.evaluate('''() => {
                const data = [];
                // מחפשים את המכולות של Wix שמחזיקות כל סרט בנפרד
                document.querySelectorAll('[data-testid="mesh-container-content"], section').forEach(container => {
                    const text = container.innerText || "";
                    if (text.includes('/') && text.includes(':')) {
                        let title = "";
                        let description = "";
                        let maxFS = 0;
                        
                        // חיפוש שם הסרט לפי גודל פונט
                        const elements = container.querySelectorAll('*');
                        elements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            const fs = parseFloat(style.fontSize);
                            const txt = el.innerText.trim();
                            
                            if (fs > maxFS && txt.length > 1 && txt.length < 40 && !txt.includes('/') && !txt.includes(':')) {
                                maxFS = fs;
                                title = txt;
                            }
                        });

                        // חיפוש תיאור: הטקסט הארוך בבלוק שאינו הכותרת
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 30);
                        description = lines.find(l => l !== title && !l.includes('/')) || "";

                        const link = container.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        
                        if (title && title !== "קרא עוד") {
                            data.push({
                                title: title,
                                desc: description,
                                raw: text,
                                url: link ? link.href : "https://www.jaffacinema.com/"
                            });
                        }
                    }
                });
                return data;
            }''')

            seen = set()
            for m in movies_data:
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['raw'])
                if time_match:
                    d_val, day_val, h_val = time_match.groups()
                    unique_key = f"{m['title']}-{h_val}"
                    if unique_key not in seen:
                        results.append({
                            "title": m['title'],
                            "desc": m['desc'],
                            "time": h_val,
                            "day": day_val,
                            "date": d_val,
                            "url": m['url'],
                            "iso": f"2026-{d_val.split('/')[1].zfill(2)}-{d_val.split('/')[0].zfill(2)}T{h_val}:00"
                        })
                        seen.add(unique_key)
        finally:
            await browser.close()
    return results

st.title("🍿 לוח הקרנות קולנוע יפו")

if st.button("🔄 עדכן לוח (סריקה עמוקה)", type="primary"):
    st.session_state.movies = asyncio.run(get_cinema_data())

if "movies" in st.session_state and st.session_state.movies:
    # לוח שנה
    events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in st.session_state.movies]
    calendar(events=events, options={"direction": "rtl"})

    st.divider()

    # כרטיסיות
    for m in st.session_state.movies:
        with st.container():
            st.markdown(f"""
                <div class="movie-card">
                    <div class="card-content">
                        <div class="movie-title">{m['title']}</div>
                        <div class="movie-desc">{m['desc']}</div>
                        <div class="movie-meta">🗓️ {m['day']} ({m['date']}) | ⏰ {m['time']}</div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים: {m['title']}</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            msg = urllib.parse.quote(f"בא לך לראות את '{m['title']}'? {m['day']} ב-{m['time']}. לינק: {m['url']}")
            st.link_button(f"🟢 שלח לחברים", f"https://wa.me/?text={msg}")
