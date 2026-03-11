import streamlit as st
import asyncio
import os
import re
from playwright.async_api import async_playwright
import urllib.parse

st.set_page_config(page_title="לוח הקרנות - קולנוע יפו", page_icon="🎬", layout="wide")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

# עיצוב CSS
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
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # מעבר לאתר
            await page.goto("https://www.jaffacinema.com/schedule", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(7000)
            
            # שליפת טקסטים בצורה תקינה (תיקון strip ל-trim)
            content = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('div, span, p, h3'))
                            .map(el => el.innerText ? el.innerText.trim() : "")
                            .filter(t => t.length > 1);
            }''')
            
            current_date = "הקרנות קרובות"
            days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
            
            for i, text in enumerate(content):
                # זיהוי יום
                if any(f"יום {d}" in text or (text.startswith("יום") and d in text) for d in days):
                    current_date = text
                
                # זיהוי שעה
                if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', text):
                    for j in range(i + 1, min(i + 8, len(content))):
                        potential_name = content[j]
                        if len(potential_name) > 3 and "הזמן" not in potential_name and ":" not in potential_name and "כרטיס" not in potential_name:
                            results.append({
                                "date": current_date,
                                "time": text,
                                "title": potential_name
                            })
                            break
        except Exception as e:
            st.error(f"שגיאה: {e}")
        finally:
            await browser.close()
    
    # ניקוי כפילויות
    unique_results = []
    seen = set()
    for res in results:
        identifier = f"{res['time']}-{res['title']}"
        if identifier not in seen:
            unique_results.append(res)
            seen.add(identifier)
    return unique_results

st.title("🎬 לוח ההקרנות של קולנוע יפו")

if st.button("🔄 טען לוח מעודכן", type="primary"):
    with st.spinner("מושך נתונים מקולנוע יפו..."):
        st.session_state["jaffa_list"] = asyncio.run(get_jaffa_data())

if "jaffa_list" in st.session_state:
    if not st.session_state["jaffa_list"]:
        st.warning("האתר נטען אך לא זוהו סרטים. נסה ללחוץ שוב על כפתור הטעינה.")
    else:
        curr_d = ""
        for m in st.session_state["jaffa_list"]:
            if m['date'] != curr_d:
                st.markdown(f'<div class="date-header">{m["date"]}</div>', unsafe_allow_html=True)
                curr_d = m['date']
            
            st.markdown(f"""
                <div class="calendar-card">
                    <div class="movie-info"><b style="color: #FF4B4B;">{m['time']}</b> | {m['title']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # הכנת הודעת וואטסאפ
            msg = f"היי, בא לך לסרט? {m['title']} בקולנוע יפו ב-{m['date']} בשעה {m['time']}. לינק:
