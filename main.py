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
            
            # שליפת טקסטים בצורה חכמה ששומרת על הקרבה בין אלמנטים
            data = await page.evaluate('''() => {
                // מחפשים את כל הבלוקים של הסרטים
                return Array.from(document.querySelectorAll('div, section'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.includes('/') && t.includes(':') && t.length > 20);
            }''')
            
            for block in data:
                lines = [l.strip() for l in block.split('\n') if l.strip()]
                
                # חיפוש שורה שמכילה תאריך ושעה (למשל: 22/03, יום ראשון 20:00)
                time_match = re.search(r'(\d{1,2}/\d{1,2}),?\s*(יום\s+\w+)\s*(\d{1,2}:\d{2})', block)
                
                # חיפוש שורת "מקור / שנה" (למשל: איראן / 1999)
                origin_match = re.search(r'(.+)\s*/\s*(\d{4})', block)
                
                if time_match:
                    date_val = time_match.group(1)
                    day_val = time_match.group(2)
                    hour_val = time_match.group(3)
                    
                    # שם הסרט לרוב מופיע אחרי שורת המקור או כטקסט בולט בבלוק
                    # ננסה לדוג אותו מהשורות הראשונות בבלוק שאינן שורת המקור
                    movie_title = "סרט ללא שם"
                    for line in lines:
                        if "/" not in line and ":" not in line and "לרכישת" not in line and len(line) > 2:
                            movie_title = line
                            break
                    elif origin_match and len(lines) > 1:
                         # אם יש שורת מקור, שם הסרט לרוב נמצא מתחתיה או מעליה
                         idx = 0
                         for i, l in enumerate(lines):
                             if "/" in l and any(char.isdigit() for char in l):
                                 idx = i
                                 break
                         if idx + 1 < len(lines):
                             movie_title = lines[idx+1]

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
                    st.markdown(f"### {m['title']}")
                    st.write(f"📅 {m['day']} ({m['date']}) | ⏰ **{m['time']}**")
                    msg = f"היי, בא לך לראות את '{m['title']}' בקולנוע יפו? ב-{m['day']} בשעה {m['time']}."
                    st.link_button("🟢 שתף בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}")
                    st.divider()
        else:
            st.warning("לא הצלחתי לחלץ את שמות הסרטים מהכרטיסיות.")
            if os.path.exists(img_path):
                st.image(img_path, caption="תצוגת האתר שנסרקה")
