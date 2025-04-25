import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import tempfile
import os
import re
from datetime import datetime

# Define expected columns in the CSV
EXPECTED_COLUMNS = [
    'id', 'title', 'description', 'price', 'duration', 'category', 'locations', 'inclusions',
    'exclusions', 'featured', 'image_url', 'gallery_images', 'itinerary', 'pdf_url',
    'created_at', 'updated_at', 'country', 'activities', 'cities', 'places', 'hotels',
    'flights_included', 'food_details', 'airport_transfer', 'guide_included', 'shopping_stops',
    'is_group_tour', 'minimum_pax', 'room_occupancy', 'visa_guidance', 'language_support',
    'difficulty_level', 'sustainability_rating', 'recommended_age_group', 'seasonal_availability',
    'amenities', 'covid_safety_measures', 'cancellation_policy', 'special_requirements',
    'accessibility_features'
]

st.title("Tour Package Extractor (Smart NLP + Bulk-Ready)")
st.write("Upload your tour packages CSV and multiple itinerary PDFs. The tool extracts and appends new packages using enhanced rule-based logic.")

uploaded_csv = st.file_uploader("Upload Tour Packages CSV", type=["csv"])
uploaded_pdfs = st.file_uploader("Upload Itinerary PDFs", type=["pdf"], accept_multiple_files=True)


def extract_info(text):
    data = {col: "" for col in EXPECTED_COLUMNS}

    lines = text.split('\n')
    lower_text = text.lower()

    # Title & description
    if lines:
        data['title'] = lines[0].strip()
    data['description'] = ' '.join(lines[1:6]).strip()

    # Duration
    duration_match = re.search(r'(\d+\s*Nights?\s*/\s*\d+\s*Days?)', text, re.IGNORECASE)
    if duration_match:
        data['duration'] = duration_match.group(1)

    # Country detection
    for keyword, country in {'bhutan': 'Bhutan', 'bali': 'Indonesia', 'andaman': 'India'}.items():
        if keyword in lower_text:
            data['country'] = country
            break

    # Cities
    cities = ['Ubud', 'Kuta', 'Port Blair', 'Havelock', 'Neil Island', 'Paro', 'Thimphu', 'Punakha']
    data['cities'] = ', '.join(sorted({c for c in cities if c.lower() in lower_text}))

    # Places
    places = ['Tiger’s Nest', 'Dochula Pass', 'Tirta Empul', 'Tanah Lot', 'Tegenungan Waterfall', 'Ubud Art Market']
    data['places'] = ', '.join(sorted({p for p in places if p.lower() in lower_text}))

    # Hotels
    hotel_match = re.findall(r'(Hotel|Resort|Villa)\s+[A-Z][a-zA-Z]+', text)
    if hotel_match:
        data['hotels'] = ', '.join(set(hotel_match))

    # Inclusions & Exclusions
    inc = re.search(r'Inclusions\s*:?(.*?)\n(?:Exclusions|Excludes|Does not include)', text, re.DOTALL | re.IGNORECASE)
    exc = re.search(r'(Exclusions|Excludes|Does not include)\s*:?(.*?)\n\n', text, re.DOTALL | re.IGNORECASE)
    if inc:
        data['inclusions'] = inc.group(1).strip().replace('\n', ', ')
    if exc:
        data['exclusions'] = exc.group(2).strip().replace('\n', ', ')

    # Activities
    activities = ['snorkeling', 'beach hopping', 'hiking', 'cultural tour', 'shopping', 'sightseeing', 'photography', 'trekking', 'dining', 'spa']
    data['activities'] = ', '.join(sorted({a for a in activities if a in lower_text}))

    # Food details
    food_keywords = ['breakfast', 'lunch', 'dinner', 'meals included', 'candlelight dinner', 'welcome drink']
    matched_food = [word for word in food_keywords if word in lower_text]
    data['food_details'] = ', '.join(matched_food)

    # Amenities
    amenity_keywords = ['private pool', 'wifi', 'air conditioning', 'jacuzzi', 'beach access', 'spa access', 'room service']
    matched_amenities = [a for a in amenity_keywords if a in lower_text]
    data['amenities'] = ', '.join(matched_amenities)

    # Itinerary block
    itinerary_lines = [line for line in lines if re.match(r'Day\s*\d+', line, re.IGNORECASE)]
    if itinerary_lines:
        data['itinerary'] = '\n'.join(itinerary_lines)

    # Defaults
    data['category'] = 'Tour Package'
    data['price'] = 'On Request'
    data['created_at'] = datetime.now().isoformat()
    data['updated_at'] = datetime.now().isoformat()

    return data

if uploaded_csv and uploaded_pdfs:
    df = pd.read_csv(uploaded_csv)

    if not all(col in df.columns for col in EXPECTED_COLUMNS):
        st.error("Your CSV file is missing one or more expected columns.")
    else:
        new_rows = []

        for pdf_file in uploaded_pdfs:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_file.read())
                pdf_path = tmp.name

            text = ""
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            os.unlink(pdf_path)

            try:
                data_dict = extract_info(text)
                new_rows.append(data_dict)
            except Exception as e:
                st.warning(f"Failed to process {pdf_file.name}: {e}")

        if new_rows:
            new_df = pd.DataFrame(new_rows)
            final_df = pd.concat([df, new_df], ignore_index=True)

            st.success("New tour packages added successfully!")
            st.dataframe(final_df.tail(len(new_rows)))

            csv_out = final_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Final CSV", data=csv_out, file_name="final_tour_packages.csv", mime="text/csv")
