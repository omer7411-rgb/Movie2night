import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def get_jaffa_cards_data():
    results = []
    screenshot_path = "debug_cards.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(10000)
            await page.screenshot(path=screenshot_path, full_page=True)
            
            data = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, section'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.includes('/') && t.includes(':') && t.length > 20);
            }''')
            
            for block in data:
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                
                # חיפוש תאריך ושעה: 22/03, יום ראשון 20:00
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+)\s*(\d{1,2}:\d{2})', block)
                
                if time_match:
                    date_val = time_match.group(1)
                    day_val = time_match.group(2)
                    hour_val = time_match.group(3)
                    
                    movie_title = "סרט ללא שם"
                    # לוגיקה פשוטה: שם הסרט הוא לרוב השורה הראשונה שלא מכילה "/" או ":"
                    for line in lines:
                        if "/" not in line and ":" not in line and "לרכישת" not in line and len(line) > 2:
                            movie_title = line
                            break
                    
                    results.append({
                        "title": movie_title,
                        "time": hour_val,
                        "day": day_val,
                        "date": date_val
                    })
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            await browser.close()
            
    return results, screenshot_path

st.title("🎬 לוח הקרנות קולנוע יפו")

if st.button("🔄 עדכן סרטים", type="primary"):
    with st.spinner("מנתח כרטיסיות סרטים..."):
        movies, img_path = asyncio.run(get_jaffa_cards_data())
        
        if movies:
            st.success(f"זיהיתי {len(movies)} סרטים!")
            for m in movies:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(m['title'])
                        st.write(f"📅 {m['day']} ({m['date']}) | ⏰ **{m['time']}**")
                    with col2:
                        msg = f"בא לך לראות את '{m['title']}' בקולנוע יפו? ב-{m['day']} בשעה {m['time']}."
                        st.link_button("🟢 וואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)
                    st.divider()
        else:
            st.warning("לא הצלחתי לחלץ סרטים. בדוק את צילום המסך למטה.")
            if os.path.exists(img_path):
                st.image(img_path)
