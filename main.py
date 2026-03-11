import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Movie2Night", page_icon="🎬")

st.markdown("""
    <style>
    .movie-card { background-color: #1e1e1e; padding: 15px; border-radius: 12px; border-right: 4px solid #FF4B4B; margin-bottom: 10px; direction: rtl; text-align: right; }
    h3 { color: #FF4B4B; margin: 0; font-size: 1.2rem; }
    .info { color: #aaaaaa; font-size: 0.9rem; margin-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

CINEMAS = [
    {"name": "קולנוע יפו", "query": "קולנוע יפו לוח הקרנות", "url": "https://www.jaffacinema.com/schedule"},
    {"name": "סינמטק תל אביב", "query": "סינמטק תל אביב לוח הקרנות", "url": "https://www.cinema.co.il/events/"},
    {"name": "סינמטק ירושלים", "query": "סינמטק ירושלים לוח הקרנות", "url": "https://jer-cin.org.il/he/program"},
    {"name": "לב סמדר", "query": "קולנוע לב סמדר לוח הקרנות", "url": "https://www.lev.co.il/cinema/smadar/"}
]

def get_movies_via_google():
    all_found = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for cinema in CINEMAS:
        try:
            # אנחנו מחפשים בגוגל את התוצאות האחרונות
            search_url = f"https://www.google.com/search?q={cinema['query']}"
            resp = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # שליפת כותרות מהחיפוש שמרמזות על סרטים חדשים
            items = soup.find_all('h3')
            for item in items[:5]: # לוקחים את התוצאות המובילות
                title = item.get_text()
                if "הקרנה" in title or "סרט" in title or "|" in title:
                    all_found.append({
                        "title": title.replace(" - גוגל", "").split("|")[0],
                        "cinema": cinema["name"],
                        "time": "בדוק באתר לזמנים",
                        "link": cinema["url"]
                    })
        except:
            continue
    return all_found

st.title("🎬 Movie2Night")
st.write("סורק נתונים דרך מנוע החיפוש (עוקף חסימות)")

if st.button("🔍 מצא סרטים עכשיו", type="primary"):
    with st.spinner("מבצע חיפוש חכם..."):
        results = get_movies_via_google()
        st.session_state.movies = results

if "movies" in st.session_state:
    if not st.session_state.movies:
        st.warning("לא הצלחתי למשוך מידע. ייתכן שגוגל דורש אימות. נסה שוב בעוד דקה.")
    else:
        for m in st.session_state.movies:
            st.markdown(f'<div class="movie-card"><h3>{m["title"]}</h3><div class="info">{m["cinema"]}</div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.link_button("🎟️ לאתר והזמנה", m['link'], use_container_width=True)
            g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&location={m['cinema']}"
            c2.link_button("📅 ליומן", g_url, use_container_width=True)
