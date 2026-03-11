import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

# הגדרות עמוד
st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

st.markdown("""
    <style>
    .movie-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border-right: 5px solid #FF4B4B; margin-bottom: 15px; direction: rtl; text-align: right; }
    h3 { color: #FF4B4B; margin: 0; }
    .info { color: #cccccc; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# הגדרות האתרים לסריקה
CINEMAS_TO_SCAN = [
    {"name": "קולנוע יפו", "url": "https://www.jaffacinema.com/schedule", "container": ".event-item", "title": "h3", "time": ".event-time"},
    {"name": "סינמטק תל אביב", "url": "https://www.cinema.co.il/events/", "container": ".cinema-event-item", "title": ".event-title", "time": ".event-hour"},
    {"name": "סינמטק ירושלים", "url": "https://jer-cin.org.il/he/program", "container": ".program-item", "title": ".title", "time": ".time"},
    {"name": "קולנוע לב סמדר", "url": "https://www.lev.co.il/cinema/smadar/", "container": ".movie-performance-item", "title": ".movie-name", "time": ".performance-time"}
]

async def scrape_all():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await context.new_page()

        for cinema in CINEMAS_TO_SCAN:
            try:
                await page.goto(cinema["url"], timeout=30000)
                # מחכה קצת שהתוכן ייטען
                await page.wait_for_timeout(2000)
                items = await page.query_selector_all(cinema["container"])
                
                for item in items:
                    title_el = await item.query_selector(cinema["title"])
                    time_el = await item.query_selector(cinema["time"])
                    if title_el and time_el:
                        t = await title_el.inner_text()
                        tm = await time_el.inner_text()
                        movies.append({
                            "title": t.strip(),
                            "time": tm.strip(),
                            "cinema": cinema["name"],
                            "link": cinema["url"]
                        })
            except Exception as e:
                print(f"Error scanning {cinema['name']}: {e}")
                continue

        await browser.close()
    return movies

st.title("🎬 Movie2Night")
st.subheader("לוח הקרנות מאוחד - יפו, תל אביב וירושלים")

if st.button("🔍 סרוק בתי קולנוע עכשיו", type="primary"):
    with st.spinner("אוסף נתונים מהאתרים..."):
        st.session_state.all_movies = asyncio.run(scrape_all())

if "all_movies" in st.session_state:
    if not st.session_state.all_movies:
        st.warning("לא נמצאו סרטים כרגע.")
    else:
        for m in st.session_state.all_movies:
            st.markdown(f"""
                <div class="movie-card">
                    <h3>{m['title']}</h3>
                    <div class="info">📍 <b>{m['cinema']}</b> | ⏰ {m['time']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.link_button("🎟️ כרטיסים", m['link'], use_container_width=True)
            with c2:
                g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&details=הקרנה ב{m['cinema']}&location={m['cinema']}"
                st.link_button("📅 ליומן", g_url, use_container_width=True)
            st.write("")
