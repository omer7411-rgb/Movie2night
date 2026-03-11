import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

# הגדרות עמוד
st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת (למקרה שהסביבה מתאפסת)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

st.markdown("""
    <style>
    .movie-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border-right: 5px solid #FF4B4B; margin-bottom: 15px; direction: rtl; }
    h3 { color: #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

async def scrape_cinemas():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()

        # --- 1. קולנוע יפו ---
        try:
            await page.goto("https://www.jaffacinema.com/schedule", timeout=30000)
            items = await page.query_selector_all(".event-item")
            for item in items:
                title = await (await item.query_selector("h3")).inner_text()
                time = await (await item.query_selector(".event-time")).inner_text()
                movies.append({"title": title.strip(), "time": time.strip(), "cinema": "קולנוע יפו", "link": "https://www.jaffacinema.com/schedule"})
        except: pass

        # --- 2. סינמטק תל אביב ---
        try:
            await page.goto("https://www.cinema.co.il/events/", timeout=30000)
            items = await page.query_selector_all(".cinema-event-item")
            for item in items:
                title = await (await item.query_selector(".event-title")).inner_text()
                time = await (await item.query_selector(".event-hour")).inner_text()
                movies.append({"title": title.strip
