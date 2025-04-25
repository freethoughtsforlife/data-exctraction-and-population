import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import tempfile
import os
import re

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

st.title("Tour Package Extractor (Rule-Based NLP Version)")
st.write("Upload your existing tour packages CSV and itinerary PDFs. The tool will extract details and append new rows using offline rules.")

uploaded_csv = st.file_uploader("Upload Tour Packages CSV", type=["csv"])
uploaded_pdfs = st.file_uploader("Upload Itinerary PDFs", type=["pdf"], accept_multiple_files=True)


def extract_info(text):
    data = {col: "" for col in EXPECTED_COLUMNS}
    
    # Title from top line
    lines = text.split('\n')
    if lines:
        data['title'] = lines[0].strip()

    # Duration
    duration_match = re.search(r'(\d+\s*Nights?\s*/\s*\d+\s*Days?)', text, re.IGNORECASE)
    if duration_match:
        data['duration'] = duration_match.group(1)

    # Country detection (basic)
    if 'bhutan' in text.lower():
        data['country'] = 'Bhutan'
    elif 'bali' in text.lower():
        data['country'] = 'Indonesia'
    elif 'andaman' in text.lower():
        data['country'] = 'India'

    # Cities or Destinations Covered
    cities = re.findall(r'\b(?:Ubud|Kuta|Port Blair|Havelock|Neil Island|Paro|Thimphu|Punakha)\b', text)
    data['cities'] = ', '.join(sorted(set(cities)))

    # Inclusions / Exclusions (basic headers)
    inclusions = re.search(r'Inclusions\s*:?\s*(.*?)\s*(Exclusions|Excludes|Does not include)', text, re.DOTALL | re.IGNORECASE)
    if inclusions:
        data['inclusions'] = inclusions.group(1).strip().replace('\n', ', ')

    exclusions = re.search(r'(Exclusions|Excludes|Does not include)\s*:?\s*(.*?)\s*(\n\n|$)', text, re.DOTALL | re.IGNORECASE)
    if exclusions:
        data['exclusions'] = exclusions.group(2).strip().replace('\n', ', ')

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
