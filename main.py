import streamlit as st
import asyncio
import os
import json
from playwright.async_api import async_playwright

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

st.set_page_config(page_title="Movie2Night", page_icon="🎬")

async def scrape_all():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # דוגמה לקולנוע יפו
        try:
            await page.goto("https://www.jaffacinema.com/schedule", timeout=60000)
            items = await page.query_selector_all(".event-item")
            for item in items:
                title = await (await item.query_selector("h3")).inner_text()
                time = await (await item.query_selector(".event-time")).inner_text()
                movies.append({"title": title, "time": time, "cinema": "קולנוע יפו", "link": "https://www.jaffacinema.com/schedule"})
        except Exception as e:
            st.error(f"שגיאה בסריקה: {e}")
            
        await browser.close()
    return movies

st.title("🎬 הסרטים שלי הלילה")

if st.button("סרוק בתי קולנוע"):
    with st.spinner("מחפש סרטים..."):
        st.session_state.movies = asyncio.run(scrape_all())

if "movies" in st.session_state:
    for m in st.session_state.movies:
        with st.container():
            st.write(f"### {m['title']}")
            st.write(f"📍 {m['cinema']} | ⏰ {m['time']}")
            col1, col2 = st.columns(2)
            col1.link_button("🎟️ הזמן כרטיס", m['link'])
            google_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&location={m['cinema']}"
            col2.link_button("📅 הוסף ליומן", google_url)
            st.divider()
