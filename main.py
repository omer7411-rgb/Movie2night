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
        background: #111418; border-radius: 15px; margin-bottom: 30px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    .movie-img { width: 200px; object-fit: cover; border-left: 1px solid #30363d; }
    .movie-content { padding: 20px; flex-grow: 1; }
    .movie-title { color: #f84444; font-size: 2rem; font-weight: bold; margin: 0; }
    .movie-desc { color: #ced4da; font-size: 1rem; margin-top: 10px; line-height: 1.5; }
    .movie-meta { color: #8b949e; margin-top: 15px; font-weight: bold; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 10px 25px; border-radius: 8px; text-align: center; 
        text-decoration: none; margin-top: 15px; font-weight: bold;
    }
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; }
        .movie-img { width: 100%; height: 250px; border-left: none; border-bottom: 1px solid #30363d; }
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_until_end(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            status.write("🌐 מתחבר לקולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # לולאת גלילה עד לסוף הדף המוחלט
            status.write("📜 מבצע גלילה עמוקה... מחפש את כל הסרטים (זה עשוי לקחת רגע)...")
            last_height = await page.evaluate("document.body.scrollHeight")
            while True:
                await page.mouse.wheel(0, 1500)
                await asyncio.sleep(1.5) # זמן טעינה ל-Wix
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height: # אם הגובה לא השתנה, הגענו לסוף
                    break
                last_height = new_height
                status.write(f"⏳ טוען עוד תוכן... (גובה דף: {new_height} פיקסלים)")

            status.write("🎣 דג פוסטרים ופרטים מכל הלוח...")
            data = await page.evaluate('''() => {
                const movies = [];
                document.querySelectorAll('div, section').forEach(el => {
                    const text = el.innerText || "";
                    const timeMatch = /(\d{1,2}\/\d{1,2}),?\s*(יום\s+\w+|היום)\s*(\d{1,2}:\d{2})/.exec(text);
                    
                    if (timeMatch && text.length < 1500) {
                        const link = el.querySelector('a[href*="calendar"], a[href*="tickets"]');
                        const img = el.querySelector('img'); // ניסיון למצוא תמונה בבלוק
                        
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

if st.button("🚀 סרוק את כל האתר עד הסוף", type="primary"):
    with st.spinner("מבצע סריקה טוטאלית..."):
        st.session_state.movies = asyncio.run(scrape_until_end(msg))
        msg.success(f"משימה הושלמה! נמצאו {len(st.session_state.movies)} סרטים.")

if "movies" in st.session_state and st.session_state.movies:
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    st.divider()
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/200x300?text=No+Poster'}" class="movie-img">
                <div class="movie-content">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-desc">{m['desc']}</div>
                    <div class="movie-meta">📅 {m['date']} | ⏰ {m['time']}</div>
                    <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמנת כרטיסים</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
