import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

st.set_page_config(page_title="Movie2Night Israel", page_icon="🎬", layout="wide")

# עיצוב UI
st.markdown("""
    <style>
    .movie-card { background-color: #1e1e1e; padding: 15px; border-radius: 12px; border-right: 4px solid #FF4B4B; margin-bottom: 10px; direction: rtl; text-align: right; }
    h3 { color: #FF4B4B; margin: 0; font-size: 1.2rem; }
    .info { color: #aaaaaa; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# הגדרות סריקה קלות (ללא דפדפן כבד)
CINEMAS = [
    {"name": "קולנוע יפו", "url": "https://www.jaffacinema.com/schedule", "container": "div.event-item", "title": "h3", "time": ".event-time"},
    {"name": "סינמטק תל אביב", "url": "https://www.cinema.co.il/events/", "container": ".cinema-event-item", "title": "h5", "time": ".event-hour"},
    {"name": "סינמטק ירושלים", "url": "https://jer-cin.org.il/he/program", "container": ".program-item", "title": ".title", "time": ".time"},
    {"name": "קולנוע לב סמדר", "url": "https://www.lev.co.il/cinema/smadar/", "container": ".movie-performance-item", "title": ".movie-name", "time": ".performance-time"}
]

def scrape_simple():
    movies = []
    # הדרס שמתחזה לדפדפן ישראלי אמיתי
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    for cinema in CINEMAS:
        try:
            st.write(f"מנסה להתחבר ל{cinema['name']}...")
            response = requests.get(cinema["url"], headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                items = soup.select(cinema["container"])
                st.write(f"🔍 {cinema['name']}: נמצאו {len(items)} סרטים")
                
                for item in items:
                    title = item.select_one(cinema["title"])
                    time = item.select_one(cinema["time"])
                    if title and time:
                        movies.append({
                            "title": title.get_text().strip(),
                            "time": time.get_text().strip(),
                            "cinema": cinema["name"],
                            "link": cinema["url"]
                        })
            else:
                st.sidebar.warning(f"{cinema['name']} חסם את הגישה (קוד {response.status_code})")
        except Exception as e:
            st.sidebar.error(f"שגיאה ב{cinema['name']}")
    return movies

st.title("🎬 Movie2Night")

if st.button("🔍 סרוק בתי קולנוע עכשיו", type="primary"):
    with st.spinner("מחפש סרטים..."):
        results = scrape_simple()
        st.session_state.all_movies = results

if "all_movies" in st.session_state:
    if not st.session_state.all_movies:
        st.error("האתרים עדיין חוסמים את השרת. ייתכן שנדרש שרת ישראלי או VPN.")
    else:
        for m in st.session_state.all_movies:
            st.markdown(f'<div class="movie-card"><h3>{m["title"]}</h3><div class="info">{m["cinema"]} | {m["time"]}</div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.link_button("🎟️ כרטיסים", m['link'], use_container_width=True)
            g_url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={m['title']}&details=הקרנה ב{m['cinema']}&location={m['cinema']}"
            c2.link_button("📅 ליומן", g_url, use_container_width=True)
