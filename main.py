import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - גרסה סופית", page_icon="🎬", layout="wide")

# עיצוב לילה נקי
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 25px;
        border: 1px solid #2d3139; padding: 20px; direction: rtl;
    }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin-bottom: 10px; }
    .movie-desc { color: #ced4da; font-size: 1rem; margin-bottom: 15px; line-height: 1.4; }
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_data(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status.write("🌐 טוען את האתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה לטעינת כל התוכן
            for _ in range(5):
                await page.keyboard.press("PageDown")
                await asyncio.sleep(1)

            # אסטרטגיה: מוצאים כפתורים ומחפשים כותרות אמיתיות מסביבם
            movies = await page.evaluate('''() => {
                const data = [];
                const buttons = Array.from(document.querySelectorAll('a'))
                                     .filter(a => a.innerText.includes('לרכישת') || a.href.includes('calendar'));

                buttons.forEach(btn => {
                    let container = btn.closest('section') || btn.parentElement.parentElement.parentElement;
                    const fullText = container.innerText;
                    
                    let bestTitle = "";
                    let maxFS = 0;
                    
                    container.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        const fs = parseFloat(style.fontSize);
                        const txt = el.innerText.trim();
                        
                        // סינון קשוח: לא כפתור, לא תאריך, לא ארוך מדי
                        if (fs > maxFS && 
                            txt.length > 1 && txt.length < 40 && 
                            !txt.includes('/') && !txt.includes(':') && 
                            !txt.includes('לרכישת') && !txt.includes('כרטיסים')) {
                            maxFS = fs;
                            bestTitle = txt;
                        }
                    });

                    if (bestTitle && bestTitle !== "קרא עוד") {
                        data.push({ title: bestTitle, raw: fullText, url: btn.href });
                    }
                });
                return data;
            }''')

            seen = set()
            for m in movies:
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['raw'])
                if time_match:
                    unique_id = f"{m['title']}-{time_match.group(3)}"
                    if unique_id not in seen:
                        # חילוץ תיאור
                        lines = m['raw'].split('\n')
                        desc = next((l.strip() for l in lines if len(l.strip()) > 50 and m['title'] not in l), "")
                        
                        results.append({
                            "title": m['title'], "desc": desc, "url": m['url'],
                            "time": time_match.group(3), "date": time_match.group(1), "day": time_match.group(2),
                            "iso": f"2026-{time_match.group(1).split('/')[1].zfill(2)}-{time_match.group(1).split('/')[0].zfill(2)}T{time_match.group(3)}:00"
                        })
                        seen.add(unique_id)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח הקרנות קולנוע יפו")
status_msg = st.empty()

if st.button("🔍 סרוק את כל הסרטים", type="primary"):
    st.session_state.movies = asyncio.run(get_cinema_data(status_msg))
    status_msg.success(f"נמצאו {len(st.session_state.movies)} סרטים!")

if "movies" in st.session_state:
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
