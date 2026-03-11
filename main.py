import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar

st.set_page_config(page_title="קולנוע יפו - סדר בלוח", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 15px; margin-bottom: 30px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; min-height: 250px;
    }
    .movie-img { width: 200px; min-width: 200px; object-fit: cover; border-left: 1px solid #30363d; background: #1a1d23; }
    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; line-height: 1.2; }
    .movie-desc { color: #ced4da; font-size: 0.95rem; margin-top: 10px; line-height: 1.4; opacity: 0.9; }
    .movie-meta { color: #8b949e; margin-top: 15px; font-size: 1rem; border-top: 1px solid #2d3139; padding-top: 10px; }
    .buy-btn {
        display: inline-block; background: #f84444 !important; color: white !important;
        padding: 8px 20px; border-radius: 6px; text-decoration: none; margin-top: 15px;
        font-weight: bold; width: fit-content;
    }
    @media (max-width: 768px) {
        .movie-card { flex-direction: column; }
        .movie-img { width: 100%; height: 220px; border-left: none; border-bottom: 1px solid #30363d; }
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_organized_cinema(status):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = await context.new_page()
        
        try:
            status.write("🌐 מתחבר לקולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            await asyncio.sleep(5)
            
            # גלילה יסודית לטעינת כל ה-Lazy Loading
            status.write("📜 סורק וטוען את כל ההקרנות...")
            last_h = 0
            for _ in range(12):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(1.2)
                curr_h = await page.evaluate("document.body.scrollHeight")
                if curr_h == last_h: break
                last_h = curr_h

            # לוגיקת "עוגן": מוצאים כפתורי רכישה ומנתחים את הסביבה הקרובה שלהם
            movies_data = await page.evaluate('''() => {
                const items = [];
                // מוצאים את כל כפתורי הרכישה
                const buttons = Array.from(document.querySelectorAll('a'))
                                     .filter(a => a.innerText.includes('לרכישת') || a.href.includes('calendar'));

                buttons.forEach(btn => {
                    // מוצאים את הקונטיינר הכי קרוב שעוטף את כל הסרט
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    
                    // מציאת כותרת: מחפשים את הטקסט הכי גדול בתוך הקונטיינר הזה בלבד
                    let title = "";
                    let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 60 && !txt.includes('/') && !txt.includes(':') && !txt.includes('לרכישת')) {
                            maxFS = fs;
                            title = txt;
                        }
                    });

                    // מציאת תמונה בתוך אותו קונטיינר
                    const img = container.querySelector('img');
                    
                    // מציאת תיאור (הטקסט הכי ארוך בבלוק)
                    const desc = Array.from(container.querySelectorAll('p, span'))
                                     .map(el => el.innerText.trim())
                                     .sort((a, b) => b.length - a.length)[0] || "";

                    if (title && title !== "קרא עוד") {
                        items.push({
                            title: title,
                            desc: desc.length > 200 ? desc.substring(0, 200) + '...' : desc,
                            url: btn.href,
                            img: img ? img.src : "",
                            fullText: container.innerText
                        });
                    }
                });
                return items;
            }''')

            seen = set()
            for m in movies_data:
                # חילוץ זמן מדויק מהטקסט של אותו בלוק
                time_match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
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

st.title("🎬 לוח הקרנות קולנוע יפו - מסודר")
status_msg = st.empty()

if st.button("🔄 סרוק מחדש וסדר כותרות", type="primary"):
    st.session_state.movies = asyncio.run(scrape_organized_cinema(status_msg))
    status_msg.success(f"נמצאו {len(st.session_state.movies)} סרטים מסודרים!")

if "movies" in st.session_state and st.session_state.movies:
    calendar(events=[{"title": m['title'], "start": m['iso'], "backgroundColor": "#f84444"} for m in st.session_state.movies], options={"direction": "rtl"})
    st.divider()
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <img src="{m['img'] if m['img'] else 'https://via.placeholder.com/200x300?text=Poster'}" class="movie-img">
                <div class="movie-content">
                    <div class="movie-title">{m['title']}</div>
                    <div class="movie-desc">{m['desc']}</div>
                    <div class="movie-meta">🗓️ {m['date']} | ⏰ {m['time']}</div>
                    <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ הזמנת כרטיסים</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
