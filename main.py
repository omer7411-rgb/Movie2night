import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הלוח המלא", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 20px;
        border: 1px solid #30363d; padding: 20px; direction: rtl;
    }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: bold; }
    .movie-desc { color: #ced4da; font-size: 1rem; margin-top: 8px; }
    .movie-meta { color: #8b949e; margin-top: 10px; font-size: 0.9rem; }
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 10px; border-radius: 6px; text-align: center; text-decoration: none; margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_full_cinema(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # שימוש ב-User Agent של מחשב רגיל כדי למנוע חסימות
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            status.write("🌐 מתחבר לקולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה מורחבת - 15 פעמים כדי להגיע לסוף הדף
            status.write("📜 מבצע גלילה עמוקה לטעינת כל הסרטים...")
            for i in range(15):
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(0.7) # מחכה שהתוכן ייטען
            
            status.write("🎣 אוסף את כל הסרטים מהדף...")
            data = await page.evaluate('''() => {
                const movies = [];
                // סורקים כל אלמנט שיכול להכיל מידע על סרט
                document.querySelectorAll('div, section').forEach(el => {
                    const text = el.innerText || "";
                    const timeMatch = /(\d{1,2}\/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})/.exec(text);
                    
                    // בודקים שהאלמנט לא גדול מדי (כדי לא לקחת את כל האתר בבת אחת)
                    if (timeMatch && text.length < 1200) {
                        const link = el.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        
                        let title = "";
                        let maxFS = 0;
                        el.querySelectorAll('*').forEach(child => {
                            const fs = parseFloat(window.getComputedStyle(child).fontSize);
                            const t = child.innerText.trim();
                            if (fs > maxFS && t.length > 1 && t.length < 50 && !t.includes('/') && !t.includes('לרכישת')) {
                                maxFS = fs;
                                title = t;
                            }
                        });

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

            seen = set()
            for m in data:
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['dateInfo'])
                if time_match:
                    # מזהה ייחודי למניעת כפילויות
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

st.title("🎬 לוח הקרנות מלא - קולנוע יפו")
msg = st.empty()

if st.button("🚀 סרוק את כל הלוח (גלילה עמוקה)", type="primary"):
    with st.spinner("טוען סרטים..."):
        st.session_state.movies = asyncio.run(scrape_full_cinema(msg))
        msg.success(f"הצלחנו! נמצאו {len(st.session_state.movies)} הקרנות.")

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
