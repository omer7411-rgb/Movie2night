import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright
from datetime import datetime

st.set_page_config(page_title="Jaffa Cinema Debugger", page_icon="🎬")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def scrape_jaffa_with_screenshot():
    movies = []
    screenshot_path = "debug_screenshot.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        try:
            url = "https://www.jaffacinema.com"
            st.write(f"מתחבר לכתובת: {url}...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # מחכים שהתוכן של Wix ייטען באמת
            await page.wait_for_timeout(7000)
            
            # צילום מסך של מה שהסורק רואה ברגע זה
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # חיפוש טקסטים של סרטים (ב-Wix הם בדרך כלל בתוך span או h3)
            # ננסה לחלץ את כל הטקסטים שנראים כמו כותרות
            elements = await page.query_selector_all("h3, span")
            for el in elements:
                text = await el.inner_text()
                if text and len(text.strip()) > 2:
                    # סינון בסיסי כדי לא לקבל זבל
                    clean_text = text.strip()
                    if any(char.isalpha() for char in clean_text):
                        movies.append(clean_text)
                        
        except Exception as e:
            st.error(f"קרתה שגיאה: {e}")
        finally:
            await browser.close()
            
    return movies, screenshot_path

st.title("🎬 סורק קולנוע יפו + דיבגינג")

if st.button("🔍 הרץ סריקה וצילום מסך"):
    with st.spinner("סורק ומצלם..."):
        movie_list, img_path = asyncio.run(scrape_jaffa_with_screenshot())
        
        # הצגת צילום המסך
        if os.path.exists(img_path):
            st.subheader("📸 ככה האתר נראה לסורק:")
            st.image(img_path)
        
        # הצגת רשימת הטקסטים שנמצאו
        st.subheader("📄 טקסטים שנמצאו באתר:")
        if movie_list:
            # מציג רק את ה-20 הראשונים כדי לא להציף
            unique_movies = list(set(movie_list))[:30]
            for m in unique_movies:
                st.write(f"- {m}")
        else:
            st.warning("לא נמצאו טקסטים בכלל.")
