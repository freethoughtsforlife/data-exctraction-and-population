import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import tempfile
import os
import ast
import google.generativeai as genai

# Load Gemini API key from Streamlit secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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

st.title("AI Tour Package Extractor (Gemini Version)")
st.write("Upload your existing tour packages CSV and itinerary PDFs. The tool will extract details and append new rows to your CSV using Google's Gemini AI.")

uploaded_csv = st.file_uploader("Upload Tour Packages CSV", type=["csv"])
uploaded_pdfs = st.file_uploader("Upload Itinerary PDFs", type=["pdf"], accept_multiple_files=True)

if uploaded_csv and uploaded_pdfs:
    df = pd.read_csv(uploaded_csv)

    if not all(col in df.columns for col in EXPECTED_COLUMNS):
        st.error("Your CSV file is missing one or more expected columns.")
    else:
        new_rows = []

        try:
            model = genai.GenerativeModel("models/gemini-pro")
        except Exception as e:
            st.error(f"Gemini model initialization failed: {e}")

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

            prompt = f"""
You are a travel domain expert AI. Extract the following fields from this itinerary and return a Python dictionary (as plain text) with keys matching:
{EXPECTED_COLUMNS}

Text:
{text}
"""

            try:
                chat = model.start_chat()
                response = chat.send_message(prompt)
                content = response.text
                data_dict = ast.literal_eval(content)
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
