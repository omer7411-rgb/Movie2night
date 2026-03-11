import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# Install browser if missing
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_jaffa_home_data():
    results = []
    screenshot_path = "home_debug.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            # Going to home page to avoid 404 errors seen in previous logs
            url = "https://www.jaffacinema.com/"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(8000)
            
            # Taking screenshot for debugging
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Extracting text from page elements
            content = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, span, p, h1, h2, h3'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.length > 1);
            }''')
            
            current_date = "הקרנות קרובות"
            days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
            
            for i, text in enumerate(content):
                if any(f"יום {d}" in text for d in days) or "2026" in text:
                    current_date = text
                
                # Regex for HH:MM format
                if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', text):
                    for j in range(max(0, i-2), min(i + 8, len(content))):
                        potential = content[j]
                        if len(potential) > 3 and "הזמן" not in potential and ":" not in potential and potential != text:
                            results.append({"date": current_date, "time": text, "title": potential})
                            break
        except Exception as e:
            st.error(f"Error during scraping: {e}")
        finally:
            await browser.close()
            
    return results, screenshot_path

st.title("🎬 לוח הקרנות קולנוע יפו")

if st.button("🚀 סרוק את האתר", type="primary"):
    with st.spinner("מתחבר לקולנוע יפו..."):
        movies, img_path = asyncio.run(get_jaffa_home_data())
        
        if os.path.exists(img_path):
            st.subheader("📸 תמונת מצב מהאתר:")
            st.image(img_path)
        
        if movies:
            st.success(f"נמצאו {len(movies)} סרטים!")
            for m in movies:
                with st.container():
                    st.markdown(f"### {m['title']}")
                    st.write(f"⏰ {m['time']} | 📅 {m['date']}")
                    msg = f"בא לך לסרט? {m['title']} ב-{m['time']} ({m['date']})"
                    st.link_button("🟢 שלח בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}")
                    st.divider()
        else:
            st.warning("לא זוהו סרטים. בדוק את צילום המסך למעלה.")
