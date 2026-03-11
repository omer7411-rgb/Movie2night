import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

# הגדרות עיצוב
st.set_page_config(page_title="Cinema Sync", page_icon="🎬", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; }
    .movie-card { background-color: #262730; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# פונקציית סריקה
async def get_movies():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # דוגמה לסריקה של קולנוע יפו (ניתן להוסיף את השאר לפי ה-JSON)
        try:
            await page.goto("https://www.jaffacinema.com/schedule", timeout=60000)
            elements = await page.query_selector_all(".event-item")
            for el in elements:
                title = await (await el.query_selector("h3")).inner_text()
                time = await (await el.query_selector(".event-time")).inner_text()
                movies.append({"title": title, "time": time, "cinema": "קולנוע יפו", "link": "https://www.jaffacinema.com/schedule"})
        except: pass
        
        await browser.close()
    return movies

st.title("🎬 סרטים בקולנוע")

if st.button("רענן רשימת סרטים"):
    with st.spinner("סורק את בתי הקולנוע..."):
        st.session_state.movies = asyncio.run(get_movies())

if "movies" in st.session_state:
    for m in st.session_state.movies:
        st.markdown(f"""
            <div class="movie-card">
                <h3>{m['title']}</h3>
                <p>📍 {m['cinema']} | ⏰ {m['time']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("🎟️ הזמן כרטיס", m['link'])
        with col2:
            google_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&details=הקרנה ב{m['cinema']}&location={m['cinema']}"
            st.link_button("📅 הוסף ליומן", google_url)
