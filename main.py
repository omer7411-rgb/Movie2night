import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🍿", layout="wide")

# עיצוב שחור יוקרתי (Dark Cinema)
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418;
        border-radius: 20px;
        margin-bottom: 25px;
        border: 1px solid #2d3139;
        overflow: hidden;
        direction: rtl;
        transition: 0.3s;
    }
    .movie-card:hover { border-color: #f84444; background: #1a1e24; }
    .card-content { padding: 25px; }
    .movie-title { color: #ffffff; font-size: 2.2rem; font-weight: 900; margin-bottom: 10px; }
    .movie-meta { color: #8b949e; font-size: 1.2rem; margin-bottom: 20px; }
    .buy-btn {
        display: inline-block; background: #f84444; color: white !important;
        padding: 12px 25px; border-radius: 10px; font-weight: bold; text-decoration: none;
        font-size: 1.1rem;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_visual_cinema_data():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)
            
            # סריקה לפי מאפיינים ויזואליים (Computed Styles)
            movies = await page.evaluate('''() => {
                const items = [];
                // סריקה של כל בלוק שמכיל מידע על הקרנה
                document.querySelectorAll('section, div[data-testid="mesh-container-content"]').forEach(block => {
                    const text = block.innerText || "";
                    if (text.includes('/') && text.includes(':')) {
                        let mainTitle = "";
                        let maxFontSize = 0;
                        
                        // מחפשים את האלמנט הכי גדול ובולט בתוך הבלוק (שם הסרט)
                        block.querySelectorAll('*').forEach(el => {
                            const style = window.getComputedStyle(el);
                            const fSize = parseFloat(style.fontSize);
                            const content = el.innerText.trim();
                            
                            // סינון: שם סרט הוא בד"כ קצר, גדול, ולא מכיל סימני זמן/מקום
                            if (fSize > maxFontSize && content.length > 1 && content.length < 45 && 
                                !content.includes('/') && !content.includes(':') && !content.includes('לרכישת')) {
                                maxFontSize = fSize;
                                mainTitle = content;
                            }
                        });

                        // חילוץ לינק הרכישה הספציפי לבלוק הזה
                        const ticketLink = block.querySelector('a[href*="tickets"], a[href*="event-details"]');
                        
                        if (mainTitle && mainTitle !== "קרא עוד") {
                            items.push({
                                title: mainTitle,
                                rawText: text,
                                url: ticketLink ? ticketLink.href : "https://www.jaffacinema.com/"
                            });
                        }
                    }
                });
                return items;
            }''')

            seen = set()
            for m in movies:
                # חילוץ תאריך ושעה מהטקסט של הבלוק
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['rawText'])
                if time_match:
                    date_val, day_val, hour_val = time_match.groups()
                    unique_id = f"{m['title']}-{hour_val}-{date_val}"
                    
                    if unique_id not in seen:
                        results.append({
                            "title": m['title'],
                            "time": hour_val,
                            "day": day_val,
                            "date": date_val,
                            "url": m['url'],
                            "iso": f"2026-{date_val.split('/')[1].zfill(2)}-{date_val.split('/')[0].zfill(2)}T{hour_val}:00"
                        })
                        seen.add(unique_id)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח ההקרנות החכם - קולנוע יפו")

if st.button("🚀 סרוק לוח מעודכן", type="primary"):
    with st.spinner("מזהה סרטים לפי גודל פונט ומיקום..."):
        st.session_state.movies = asyncio.run(get_visual_cinema_data())

if "movies" in st.session_state and st.session_state.movies:
    # יומן חודשי מעוצב
    st.subheader("🗓️ מבט חודשי")
    cal_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "backgroundColor": "#f84444"} for m in st.session_state.movies]
    calendar(events=cal_events, options={"direction": "rtl", "initialView": "dayGridMonth"})

    st.divider()

    # רשימת סרטים
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <div class="card-content">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-meta">🗓️ {m['day']} ({m['date']}) | ⏰ {m['time']}</div>
                    <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ לרכישת כרטיסים</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        msg = urllib.parse.quote(f"בא לך לראות את '{m['title']}'? {m['day']} בשעה {m['time']}. לינק להזמנה: {m['url']}")
        st.link_button(f"🟢 שלח בוואטסאפ", f"https://wa.me/?text={msg}")
