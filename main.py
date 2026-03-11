import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - הלוח המלא", page_icon="🎬", layout="wide")

# עיצוב כהה משודרג
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
    .movie-meta { color: #8b949e; margin-top: 15px; font-weight: bold; border-top: 1px solid #2d3139; padding-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 12px 30px; border-radius: 8px; text-align: center; 
        text-decoration: none; margin-top: 20px; font-weight: bold;
    }
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; }
        .movie-img { width: 100%; height: 300px; border-left: none; border-bottom: 1px solid #30363d; }
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_with_patience(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # מדמה מסך גדול מאוד כדי "לתפוס" יותר תוכן בכל פעם
        context = await browser.new_context(viewport={'width': 1920, 'height': 2000})
        page = await context.new_page()
        
        try:
            status.write("🌐 פותח את האתר ומחכה לטעינה ראשונית (10 שניות)...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            await asyncio.sleep(10) # זמן לאתר ה-Wix ה"כבד" להתייצב
            
            status.write("📜 מתחיל גלילה איטית ויסודית עד לסוף הדף...")
            
            curr_pos = 0
            last_height = await page.evaluate("document.body.scrollHeight")
            
            # גלילה בצעדים קטנים של 600 פיקסלים
            while True:
                curr_pos += 600
                await page.mouse.wheel(0, 600)
                await asyncio.sleep(1) # מחכה שכל סרט ייטען ויצוץ
                
                new_height = await page.evaluate("document.body.scrollHeight")
                if curr_pos > new_height and new_height == last_height:
                    # בדיקה נוספת למקרה שהסוף באמת הגיע
                    await asyncio.sleep(3)
                    if (await page.evaluate("document.body.scrollHeight")) == new_height:
                        break
                
                last_height = new_height
                if curr_pos % 3000 == 0:
                    status.write(f"⏳ בתהליך... נסרקו {curr_pos} פיקסלים.")

            status.write("🎣 הסריקה הושלמה. מעבד נתונים ותמונות...")
            data = await page.evaluate('''() => {
                const movies = [];
                document.querySelectorAll('div, section').forEach(el => {
                    const text = el.innerText || "";
                    const timeMatch = /(\d{1,2}\/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})/.exec(text);
                    
                    if (timeMatch && text.length < 1500) {
                        const link = el.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        // מחפשים תמונה - Wix משתמש ב-img בתוך קונטיינרים מורכבים
                        const img = el.querySelector('img');
                        
                        let title = "";
                        let maxFS = 0;
                        el.querySelectorAll('*').forEach(child => {
                            const fs = parseFloat(window.getComputedStyle(child).fontSize);
                            const t = child.innerText.trim();
                            if (fs > maxFS && t.length > 1 && t.length < 60 && !t.includes('/') && !t.includes(':') && !t.includes('לרכישת')) {
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
                                img: img ? img.src : "",
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
                    uid = f"{m['title']}-{time_match.group(2)}-{time_match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "desc": m['desc'], "url": m['url'], "img": m['img'],
                            "time": time_match.group(2), "date": time_match.group(1),
                            "iso": f"2026-{time_match.group(1).split('/')[1].zfill(2)}-{time_match.group(1).split('/')[0].zfill(2)}T{time_match.group(2)}:00"
                        })
                        seen.add(uid)
        finally:
            await browser.close()
    return results

st.title("🎬 לוח הקרנות מלא - קולנוע יפו")
msg = st.empty()

if st.button("🚀 סרוק את כל האתר (גלילה יסודית)", type="primary"):
    with st.spinner("מבצע סריקה עמוקה... נא לא לסגור את הדף"):
        st.session_state.movies = asyncio.run(scrape_with_patience(msg))
        msg.success(f"הצלחנו! נמצאו {len(st.session_state.movies)} סרטים.")

if "movies" in st.session_state and st.session_state.movies:
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    st.divider()
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <img src="{m['img'] if m['img'] and 'static.wixstatic' in m['img'] else 'https://via.placeholder.com/220x330?text=Cinema+Jaffa'}" class="movie-img">
                <div class="movie-content">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-desc">{m['desc']}</div>
                    <div class="movie-meta">📅 תאריך: {m['date']} | ⏰ שעה: {m['time']}</div>
                    <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמנת כרטיסים</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
