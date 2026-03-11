import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

st.set_page_config(page_title="קולנוע יפו - הגרסה המלאה", page_icon="🎬", layout="wide")

# CSS מותאם לנייד ולעיצוב נקי
st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט רספונסיבי */
    .movie-card {
        background: #111418; border-radius: 12px; margin-bottom: 25px;
        border: 1px solid #30363d; overflow: hidden; direction: rtl;
        display: flex; flex-direction: row-reverse;
    }
    
    @media (min-width: 768px) {
        .movie-card { height: 260px; }
        .movie-img { width: 220px; min-width: 220px; height: 100%; object-fit: cover; border-left: 1px solid #30363d; }
    }
    
    @media (max-width: 767px) {
        .movie-card { flex-direction: column; height: auto; }
        .movie-img { width: 100%; height: 230px; border-bottom: 1px solid #30363d; }
    }

    .movie-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
    .movie-title { color: #f84444; font-size: 1.8rem; font-weight: 900; margin: 0; line-height: 1.1; }
    .movie-meta { color: #8b949e; font-size: 1.2rem; font-weight: bold; margin-top: 5px; }
    
    .buy-btn {
        display: block; background-color: #f84444 !important; color: white !important;
        padding: 12px; border-radius: 8px; text-decoration: none !important; 
        font-weight: bold; text-align: center; margin-top: 15px; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

async def scrape_deep_search(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # שימוש ב-Viewport גדול כדי לתפוס את כל התוכן
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000})
        page = await context.new_page()
        try:
            status_placeholder.info("מתחבר לסורק העמוק של קולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה מבוקרת לטעינת כל ה-DOM
            for i in range(12):
                await page.mouse.wheel(0, 1200)
                await asyncio.sleep(0.8)
                status_placeholder.text(f"שואב נתונים... שלב {i+1}/12")

            # שיטת הסריקה העמוקה שמחפשת לפי מבנה הנתונים
            movies_data = await page.evaluate('''() => {
                const list = [];
                // מוצאים את כל הקונטיינרים של Wix שכוללים כפתור רכישה
                const items = Array.from(document.querySelectorAll('div[data-mesh-id]'))
                    .filter(el => el.innerText.includes('לרכישת'));
                
                items.forEach(item => {
                    const img = item.querySelector('img');
                    const link = item.querySelector('a[href*="tickets"], a[href*="event-details"]');
                    
                    // מחלצים כותרת (הטקסט הכי גדול בקונטיינר)
                    let title = ""; let maxFS = 0;
                    item.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 2 && txt.length < 50 && !txt.includes(':') && !txt.includes('/')) {
                            maxFS = fs; title = txt;
                        }
                    });

                    if (title && link) {
                        list.push({
                            title,
                            url: link.href,
                            img: img ? img.src : "",
                            text: item.innerText
                        });
                    }
                });
                return list;
            }''')

            seen = set()
            for m in movies_data:
                # חילוץ תאריך ושעה בעזרת Regex חזק
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['text'])
                if match:
                    d, month = match.group(1).split('/')
                    date_obj = datetime(2026, int(month), int(d))
                    uid = f"{m['title']}-{match.group(2)}-{match.group(1)}"
                    if uid not in seen:
                        results.append({
                            "title": m['title'], "url": m['url'], "img": m['img'],
                            "time": match.group(2), "date_str": f"{d.zfill(2)}/{month.zfill(2)}",
                            "day_name": days_map[date_obj.weekday()], "dt": date_obj,
                            "iso": f"2026-{month.zfill(2)}-{d.zfill(2)}T{match.group(2)}:00"
                        })
                        seen.add(uid)
        finally: await browser.close()
    return sorted(results, key=lambda x: x['dt'])

# ניהול מצב
if "movies" not in st.session_state: st.session_state.movies = None
if "view" not in st.session_state: st.session_state.view = "רשימה"

st.title("🎬 קולנוע יפו - לוח הקרנות")

if st.session_state.movies is None:
    if st.button("🔍 סרוק את כל הסרטים", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_deep_search(msg))
        st.rerun()
else:
    with st.sidebar:
        st.header("🔍 חיפוש")
        titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_sel = st.selectbox("בחר סרט משלוף:", titles)
        
        st.divider()
        if st.button("📅 הצג בלוח שנה" if st.session_state.view == "רשימה" else "📋 הצג כרשימה", use_container_width=True):
            st.session_state.view = "חודש" if st.session_state.view == "רשימה" else "רשימה"
            st.rerun()
        
        st.divider()
        # ייצוא ליומן
        ical = "BEGIN:VCALENDAR\nVERSION:2.0\n"
        for m in st.session_state.movies:
            ical += f"BEGIN:VEVENT\nSUMMARY:{m['title']}\nDTSTART:{m['iso'].replace('-','').replace(':','')}\nURL:{m['url']}\nEND:VEVENT\n"
        ical += "END:VCALENDAR"
        st.download_button("🗓️ הוסף ליומן גוגל", ical, "jaffa.ics", use_container_width=True)
        
        if st.button("🔄 סריקה חדשה", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # פילטור
    f = [m for m in st.session_state.movies if movie_sel == "הכל" or m['title'] == movie_sel]

    if st.session_state.view == "רשימה":
        st.subheader(f"נמצאו {len(f)} הקרנות")
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | {m['time']}</div>
                        </div>
                        <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ רכישת כרטיסים</a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.subheader("מרץ 2026")
        evs = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=evs, options={"initialDate": "2026-03-01", "locale": "he", "direction": "rtl", "initialView": "dayGridMonth"})
