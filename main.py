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
    .movie-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border-right: 5px solid #FF4B4B; margin-bottom: 15px; direction: rtl; text-align: right; }
    h3 { color: #FF4B4B; margin: 0; }
    .info { color: #cccccc; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

async def scrape_cinemas():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await context.new_page()

        # --- 1. קולנוע יפו ---
        try:
            await page.goto("https://www.jaffacinema.com/schedule", timeout=30000)
            items = await page.query_selector_all(".event-item")
            for item in items:
                title_el = await item.query_selector("h3")
                time_el = await item.query_selector(".event-time")
                if title_el and time_el:
                    title = await title_el.inner_text()
                    time = await time_el.inner_text()
                    movies.append({"title": title.strip(), "time": time.strip(), "cinema": "קולנוע יפו", "link": "https://www.jaffacinema.com/schedule"})
        except: pass

        # --- 2. סינמטק תל אביב ---
        try:
            await page.goto("https://www.cinema.co.il/events/", timeout=30000)
            items = await page.query_selector_all(".cinema-event-item")
            for item in items:
                title_el = await item.query_selector(".event-title")
                time
