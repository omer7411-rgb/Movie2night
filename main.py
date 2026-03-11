import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב לוח שנה
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
        padding: 5px 15px;
        border-radius: 5px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .movie-title { font-size: 1.5rem; font-weight: bold; margin: 5px 0; }
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

            # מוציא את כל גושי הטקסט מהדף
            elements = await page.query_selector_all("span, p, h3")
            
            temp_date = "הקרנות קרובות
