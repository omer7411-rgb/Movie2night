import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב מותאם לנייד
st.markdown("""
    <style>
    .movie-card { background-color: #1e1e1e; padding: 15px; border-radius: 12px; border-right: 4px solid #FF4B4B; margin-bottom: 10px; direction: rtl; text-align: right; }
    h3 { color: #FF4B4B; margin: 0; font-size: 1.2rem; }
    .info { color: #aaaaaa; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# רשימת בתי הקולנוע עם הכתובות המדויקות ביותר
CINEMAS = [
    {"name": "קולנוע יפו", "url": "https://www.jaffacinema.com/schedule", "container": ".event-item", "title": "h3", "time": ".event-time"},
    {"name": "סינמטק תל אביב", "url": "https://www.cinema.co.il/events/", "container": ".cinema-event-item", "title": "h5, .event-title", "time": ".event-hour"},
    {"name": "סינמטק ירושלים", "url": "https://jer-cin.org.il/he/program", "container": ".program-item", "title": ".title", "time": ".time"},
    {"name": "קולנוע לב סמדר", "url": "https://www.lev.co.il/cinema/smadar/", "container": ".movie-performance-item", "title": ".movie-name", "time": ".performance-time"}
]

async def scrape_all():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # יצירת דפדפן שנראה כמו מחשב רגיל בישראל
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="he-IL"
        )
        page = await context.new_page()

        for cinema in CINEMAS:
            try:
                st.write(f"בודק את {cinema['name']}...")
                await page.goto(cinema["url"], timeout=45000, wait_until="networkidle")
                await page.wait_for_timeout(3000) # המתנה לטעינה נוספת
                
                items = await page.query_selector_all(cinema["container"])
                st.write(f"מצאתי {len(items)} אלמנטים פוטנציאליים ב-{cinema['name']}")
                
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
                st.sidebar.error(f"שגיאה ב{cinema['name']}: {str(e)[:50]}")
        
        await browser.close()
    return movies

st.title("🎬 Movie2Night")

if st.button("🔍 סרוק בתי קולנוע עכשיו", type="primary"):
    with st.spinner("מחפש סרטים..."):
        results = asyncio.run(scrape_all())
        st.session_state.all_movies = results

if "all_movies" in st.session_state:
    if not st.session_state.all_movies:
        st.error("הסריקה הסתיימה אך לא חזרו תוצאות. האתרים כנראה חוסמים גישה מהענן.")
    else:
        for m in st.session_state.all_movies:
            st.markdown(f'<div class="movie-card"><h3>{m["title"]}</h3><div class="info">{m["cinema"]} | {m["time"]}</div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.link_button("🎟️ כרטיסים", m['link'], use_container_width=True)
            g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&details=הקרנה ב{m['cinema']}&location={m['cinema']}"
            c2.link_button("📅 ליומן", g_url, use_container_width=True)
