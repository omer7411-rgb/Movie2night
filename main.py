import streamlit as st
import asyncio
import re
from playwright.async_api import async_playwright
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# הגדרות עמוד
st.set_page_config(page_title="קולנוע יפו - לוח הקרנות", page_icon="🎬", layout="wide")

# עיצוב גרפי רספונסיבי (מותאם למחשב ולנייד)
st.markdown("""
    <style>
    /* רקע כללי */
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* כרטיס סרט רספונסיבי */
    .movie-card {
        background: #111418; 
        border-radius: 12px; 
        margin-bottom: 25px;
        border: 1px solid #30363d; 
        overflow: hidden; 
        direction: rtl;
        display: flex; 
        flex-direction: row-reverse; /* ברירת מחדל למחשב: תמונה בצד */
        min-height: 260px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    .movie-img { 
        width: 220px; 
        min-width: 220px; 
        height: auto;
        object-fit: cover; 
        border-left: 1px solid #30363d; 
    }

    .movie-content { 
        padding: 24px; 
        flex-grow: 1; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between; 
        text-align: right;
    }

    .movie-title { 
        color: #f84444; 
        font-size: 1.8rem; 
        font-weight: 900; 
        margin: 0; 
        line-height: 1.1; 
    }

    .movie-meta { 
        color: #8b949e; 
        font-size: 1.1rem; 
        font-weight: bold; 
        margin-top: 10px; 
    }

    /* כפתור רכישה */
    .buy-container { margin-top: 15px; }
    .buy-btn {
        display: inline-block; 
        background-color: #f84444 !important; 
        color: white !important;
        padding: 12px 35px; 
        border-radius: 8px; 
        text-decoration: none !important; 
        font-weight: bold; 
        font-size: 1.1rem; 
        border: none; 
        transition: 0.3s;
        text-align: center;
    }
    .buy-btn:hover { background-color: #ff5f5f !important; transform: scale(1.02); }

    /* --- התאמה לנייד (Media Query) --- */
    @media (max-width: 768px) {
        .movie-card {
            flex-direction: column; /* תמונה מעל הטקסט בנייד */
            height: auto;
            min-height: unset;
        }
        
        .movie-img {
            width: 100%;
            height: 250px;
            min-width: unset;
            border-left: none;
            border-bottom: 1px solid #30363d;
        }

        .movie-title {
            font-size: 1.5rem;
        }

        .movie-content {
            padding: 15px;
        }

        .buy-btn {
            display: block; /* הכפתור יתפרס על כל הרוחב בנייד */
            width: 100%;
            padding: 12px 0;
        }
    }

    /* עיצוב טאבים */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { font-size: 1.2rem; color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #f84444 !important; border-bottom-color: #f84444 !important; }
    </style>
    """, unsafe_allow_html=True)

async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            status_placeholder.info("מתחבר לאתר קולנוע יפו...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            
            for i in range(10):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.6)
                status_placeholder.text(f"סורק את הלוח... ({i+1}/10)")

            movies_data = await page.evaluate('''() => {
                const res = [];
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

            seen = set()
            for m in movies_data:
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
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
    return results

# ניהול מצב
if "movies" not in st.session_state:
    st.session_state.movies = None

st.title("🎬 קולנוע יפו - לוח הקרנות")

if st.session_state.movies is None:
    if st.button("🚀 טען את כל ההקרנות", type="primary", use_container_width=True):
        msg = st.empty()
        st.session_state.movies = asyncio.run(scrape_full_board(msg))
        st.rerun()
else:
    # סרגל צד (Sidebar)
    with st.sidebar:
        st.header("🔍 חיפוש וסינון")
        all_titles = ["הכל"] + sorted(list(set(m['title'] for m in st.session_state.movies)))
        movie_filter = st.selectbox("חפש שם סרט:", all_titles)
        
        st.divider()
        if st.button("🔄 עדכן נתונים", use_container_width=True):
            st.session_state.movies = None
            st.rerun()

    # סינון תוצאות
    f = st.session_state.movies
    if movie_filter != "הכל": f = [m for m in f if m['title'] == movie_filter]
    
    t1, t2 = st.tabs(["📋 רשימת הקרנות", "📅 לוח שנה"])
    
    with t1:
        st.write(f"נמצאו {len(f)} הקרנות")
        for m in f:
            st.markdown(f"""
                <div class="movie-card">
                    <img src="{m['img']}" class="movie-img">
                    <div class="movie-content">
                        <div>
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">יום {m['day_name']} | {m['date_str']} | בשעה {m['time']}</div>
                        </div>
                        <div class="buy-container">
                            <a href="{m['url']}" target="_blank" class="buy-btn">🎟️ רכישת כרטיסים</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with t2:
        calendar_events = [{"title": m['title'], "start": m['iso'], "url": m['url'], "color": "#f84444"} for m in f]
        calendar(events=calendar_events, options={
            "initialDate": "2026-03-01",
            "locale": "he",
            "direction": "rtl",
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}
        })
