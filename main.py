import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="דיבגינג - קולנוע יפו", page_icon="📸", layout="wide")

# התקנת דפדפן בשרת במידה וחסר
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_jaffa_with_debug():
    results = []
    screenshot_path = "debug_view.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # התחזות לדפדפן רגיל כדי למנוע חסימות
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            url = "https://www.jaffacinema.com/schedule"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # המתנה לטעינת Wix
            await page.wait_for_timeout(8000)
            
            # צילום מסך של מה שהבוט רואה
            await page.screenshot(path=screenshot_path, full_page=True)
