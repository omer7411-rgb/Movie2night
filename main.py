import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🍿", layout="wide")

# עיצוב לילה מעודכן
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid #2d3139;
        direction: rtl;
        padding: 25px;
    }
    .movie-title { color: #f84444; font-size: 2rem; font-weight: 900; margin-bottom: 10px; }
    .movie-desc { color: #ced4da; font-size: 1.1rem; line-height: 1.5; margin-bottom: 15px; }
    .movie-meta { color: #8b949e; font-size: 1.1rem; border-top: 1px solid #2d3139; padding-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 12px 25px; border-radius: 8px; font-weight: bold; text-decoration: none; margin-top: 15px;
        text-align: center; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_data(status):
    results = []
    async with async_playwright() as p:
        status.write("🚀 פותח מנועים...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            status.write("🌐 טוען את קולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            
            # גלילה עמוקה יותר ואיטית יותר לטעינת כל ה-Wix Components
            status.write("📜 סורק את כל הדף (גלילה עמוקה)...")
            for _ in range(8):
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(1.5)
            
            # אסטרטגיה חדשה: חיפוש לפי כפתורי רכישה
            movies_data = await page.evaluate('''() => {
                const foundMovies = [];
                // מוצאים את כל הקישורים שמכילים את המילה "calendar" או "tickets"
                const purchaseLinks = Array.from(document.querySelectorAll('a'))
                    .filter(a => a.href.includes('calendar') || a.innerText.includes('לרכישת'));

                purchaseLinks.forEach(link => {
                    // לכל כפתור, נחפש את הבלוק הקרוב ביותר אליו
                    let container = link.closest('section') || link.parentElement.parentElement.parentElement;
                    const text = container.innerText || "";
                    
                    if (text.includes('/') && text.includes(':')) {
                        let bestTitle = "";
                        let maxFS = 0;
                        
                        // חיפוש הכותרת בתוך הבלוק הספציפי של הכפתור
                        container.querySelectorAll('*').forEach(el => {
                            const fs = parseFloat(window.getComputedStyle(el).fontSize);
                            const txt = el.innerText.trim();
                            if (fs > maxFS && txt.length > 1 && txt.length < 50 && !txt.includes('/') && !txt.includes(':')) {
                                maxFS = fs;
                                bestTitle = txt;
                            }
                        });

                        // חילוץ תיאור
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 35);
                        const description = lines.find(l => l !== bestTitle && !l.includes('/')) || "";

                        foundMovies.push({
                            title: bestTitle,
                            desc: description,
                            raw: text,
                            url: link.href
                        });
                    }
                });
                return foundMovies;
            }''')

            status.write(f"🔍 ניתוח נתונים עבור {len(movies_data)} תוצאות...")
            seen = set()
            for m in movies_data:
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['raw'])
                if time_match:
                    unique_key = f"{m['title']}-{time_match.group(3)}"
                    if unique_key not in seen and m['title'] != "קרא עוד":
                        results.append({
                            "title": m['title'],
                            "desc": m['desc'],
                            "time": time_match.group(3),
                            "day": time_match.group(2),
                            "date": time_match.group(1),
                            "url": m['url'],
                            "iso": f"2026-{time_match.group(1).split('/')[1].zfill(2)}-{time_match.group(1).split('/')[0].zfill(2)}T{time_match.group(3)}:00"
                        })
                        seen.add(unique_key)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח הקרנות מעודכן - קולנוע יפו")

status_msg = st.empty()
if st.button("🔄 סריקה מלאה של האתר", type="primary"):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.movies = loop.run_until_complete(get_cinema_data(status_msg))
    status_msg.success(f"סיימתי! נמצאו {len(st.session_state.movies)} סרטים.")

if "movies" in st.session_state and st.session_state.movies:
    # לוח שנה חודשי
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    
    st.divider()

    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <div class="movie-title">{m['title']}</div>
                <div class="movie-desc">{m['desc']}</div>
                <div class="movie-meta">🗓️ {m['day']} ({m['date']}) | ⏰ {m['time']}</div>
                <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים ל-{m['title']}</a>
            </div>
        """, unsafe_allow_html=True)
