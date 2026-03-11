import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

# הגדרות עמוד וממשק
st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת (חובה להרצה בענן)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב ויזואלי - וודא שהסגירה של הציטוטים המשולשים למטה תקינה
st.markdown("""
    <style>
    .movie-card { 
        background-color: #1e1e1e; 
        padding: 20px; 
        border-radius: 15px; 
        border-right: 5px solid #FF4B4B; 
        margin-bottom: 15px; 
        direction: rtl; 
        text-align: right; 
    }
    h3 { color: #FF4B4B; margin: 0; font-size: 1.5rem; }
    .info { color: #cccccc; margin: 10px 0; font-size: 1.1rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# רשימת בתי הקולנוע והסלקטורים שלהם
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
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for cinema in CINEMAS_TO_SCAN:
            try:
                await page.goto(cinema["url"], timeout=60000, wait_until="domcontentloaded")
