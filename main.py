import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת במידה וחסר
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב CSS יציב
st.markdown("""
    <style>
    .calendar-card {
        background-color: #262730;
        border-radius: 12px;
        border-right: 8px solid #FF4B4B;
        padding: 15px;
        margin-bottom: 10px;
        direction: rtl;
        text-align: right;
    }
    .date-header {
        background-color: #FF4B4B;
        color: white;
        padding: 5px 15px;
        border-radius: 5px;
        margin-top: 15px;
        font-weight: bold;
        display: inline-block;
        direction: rtl;
    }
    .movie-info { font-size: 1.2rem; margin-bottom: 10px; color: white; }
    </style>
    """, unsafe_allow_html=True)

async def get_jaffa_data():
