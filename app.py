import streamlit as st
from module import extract_preferences, normalize_dates, search_hotels_and_offers, format_offers_with_booking_links

# Streamlit app logic
st.set_page_config(page_title="AI Hotel Finder", layout="centered")
st.title("AI-Powered Hotel Finder")
st.write("Describe your ideal hotel stay and we’ll find matches for you!")

user_query = st.text_area("What are you looking for?", placeholder="e.g., Hotels near CN Tower in Toronto...")

if st.button("Search"):
    if user_query.strip():
        with st.spinner("Finding the best options for you..."):
            prefs = extract_preferences(user_query)
            if prefs:
                prefs = normalize_dates(prefs)
                results = search_hotels_and_offers(prefs)
                top_matches = format_offers_with_booking_links(results)

                if top_matches:
                    st.success("Here are your hotel options:")
                    for match in top_matches:
                        st.markdown(f"### {match['hotel_name']}")
                        st.markdown(f"**Room:** {match['room_description']}")
                        st.markdown(f"**Price:** {match['price']}")
                        st.markdown(f"**Dates:** {match['check_in']} → {match['check_out']}")
                        st.markdown(f"[🔗 Book on Booking.com]({match['booking_url']})")
                        st.markdown("---")
                else:
                    st.warning("No results found.")
            else:
                st.error("We couldn’t understand your preferences. Try again.")
    else:
        st.warning("Please enter your request above.")
