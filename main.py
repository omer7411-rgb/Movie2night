import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הגרסה המלאה", page_icon="🍿", layout="wide")

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
        padding: 20px;
    }
    .movie-title { color: #f84444; font-size: 2rem; font-weight: 900; }
    .movie-desc { color: #ced4da; font-size: 1rem; margin-top: 10px; }
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none;
        text-align: center; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_all_movies(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status.write("🌐 מתחבר לאתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה אגרסיבית לטעינת כל הרכיבים
            status.write("📜 טוען את כל הסרטים (גלילה עמוקה)...")
            for _ in range(10):
                await page.keyboard.press("PageDown")
                await asyncio.sleep(0.8)
            
            status.write("⚡ מנתח מבנה ויזואלי...")
            # לוגיקה שסורקת את כל האלמנטים בדף בצורה שטוחה
            raw_movies = await page.evaluate('''() => {
                const data = [];
                // מוצאים את כל כפתורי הרכישה כנקודות עוגן
                const buttons = Array.from(document.querySelectorAll('a'))
                                     .filter(a => a.innerText.includes('לרכישת') || a.href.includes('calendar'));

                return buttons.map(btn => {
                    // לכל כפתור, נחפש טקסטים סביבו (למעלה או למטה)
                    let parent = btn.parentElement;
                    for (let i = 0; i < 10; i++) { // מטפסים עד 10 רמות למעלה למצוא קונטיינר
                        if (parent.innerText.includes('/') && parent.innerText.includes(':')) break;
                        parent = parent.parentElement;
                    }
                    
                    const fullText = parent.innerText;
                    const lines = fullText.split('\\n').map(s => s.trim()).filter(s => s.length > 2);
                    
                    // זיהוי שם סרט לפי גודל פונט בתוך הקונטיינר שנמצא
                    let title = "";
                    let maxFS = 0;
                    parent.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fs > maxFS && el.innerText.length < 50 && !el.innerText.includes('/') && !el.innerText.includes(':')) {
                            maxFS = fs;
                            title = el.innerText.trim();
                        }
                    });

                    return { title, fullText, url: btn.href };
                });
            }''')

            seen_ids = set()
            for m in raw_movies:
                # חילוץ תאריך ושעה
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['fullText'])
                if time_match and m['title'] and m['title'] != "קרא עוד":
                    unique_id = f"{m['title']}-{time_match.group(3)}"
                    if unique_id not in seen_ids:
                        # חילוץ תיאור - השורה הכי ארוכה שלא מכילה תאריך
                        desc_candidates = [l for l in m['fullText'].split('\n') if len(l) > 40 and m['title'] not in l]
                        description = desc_candidates[0] if desc_candidates else ""
                        
                        results.append({
                            "title": m['title'],
                            "desc": description,
                            "time": time_match.group(3),
                            "date": time_match.group(1),
                            "day": time_match.group(2),
                            "url": m['url'],
                            "iso": f"2026-{time_match.group(1).split('/')[1].zfill(2)}-{time_match.group(1).split('/')[0].zfill(2)}T{time_match.group(3)}:00"
                        })
                        seen_ids.add(unique_id)
            
        finally:
            await browser.close()
    return results

st.title("🎬 לוח הקרנות מלא - קולנוע יפו")
msg = st.empty()

if st.button("🔍 סרוק את כל הסרטים", type="primary"):
    with st.spinner("מבצע סריקת עומק..."):
        st.session_state.movies = asyncio.run(get_all_movies(msg))
        msg.success(f"נמצאו {len(st.session_state.movies)} סרטים!")

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
                <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמן כרטיס ל-{m['title']}</a>
            </div>
        """, unsafe_allow_html=True)
