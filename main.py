import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת (חובה להרצה ראשונה ב-Streamlit)
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב הלוח
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
    }
    .movie-info { font-size: 1.2rem; margin-bottom: 10px; color: white; }
    </style>
    """, unsafe_allow_html=True)

async def get_jaffa_data():
    results = []
    async with async_playwright() as p:
        # הפעלת דפדפן עם התחזות למשתמש רגיל כדי למנוע חסימות
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto("https://www.jaffacinema.com/schedule", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(7000) # זמן לטעינת Wix
            
            # תיקון השגיאה מצילום המסך: שימוש ב-trim() במקום strip()
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
                
                # זיהוי שעה (HH:MM)
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
    
    # הסרת כפילויות
    unique_results = []
    seen = set()
    for res in results:
        if f"{res['time']}-{res['title']}" not in seen:
            unique_results.append(res)
            seen.add(f"{res['time']}-{res['title']}")
    return unique_results

st.title("🎬 לוח הקרנות - קולנוע יפו")

if st.button("🔄 טען לוח מעודכן", type="primary"):
    with st.spinner("דג סרטים מהאתר..."):
        st.session_state["jaffa_list"] = asyncio.run(get_jaffa_data())

if "jaffa_list" in st.session_state:
    if not st.session_state["jaffa_list"]:
        st.warning("לא נמצאו סרטים. נסה שוב.")
    else:
        curr_d = ""
        for m in st.session_state["jaffa_list"]:
            if m['date'] != curr_d:
                st.markdown(f'<div class="date-header">{m["date"]}</div>', unsafe_allow_html=True)
                curr_d = m['date']
            
            st.markdown(f"""
                <div class="calendar-card">
                    <b style="color: #FF4B4B;">{m['time']}</b> | {m['title']}
                </div>
            """, unsafe_allow_html=True)
            
            # כפתור וואטסאפ
            msg = f"בא לך לסרט? {m['title']} בקולנוע יפו ב-{m['date']} ב-{m['time']}."
            st.link_button("🟢 שלח בוואטסאפ", f"https://wa.me/?text={urllib.parse.quote(msg)}")
