import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

# הגדרות עמוד
st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב לוח שנה - שים לב לסגירה של המרכאות למטה
st.markdown("""
    <style>
    .calendar-card {
        background-color: #262730;
        border-radius: 12px;
        border-right: 8px solid #FF4B4B;
        padding: 20px;
        margin-bottom: 15px;
        direction: rtl;
        text-align: right;
    }
    .date-header {
        background-color: #FF4B4B;
        color: white;
        padding: 8px 20px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 20px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .movie-title { font-size: 1.5rem; font-weight: bold; margin: 5px 0; color: white; }
    .time-label { color: #FF4B4B; font-size: 1.2rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

async def get_jaffa_calendar():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 1000})
        page = await context.new_page()
        try:
            url = "https://www.jaffacinema.com/schedule"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)

            elements = await page.query_selector_all("span, p, h3")
            
            temp_date = "הקרנות קרובות"
            days = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "שבת", "יום ראשון"]
            
            for i in range(len(elements)):
                text = (await elements[i].inner_text()).strip()
                if not text: continue
                
                if any(d in text for d in days):
                    temp_date = text
                elif ":" in text and len(text) <= 5:
                    if i + 1 < len(elements):
                        movie_name = (await elements[i+1].inner_text()).strip()
                        if len(movie_name) > 2 and "הזמן" not in movie_name and "כרטיסים" not in movie_name:
                            movies.append({
                                "date": temp_date,
                                "time": text,
                                "title": movie_name
                            })
        except Exception as e:
            st.error(f"שגיאה בסריקה: {e}")
        finally:
            await browser.close()
    return movies

st.title("📅 לוח ההקרנות של קולנוע יפו")

if st.button("🔄 טען לוח הקרנות מעודכן", type="primary"):
    with st.spinner("מתחבר לאתר ובונה את הלוח..."):
        results = asyncio.run(get_jaffa_calendar())
        st.session_state["jaffa_data"] = results

if "jaffa_data" in st.session_state:
    if not st.session_state["jaffa_data"]:
        st.warning("לא נמצאו סרטים. נסה לרענן.")
    else:
        current_day = ""
        for m in st.session_state["jaffa_data"]:
            if m['date'] != current_day:
                st.markdown(f'<div class="date-header">{m["date"]}</div>', unsafe_allow_html=True)
                current_day = m['date']
            
            st.markdown(f"""
                <div class="calendar-card">
                    <div class="time-label">⏰ {m['time']}</div>
                    <div class="movie-title">{m['title']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("🎟️ הזמנת כרטיס", "https://www.jaffacinema.com/schedule")
            with col2:
                g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&location=קולנוע יפו"
                st.link_button("📅 הוספה ליומן", g_url)
