import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

# הגדרות עמוד וממשק
st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת (חובה להרצה בענן)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב ויזואלי
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
    .stButton>button { width: 100%; border-radius: 10px; height: 3
