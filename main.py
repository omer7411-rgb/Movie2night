import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הלוח המלא", page_icon="🎬", layout="wide")

# עיצוב כהה עם כרטיסיות בולטות
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; padding: 20px; direction: rtl;
    }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: bold; }
    .movie-desc { color: #ced4da; font-size: 1rem; margin-top: 8px; }
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 10px; border-radius: 6px; text-align: center; text-decoration: none; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_all_cinema_content(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status.write("🌐 פותח את האתר...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה מסיבית כדי לוודא שהכל נטען
            status.write("📜 גולל וטוען את כל הלוח...")
            for _ in range(10):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(0.5)

            # לוגיקה "רעבה": מחפשים כל אלמנט שיש בו תאריך ושעה
            data = await page.evaluate('''() => {
                const movies = [];
                // סורקים את כל הדיבים שיש להם טקסט משמעותי
                document.querySelectorAll('div').forEach(div => {
                    const text = div.innerText || "";
                    const timeMatch = /(\d{1,2}\/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})/.exec(text);
                    
                    if (timeMatch && text.length < 1000) { // מסננים דיבים ענקיים מדי שכוללים הכל
                        // מחפשים לינק בתוך הדיב או קרוב אליו
                        const link = div.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        
                        // מוצאים את הכותרת בתוך הדיב (הטקסט הכי גדול)
                        let title = "";
                        let maxFS = 0;
                        div.querySelectorAll('*').forEach(el => {
                            const fs = parseFloat(window.getComputedStyle(el).fontSize);
                            const t = el.innerText.trim();
                            if (fs > maxFS && t.length > 1 && t.length < 50 && !t.includes('/') && !t.includes('לרכישת')) {
                                maxFS = fs;
                                title = t;
                            }
                        });

                        // תיאור - השורה הכי ארוכה
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 40);
                        const desc = lines.find(l => l !== title && !l.includes('/')) || "";

                        if (title && title !== "קרא עוד") {
                            movies.push({
                                title: title,
                                desc: desc,
                                url: link ? link.href : "https://www.jaffacinema.com/",
                                raw: text,
                                dateInfo: timeMatch[0]
                            });
                        }
                    }
                });
                return movies;
            }''')

            # ניקוי כפילויות פשוט על בסיס שם וזמן
            status.write(f"🔍 מעבד {len(data)} ממצאים...")
            seen = set()
            for m in data:
                # חילוץ נקי של הזמן מהמחרוזת שמצאנו
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['dateInfo'])
                if time_match:
                    uid = f"{m['title']}-{time_match.group(2)}-{time_match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "desc": m['desc'], "url": m['url'],
                            "time": time_match.group(2), "date": time_match.group(1),
                            "iso": f"2026-{time_match.group(1).split('/')[1].zfill(2)}-{time_match.group(1).split('/')[0].zfill(2)}T{time_match.group(2)}:00"
                        })
                        seen.add(uid)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח ההקרנות המלא - קולנוע יפו")
status_box = st.empty()

if st.button("🚀 סרוק את כל הסרטים עכשיו", type="primary"):
    st.session_state.movies = asyncio.run(scrape_all_cinema_content(status_box))
    status_box.success(f"הצלחנו! נמצאו {len(st.session_state.movies)} סרטים.")

if "movies" in st.session_state and st.session_state.movies:
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    st.divider()
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <div class="movie-title">{m['title']}</div>
                <div class="movie-desc">{m['desc']}</div>
                <div class="movie-meta">⏰ שעה: {m['time']} | 📅 תאריך: {m['date']}</div>
                <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ לרכישת כרטיסים</a>
            </div>
        """, unsafe_allow_html=True)
