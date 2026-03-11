
import streamlit as st
import asyncio
import re
import json
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הלוח המלא", page_icon="🎬", layout="wide")

# עיצוב Dark Cinema
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 30px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    .movie-img { width: 220px; min-width: 220px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 25px; flex-grow: 1; }
    .movie-title { color: #f84444; font-size: 2.2rem; font-weight: 900; margin: 0; }
    .movie-desc { color: #ced4da; font-size: 1.1rem; margin-top: 12px; line-height: 1.6; }
    .movie-meta { color: #8b949e; margin-top: 15px; font-weight: bold; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 12px 30px; border-radius: 8px; font-weight: bold; text-decoration: none; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_data_deep_scan(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            status.write("🌐 מתחבר לליבת האתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה מהירה כדי "לעורר" את כל הקונטיינרים
            status.write("🔎 מחלץ נתונים מכל חלקי הדף...")
            for _ in range(5):
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1)

            # אסטרטגיה: מחפשים כל אלמנט שמכיל את המבנה של תאריך/שעה, ללא קשר למיקום שלו
            movies_raw = await page.evaluate('''() => {
                const items = [];
                // מחפשים את כל הקישורים לרכישה - הם העוגן הכי חזק שלנו
                const links = Array.from(document.querySelectorAll('a[href*="calendar"], a[href*="tickets"]'));
                
                links.forEach(link => {
                    // מוצאים את האבא המשותף הכי קרוב שמכיל גם טקסט וגם תמונה
                    let parent = link.parentElement;
                    while (parent && parent.innerText.length < 100 && parent.tagName !== 'SECTION') {
                        parent = parent.parentElement;
                    }
                    
                    if (parent) {
                        const text = parent.innerText;
                        const img = parent.querySelector('img');
                        items.push({
                            text: text,
                            url: link.href,
                            img: img ? img.src : ""
                        });
                    }
                });
                return items;
            }''')

            seen = set()
            for m in movies_raw:
                # חיפוש תאריך ושעה בטקסט שחולץ
                match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['text'])
                if match:
                    # חילוץ כותרת: השורה הראשונה או הטקסט הקצר והבולט ביותר
                    lines = [l.strip() for l in m['text'].split('\n') if len(l.strip()) > 1]
                    title = lines[0] if lines else "סרט ללא שם"
                    
                    # ניקוי כותרת אם היא נתפסה כ"לרכישת כרטיסים"
                    if "לרכישת" in title or len(title) > 50:
                        title = next((l for l in lines if 2 < len(l) < 40 and "/" not in l and ":" not in l), title)

                    uid = f"{title}-{match.group(3)}-{match.group(1)}"
                    if uid not in seen and "כרטיסים" not in title:
                        results.append({
                            "title": title,
                            "desc": next((l for l in lines if len(l) > 50), ""),
                            "time": match.group(3),
                            "date": match.group(1),
                            "day": match.group(2),
                            "url": m['url'],
                            "img": m['img'],
                            "iso": f"2026-{match.group(1).split('/')[1].zfill(2)}-{match.group(1).split('/')[0].zfill(2)}T{match.group(3)}:00"
                        })
                        seen.add(uid)
            
        finally:
            await browser.close()
    return results

st.title("🎬 קולנוע יפו - הלוח המלא (Deep Scan)")
status_msg = st.empty()

if st.button("🚀 בצע סריקה עמוקה", type="primary"):
    with st.spinner("חודר דרך שכבות האתר..."):
        st.session_state.movies = asyncio.run(get_cinema_data_deep_scan(status_msg))
        status_msg.success(f"נמצאו {len(st.session_state.movies)} סרטים!")

if "movies" in st.session_state and st.session_state.movies:
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    st.divider()
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/220x330?text=Cinema+Jaffa'}" class="movie-img">
                <div class="movie-content">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-desc">{m['desc']}</div>
                    <div class="movie-meta">📅 {m['day']} {m['date']} | ⏰ שעה: {m['time']}</div>
                    <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ כרטיסים</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
