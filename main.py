import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="דיבגינג - קולנוע יפו", page_icon="📸", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_jaffa_with_debug():
    results = []
    screenshot_path = "debug_view.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            url = "https://www.jaffacinema.com/schedule"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # המתנה לטעינת Wix
            await page.wait_for_timeout(8000)
            
            # צילום מסך - השורה שבה קרסה השגיאה
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # חילוץ טקסטים
            content = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, span, p, h3'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.length > 1);
            }''')
            
            current_date = "הקרנות קרובות"
            days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
            
            for i, text in enumerate(content):
                if any(f"יום {d}" in text for d in days):
                    current_date = text
                
                if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', text):
                    for j in range(i + 1, min(i + 8, len(content))):
                        potential_name = content[j]
                        if len(potential_name) > 3 and "הזמן" not in potential_name and ":" not in potential_name:
                            results.append({"date": current_date, "time": text, "title": potential_name})
                            break
        except Exception as e:
            st.error(f"שגיאה בסריקה: {e}")
        finally:
            await browser.close()
            
    return results, screenshot_path

st.title("🔍 בדיקת תצוגה - קולנוע יפו")

if st.button("🚀 הרץ סריקה וצלם מסך", type="primary"):
    with st.spinner("מבצע סריקה וצילום..."):
        movies, img_path = asyncio.run(get_jaffa_with_debug())
        
        # הצגת התמונה שנלכדה כדי שנבין מה הבוט רואה
        if os.path.exists(img_path):
            st.subheader("📸 ככה האתר נראה לסורק:")
            st.image(img_path)
        
        if movies:
            st.success(f"נמצאו {len(movies)} סרטים!")
            for m in movies:
                st.write(f"📅 {m['date']} | ⏰ {m['time']} | 🎬 **{m['title']}**")
        else:
            st.warning("לא זוהו סרטים בטקסט. בדוק את התמונה למעלה לראות אם האתר נטען.")
