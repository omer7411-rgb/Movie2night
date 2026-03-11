import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright

st.set_page_config(page_title="Jaffa Cinema Scanner", page_icon="🎬")

# התקנת דפדפן בשרת
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    os.system("playwright install chromium")

async def scrape_jaffa():
    movies = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # מדמה דפדפן רגיל לחלוטין
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # ננסה את עמוד הבית שבו מופיע הלוח
            url = "https://www.jaffacinema.com"
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # המתנה של 5 שניות כדי לוודא ש-Wix סיים לטעון את הווידג'טים
            await page.wait_for_timeout(5000)
            
            # חיפוש אלמנטים שמכילים טקסט של כותרת (h3 נפוץ ב-Wix לכותרות סרטים)
            items = await page.query_selector_all("h3")
            
            for item in items:
                title = await item.inner_text()
                if title and len(title.strip()) > 1:
                    movies.append({
                        "title": title.strip(),
                        "cinema": "קולנוע יפו",
                        "link": url
                    })
        except Exception as e:
            st.error(f"שגיאה: {e}")
        finally:
            await browser.close()
    return movies

st.title("🎬 סורק קולנוע יפו")

if st.button("🔍 חפש הקרנות ביפו"):
    with st.spinner("סורק את האתר..."):
        results = asyncio.run(scrape_jaffa())
        if results:
            st.success(f"מצאתי {len(results)} כותרות פוטנציאליות!")
            for m in results:
                with st.container():
                    st.markdown(f"### {m['title']}")
                    st.link_button("לאתר", m['link'])
                    st.write("---")
        else:
            st.warning("לא נמצאו סרטים. ייתכן והאתר מגן על התוכן שלו.")
