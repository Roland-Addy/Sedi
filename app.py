import streamlit as st
from module import extract_preferences, normalize_dates, search_hotels_and_offers, format_offers_with_booking_links

# Configure page
st.set_page_config(page_title="Sedi | AI Hotel Finder", layout="centered")

# Custom CSS for aesthetics
st.markdown("""
    <style>
        .main {background-color: #f7f9fa;}
        h1, h2, h3, h4 {color: #1E3A8A; font-family: 'Helvetica Neue', sans-serif;}
        .stTextInput > label {font-weight: bold; color: #333;}
        .stTextArea textarea {font-size: 16px; height: 120px;}
        .result-card {
            background-color: white;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 style='text-align: center;'>🌍 Welcome to Sedi!</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px;'>Your AI-powered travel assistant for finding the perfect hotel stay</p>", unsafe_allow_html=True)

# Input section
user_query = st.text_area("What are you looking for?", placeholder="e.g., Hotels near CN Tower in Toronto, check-in June 1st for 3 nights, max 250 CAD, gym")

# Search logic
if st.button("🔍 Search Hotels"):
    if user_query.strip():
        with st.spinner("Finding the best options for you..."):
            prefs = extract_preferences(user_query)
            if prefs:
                prefs = normalize_dates(prefs)
                results = search_hotels_and_offers(prefs)
                top_matches = format_offers_with_booking_links(results)

                if top_matches:
                    st.markdown("<h2>🏨 Top Hotel Matches:</h2>", unsafe_allow_html=True)
                    for match in top_matches:
                        st.markdown(f"""
                        <div class='result-card'>
                            <h3>{match['hotel_name']}</h3>
                            <p><strong>Room:</strong> {match['room_description']}</p>
                            <p><strong>Price:</strong> {match['price']}</p>
                            <p><strong>Dates:</strong> {match['check_in']} → {match['check_out']}</p>
                            <a href='{match['booking_url']}' target='_blank'>🔗 Book on Booking.com</a>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No matching hotels were found. Please adjust your preferences and try again.")
            else:
                st.error("We couldn’t understand your preferences. Try rephrasing your request.")
    else:
        st.warning("Please describe what you're looking for to begin your search.")

