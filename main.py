import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב לוח שנה מודרני
st.markdown("""
    <style>
    .calendar-card {
        background-color: #262730;
        border-radius: 10px;
        border-right: 8px solid #FF4B4B;
        padding: 20px;
        margin-bottom: 15px;
        direction: rtl;
        text-align: right;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .date-label { color: #FF4B4B; font-weight: bold; font-size: 1.1rem; }
    .movie-title { color: white; font-size: 1.4rem; margin: 5px 0; font-weight: 600; }
    .cinema-tag { background: #444; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

async def get_jaffa_calendar():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            url = "https://www.jaffacinema.com/schedule"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000) # זמן לטעינת הלוח

            # חילוץ נתונים: ב-Wix לוח ההקרנות מורכב בד"כ מרשימת טקסטים
            # אנחנו מחפשים קומבינציה של שעה (למשל 20:00) ושם סרט
            all_text_elements = await page.query_selector_all("span, p, h3")
            
            temp_date = "הקרנות קרובות"
            for el in all_text_elements:
                text = await el.inner_text()
                if not text: continue
                text = text.strip()

                # זיהוי תאריכים (למשל: "יום שני 12.5")
                if any(day in text for day in ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "שבת", "יום ראשון"]):
                    temp_date = text
                
                # זיהוי שעה ושם סרט (מחפשים פורמט של 00:00)
                elif ":" in text and len(text) < 6: # שעה
                    next_el = all_text_elements[all_text_elements.index(el) + 1]
                    movie_name = await next_el.inner_text()
                    if movie_name and len(movie_name) > 2:
                        movies.append({
                            "date": temp_date,
                            "time": text,
                            "title": movie_name.strip()
                        })
        except Exception as e:
            st.error(f"שגיאה בסריקה: {e}")
        finally:
            await browser.close()
    return movies

st.title("📅 לוח ההקרנות של קולנוע יפו")
st.write("המידע נמשך ישירות מהאתר המעודכן")

if st.button("🔄 עדכן לוח הקרנות", type="primary"):
    with st.spinner("בונה את לוח השנה..."):
        data = asyncio.run(get_jaffa_calendar())
        st.session_state.jaffa_data = data

if "jaffa_data
