import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - סריקה חכמה", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 25px;
        border: 1px solid #2d3139; padding: 25px; direction: rtl;
    }
    .movie-title { color: #f84444; font-size: 2rem; font-weight: 900; margin-bottom: 10px; }
    .movie-desc { color: #ced4da; font-size: 1.1rem; margin-bottom: 20px; line-height: 1.5; }
    .buy-btn {
        display: block; background: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; font-weight: bold; text-decoration: none; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

async def get_cinema_data_pro(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status.write("🌐 מתחבר לקולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="domcontentloaded")
            
            # גלילה איטית ואקטיבית לטעינת כל הרכיבים
            status.write("📜 סורק את כל עומק הדף...")
            for _ in range(12):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(1)

            # לוגיקת AI: איסוף כל האלמנטים הרלוונטיים בדף וחיבורם לפי קירבה
            movies = await page.evaluate('''() => {
                const allData = [];
                // מוצאים את כל הבלוקים שיש להם מבנה של הקרנה (זמן + קישור)
                const sections = Array.from(document.querySelectorAll('section, div[data-mesh-id]'));
                
                sections.forEach(section => {
                    const text = section.innerText || "";
                    // חיפוש דפוס של תאריך ושעה בתוך הטקסט
                    const timePattern = /(\d{1,2}\/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})/;
                    if (timePattern.test(text)) {
                        const link = section.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        if (link) {
                            let title = "";
                            let maxFS = 0;
                            
                            // מציאת הכותרת הכי גדולה בבלוק שאינה טקסט טכני
                            section.querySelectorAll('*').forEach(el => {
                                const fs = parseFloat(window.getComputedStyle(el).fontSize);
                                const content = el.innerText.trim();
                                if (fs > maxFS && content.length > 1 && content.length < 50 && 
                                    !content.includes('/') && !content.includes(':') && 
                                    !content.includes('לרכישת')) {
                                    maxFS = fs;
                                    title = content;
                                }
                            });

                            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 40);
                            const desc = lines.find(l => l !== title && !l.includes('/')) || "";

                            if (title && title !== "קרא עוד") {
                                allData.push({ title, desc, url: link.href, raw: text });
                            }
                        }
                    }
                });
                return allData;
            }''')

            # ניקוי כפילויות חכם
            seen = set()
            for m in movies:
                match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})', m['raw'])
                if match:
                    # מזהה ייחודי משולב של שם וזמן למניעת כפילויות
                    uid = f"{m['title']}-{match.group(3)}-{match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "desc": m['desc'], "url": m['url'],
                            "time": match.group(3), "date": match.group(1), "day": match.group(2),
                            "iso": f"2026-{match.group(1).split('/')[1].zfill(2)}-{match.group(1).split('/')[0].zfill(2)}T{match.group(3)}:00"
                        })
                        seen.add(uid)
        finally:
            await browser.close()
    return results

st.title("🎬 קולנוע יפו - לוח הקרנות")
status_placeholder = st.empty()

if st.button("🔍 סריקה חכמה של כל האתר", type="primary"):
    st.session_state.movies = asyncio.run(get_cinema_data_pro(status_placeholder))
    status_placeholder.success(f"נמצאו {len(st.session_state.movies)} הקרנות שונות!")

if "movies" in st.session_state and st.session_state.movies:
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
