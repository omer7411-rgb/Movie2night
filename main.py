import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

# 1. הגדרות דף - תמיד בשורה הראשונה
st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# 2. התקנת דפדפן - וידוא התקנה שקטה בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try:
        os.system("playwright install chromium")
    except Exception as e:
        st.error(f"שגיאה בהתקנת דפדפן: {e}")

async def get_jaffa_home_data():
    results = []
    screenshot_path = "home_debug.png"
    async with async_playwright() as p:
        # הפעלת דפדפן עם User Agent כדי לא להיחסם
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # הולכים לדף הבית כי ה-schedule החזיר 404
            url = "https://www.jaffacinema.com/"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # המתנה לטעינת Wix (קריטי!)
            await page.wait_for_timeout(8000)
            
            # צילום מסך ל
