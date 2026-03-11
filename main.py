async def scrape_full_board(status_placeholder):
    results = []
    days_map = {0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            status_placeholder.info("מתחבר לאתר וסורק את כל ההקרנות...")
            await page.goto("https://www.jaffacinema.com/", wait_until="networkidle")
            
            # גלילה עמוקה יותר כדי לוודא שכל האלמנטים נטענו
            for _ in range(12): 
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(0.4)
            
            # סקריפט JS משופר שמחפש את כל כפתורי הרכישה והטקסטים סביבם
            movies_raw = await page.evaluate('''() => {
                const data = [];
                // מחפש את כל כפתורי הרכישה
                const allLinks = Array.from(document.querySelectorAll('a'))
                                     .filter(a => a.innerText.includes('לרכישת'));
                
                allLinks.forEach(link => {
                    let container = link.closest('div[data-mesh-id]') || link.parentElement.parentElement.parentElement;
                    const img = container.querySelector('img');
                    
                    // מציאת הכותרת (הטקסט הכי גדול בקונטיינר)
                    let title = ""; let maxFS = 0;
                    container.querySelectorAll('*').forEach(el => {
                        const fs = parseFloat(window.getComputedStyle(el).fontSize);
                        const txt = el.innerText.trim();
                        if (fs > maxFS && txt.length > 1 && txt.length < 60 && !txt.includes('/') && !txt.includes(':')) {
                            maxFS = fs; title = txt;
                        }
                    });
                    
                    data.push({
                        title: title,
                        url: link.href,
                        img: img ? img.src : "",
                        fullText: container.innerText
                    });
                });
                return data;
            }''')

            seen_instances = set()
            curr_year = datetime.now().year
            
            for m in movies_raw:
                # חילוץ תאריך ושעה מהטקסט המלא של הקונטיינר
                match = re.search(r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})', m['fullText'])
                if match and m['title']:
                    day_month = match.group(1)
                    time_str = match.group(2)
                    d, month = day_month.split('/')
                    
                    # יצירת מזהה ייחודי כדי למנוע כפילויות בסריקה
                    uid = f"{m['title']}-{day_month}-{time_str}"
                    if uid not in seen_instances:
                        date_obj = datetime(curr_year, int(month), int(d))
                        iso_time = f"{curr_year}-{month.zfill(2)}-{d.zfill(2)}T{time_str}:00"
                        
                        results.append({
                            "title": m['title'],
                            "url": m['url'],
                            "img": m['img'],
                            "time": time_str,
                            "date_str": f"{d.zfill(2)}/{month.zfill(2)}",
                            "day_name": days_map[date_obj.weekday()],
                            "dt": date_obj,
                            "iso": iso_time
                        })
                        seen_instances.add(uid)
            
        finally: await browser.close()
    return results
