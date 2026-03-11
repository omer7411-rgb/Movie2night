import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta
import urllib.parse
from collections import defaultdict

# 1. הגדרות עמוד ועיצוב (ללא שינוי דרמטי)
st.set_page_config(page_title="קולנוע יפו - כל ההקרנות", page_icon="🎬", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse; min-height: 250px;
    }
    .movie-img { width: 200px; min-width: 200px; object-fit: cover; }
    .movie-content { padding: 20px; flex-grow: 1; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; }
    .showtimes-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
    .showtime-chip {
        background: #1f242b; border: 1px solid #484f58; border-radius: 6px;
        padding: 6px 10px; text-decoration: none !important; color: white !important;
        text-align: center; min-width: 80px;
    }
    .chip-date { font-size: 0.75rem; display: block; color: #8b949e; }
    .chip-time { font-size: 1rem; font-weight: bold; color: #f84444; }
    </style>
    """, unsafe_allow_html=True)

# 2. פונקציית הסריקה עם לוגיקת "לחץ להצגת עוד"
async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("מתחבר לאתר ומרחיב את כל זמני ההקרנה...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")

            # שלב א': לחיצה על כל כפתורי "עוד זמנים" או דרופדאונים
            # אנחנו מחפשים כפתורים שמכילים טקסט כמו "זמנים נוספים" או אייקון פתיחה
            await page.evaluate('''async () => {
                // גלילה ראשונית לטעינת אלמנטים
                window.scrollBy(0, 2000);
                await new Promise(r => setTimeout(r, 1000));
                
                // מציאת כל הכפתורים שמרחיבים תצוגה (נפוץ ב-Wix/אתרי קולנוע)
                const expandButtons = Array.from(document.querySelectorAll('button, a, span'))
                    .filter(el => {
                        const txt = el.innerText.toLowerCase();
                        return txt.includes('עוד') || txt.includes('מועדים') || txt.includes('more');
                    });
                
                for (let btn of expandButtons) {
                    try { 
                        btn.click(); 
                        await new Promise(r => setTimeout(r, 300)); // המתנה קצרה לפתיחה
                    } catch(e) {}
                }
            }''')

            # שלב ב': איסוף הנתונים אחרי שהכל פתוח
            movies_data = await page.evaluate('''() => {
                const res = [];
                // מחפשים את כל כפתורי הרכישה שקיימים כרגע בדף
                const btns = Array.from(document.querySelectorAll('a')).filter(a => a.innerText.includes('לרכישת'));
                
                btns.forEach(btn => {
                    let container = btn.closest('div[data-mesh-id]') || btn.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    let title = ""; let maxFS = 0;
                    
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 55 && !txt.includes('/') && !txt.includes(':')) {
                            maxFS = fs; title = txt;
                        }
                    });
                    res.push({ title, url: btn.href, img: img ? img.src : "", fullText: container.innerText });
                });
                return res;
            }''')
            
            curr_year = datetime.now().year
            for m in movies_data:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    d, month = match.group(1).split('/')
                    date_obj = datetime(curr_year, int(month), int(d))
                    iso_time = f"{curr_year}-{month.zfill(2)}-{d.zfill(2)}T{match.group(2)}:00"
                    
                    results.append({
                        "title": m['title'], "url": m['url'], "img": m['img'],
                        "time": match.group(2), "date_str": f"{d.zfill(2)}/{month.zfill(2)}",
                        "day_name": days_map[date_obj.weekday()], "dt": date_obj, "iso": iso_time
                    })
        finally: await browser.close()
    return results

# 3. תצוגה (Grouping)
if "movies" not in st.session_state: st.session_state.movies = None

st.title("🎬 לוח הקרנות מלא - קולנוע יפו")

if st.session_state.movies is None:
    if st.button("🚀 סרוק את כל המועדים (כולל כפתורי 'עוד')", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_full_board(msg))
        st.rerun()
else:
    grouped = defaultdict(list)
    for m in st.session_state.movies:
        grouped[m['title']].append(m)

    for title, dates in grouped.items():
        sorted_dates = sorted(dates, key=lambda x: x['dt'])
        st.markdown(f"""
            <div class="movie-card">
                <img src="{sorted_dates[0]['img']}" class="movie-img">
                <div class="movie-content">
                    <div class="movie-title">{title}</div>
                    <div class="showtimes-grid">
                        {''.join([f'<a href="{d["url"]}" target="_blank" class="showtime-chip"><span class="chip-date">{d["day_name"]} {d["date_str"]}</span><span class="chip-time">{d["time"]}</span></a>' for d in sorted_dates])}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if st.button("🔄 סריקה חדשה"):
        st.session_state.movies = None
        st.rerun()
