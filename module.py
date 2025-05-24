import pandas as pd
import openai
import os
import json
from datetime import datetime, timedelta
import urllib.parse
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv(dotenv_path="./ATT40370.env")

amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID"),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
)

def extract_preferences(user_input):
    from openai import OpenAI
    client = OpenAI(
      api_key=os.getenv("OPENAI_API_KEY")
    )
    prompt = f"""
    You are an assistant helping to book hotel rooms.

    Extract the following preferences from the user's request:
    - city code. Use IATA codes particularly airport codes if users specify airport and not cities. This should be a string.
    - latitude. Latitude if landmark is specified.
    - longitude. Longitude if landmark is specified.
    - amenities (if mentioned). This should be an array[string]. Available values are: SWIMMING_POOL, SPA, FITNESS_CENTER, AIR_CONDITIONING, RESTAURANT, PARKING, PETS_ALLOWED, AIRPORT_SHUTTLE, BUSINESS_CENTER, DISABLED_FACILITIES, WIFI, MEETING_ROOMS, NO_KID_ALLOWED,
    TENNIS, GOLF, KITCHEN, ANIMAL_WATCHING, BABY-SITTING, BEACH, CASINO, JACUZZI, SAUNA, SOLARIUM, MASSAGE, VALET_PARKING, BAR or LOUNGE, KIDS_WELCOME, NO_PORN_FILMS, MINIBAR, TELEVISION, WI-FI_IN_ROOM, ROOM_SERVICE, GUARDED_PARKG, SERV_SPEC_MENU
    - ratings. Hotel stars. Up to four values can be requested at the same time in a comma separated list. Format should be an array[string].
    - adults. Number of adult guests (1-9) per room.. Default to 1 if not specified.
    - checkInDate. Check-in date of the stay (hotel local date). string format YYYY-MM-DD. The lowest accepted date is the present date (no dates in the past). If notspecified, the default value will be today's date in the GMT time zone. If the user provides a day and month without a year, interpret it as the next occurrence of that date in the future.”
    - checkOutDate. Check-out date of the stay (hotel local date). string format YYYY-MM-DD. The lowest accepted date is checkInDate+1. If not specified, it will default to checkInDate +1. “If the user provides a day and month without a year, interpret it as the next occurrence of that date in the future.”
    - priceRange. Users price range per night.(ex: 200-300 or -300 or 100. It is mandatory to include a currency when this field is set. Default to USD.
    - Currency. Currency specified by the user.

    Return the output as a valid JSON object using double quotes for all keys and string values.
    Example Output as JSON:
    {{
    "cityCode": "NYC" or "JFK"(if airport is specified),
    "latitude": 41.397158,
    "longitude": 2.160873,
    "amenities": ["SPA", "FITNESS_CENTER"],
    "ratings": ["4","5"],
    "adults": 2,
    "checkInDate": "2025-08-01",
    "checkOutDate": "2025-08-06",
    "roomQuantity": 1,
    "priceRange": "100-500",
    "currency": "USD"
    }}

    Now extract from: "{user_input}"
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw_output = response.choices[0].message.content.strip()

    # Strip triple backticks and optional json label
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`").strip()
        if raw_output.lower().startswith("json"):
            raw_output = raw_output[4:].strip()

    try:
        structured_output = json.loads(raw_output)
        return structured_output
    except Exception as e:
        print("❌ Failed to parse structured output:", e)
        print("Raw cleaned response:", raw_output)
        return None

def normalize_dates(prefs):
    today = datetime.utcnow().date()

    try:
        check_in = datetime.strptime(prefs["checkInDate"], "%Y-%m-%d").date()
        if check_in < today:
            check_in = today

        check_out = datetime.strptime(prefs["checkOutDate"], "%Y-%m-%d").date()
        if check_out <= check_in:
            check_out = check_in + timedelta(days=1)

    except Exception as e:
        print("❌ Invalid or missing date format, applying defaults:", e)
        check_in = today
        check_out = today + timedelta(days=1)

    prefs["checkInDate"] = check_in.strftime("%Y-%m-%d")
    prefs["checkOutDate"] = check_out.strftime("%Y-%m-%d")
    return prefs

def search_hotels_and_offers(prefs):
    try:
        if prefs.get("latitude") and prefs.get("longitude"):
            hotel_response = amadeus.reference_data.locations.hotels.by_geocode.get(
                latitude=prefs["latitude"],
                longitude=prefs["longitude"],
                radius=10,
                radiusUnit="KM",
                amenities=prefs.get("amenities", []),
                ratings=prefs.get("ratings", [])
            )
        else:
            hotel_response = amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=prefs["cityCode"],
                radius=10,
                radiusUnit="KM",
                amenities=prefs.get("amenities", []),
                ratings=prefs.get("ratings", [])
            )

        hotel_ids = [hotel["hotelId"] for hotel in hotel_response.data]
        if not hotel_ids:
            print("No hotels found")
            return []

        all_offers = []

        for hotel_id in hotel_ids:
            try:
                response = amadeus.shopping.hotel_offers_search.get(
                    hotelIds=[hotel_id],
                    adults=prefs.get("adults", 1),
                    checkInDate=prefs["checkInDate"],
                    checkOutDate=prefs["checkOutDate"],
                    roomQuantity=prefs.get("roomQuantity", 1),
                    priceRange=prefs.get("priceRange", "0-1000"),
                    currency=prefs.get("currency", "USD")
                )
                if response and response.data:
                    all_offers.extend(response.data)
            except ResponseError:
                continue

        return all_offers

    except ResponseError as err:
        print(f"❌ Amadeus API error: {err}")
        return []
    
    
def format_offers_with_booking_links(hotel_offer_data, affiliate_id=None):
    results = []

    for hotel_block in hotel_offer_data:
        hotel = hotel_block.get("hotel", {})
        hotel_name = hotel.get("name", "Unnamed Hotel")
        hotel_id = hotel.get("hotelId", "N/A")
        latitude = hotel.get("latitude")
        longitude = hotel.get("longitude")
        city_code = hotel.get("cityCode", "")

        # Build base Booking.com URL
        query = urllib.parse.quote_plus(f"{hotel_name} {city_code}")
        booking_url = f"https://www.booking.com/searchresults.html?ss={query}"
        if affiliate_id:
            booking_url += f"&aid={affiliate_id}"

        for offer in hotel_block.get("offers", []):
            price_str = offer.get("price", {}).get("total", "0")
            currency = offer.get("price", {}).get("currency", "USD")

            try:
                price = float(price_str)
            except (ValueError, TypeError):
                price = float('inf')  # Push invalid prices to the end

            results.append({
                "hotel_name": hotel_name,
                "room_description": offer.get("room", {}).get("description", {}).get("text", "No description"),
                "price": f"{price_str} {currency}",
                "numeric_price": price,
                "check_in": offer.get("checkInDate", ""),
                "check_out": offer.get("checkOutDate", ""),
                "booking_url": booking_url
            })

    # Sort results by numeric price and take top 5
    results = sorted(results, key=lambda x: x["numeric_price"])[:5]

    for r in results:
        r.pop("numeric_price", None)
    return results

def chunk_list(lst, n):
  for i in range(0, len(lst), n):
      yield lst[i:i + n]
        
def main(user_input):
  preferences = extract_preferences(user_input)
  preferences = normalize_dates(preferences)
  hotel_offer_data = search_hotels_and_offers(preferences)
  response = format_offers_with_booking_links(hotel_offer_data, affiliate_id=None)
  return response