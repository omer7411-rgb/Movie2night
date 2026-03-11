import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_jaffa_final_v3():
    results = []
    screenshot_path = "debug_final.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # שימוש בעמוד הבית שראינו שעולה בהצלחה
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)
            
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # שליפת כל הטקסטים מהדף
            data = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('span, div, p, h1, h2, h3'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.length > 1);
            }''')
            
            for i, text in enumerate(data):
                # זיהוי שם סרט לפי קו אלכסוני ושנה (למשל: "שם הסרט / 23")
                # מחפש טקסט שמכיל "/" ואחריו לפחות ספרה אחת
                if "/" in text and re.search(r'/\s*\d+', text):
                    movie_title = text
                    movie_time = ""
                    movie_day = ""
                    movie_date = ""
                    
                    # סריקה של 12 האלמנטים הבאים אחרי שם הסרט כדי למצוא תאריך ושעה
                    for j in range(i + 1, min(i + 13, len(data))):
                        val = data[j]
                        
                        # זיהוי שעה (HH:MM)
                        if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', val):
                            movie_time = val
                        
                        # זיהוי יום בשבוע
                        elif any(day in val for day in ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת", "יום ראשון"]):
                            movie_day = val
                        
                        # זיהוי תאריך (למשל 12.05 או 12/05)
                        elif re.search(r'\d{1,2}[\./]\d{1,2}', val):
                            movie_date = val
                        
                        if movie_time and movie_day:
                            break
                    
                    if movie_title and movie_time:
                        results.append({
                            "title": movie_title,
                            "time": movie_time,
                            "day": movie_day,
                            "date": movie_date
                        })
        except Exception as e:
            st.error(f"שגיאה בסריקה: {e}")
        finally:
            await browser.close()
            
    # הסרת כפילויות
    unique = []
    seen = set()
    for r in results:
        key = f"{r['time']}-{r['title']}"
        if key not in seen:
            unique.append(r)
            seen.add(key)
    return unique, screenshot_path

st.title("🎬 לוח הקרנות קולנוע יפו")

if st.button("🔄 עדכן לוח הקרנות", type="primary"):
    with st.spinner("מחפש סרטים עם המבנה 'שם / שנה'..."):
        movies, img_path = asyncio.run(get_jaffa_final_v3())
        
        if movies:
            st.success(f"נמצאו {len(movies)} הקרנות!")
            for m in movies:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(m['title'])
                        details = f"🗓️ {m['day']}"
                        if m['date']: details += f" ({m['date']})"
                        details += f" | ⏰ **{m['time']}**"
                        st.write(details)
                    with col2:
                        msg = f"היי, בא לך לסרט? {m['title']} ב-{m['time']} ({m['day']})."
                        st.link_button("🟢 וואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}")
                    st.divider()
        else:
            st.warning("לא הצלחתי למצוא סרטים במבנה המבוקש.")
            if os.path.exists(img_path):
                st.image(img_path, caption="ככה נראה האתר בזמן הבדיקה")
