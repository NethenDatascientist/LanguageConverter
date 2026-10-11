import streamlit as st
from deep_translator import GoogleTranslator
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Set up the page title and layout
st.set_page_config(page_title="Kannada Place Name Converter", page_icon="🌍")

st.title("Kannada Name Converter 🌍")
st.markdown("Convert Kannada locations into English by either **translating** the meaning (e.g., Lake) or **transliterating** the sound (e.g., Kere).")

# 1. Typeable Input Box
user_input = st.text_input("Enter Kannada text here:", value="ಬಂಡೇಕೊಡಿಗೇಹಳ್ಳಿ ಕೆರೆ")

# 2. Options to choose conversion style
option = st.radio(
    "How would you like to convert it?",
    ("Translation (e.g., Bansekodihalli Lake)", "Transliteration (e.g., Bansekodihalli Kere)")
)

# 3. Action Button
if st.button("Convert"):
    if user_input.strip() == "":
        st.warning("Please enter some Kannada text.")
    else:
        with st.spinner("Converting..."):
            
            if "Translation" in option:
                try:
                    # Translates the actual meaning to English
                    translated_text = GoogleTranslator(source='kn', target='en').translate(user_input)
                    st.success(f"**Result:** {translated_text}")
                except Exception as e:
                    st.error(f"Translation Error: {e}")
            
            elif "Transliteration" in option:
                try:
                    # Converts phonetically to English characters (ITRANS scheme)
                    phonetic_text = transliterate(user_input, sanscript.KANNADA, sanscript.ITRANS)
                    
                    # ITRANS uses uppercase for long vowels (e.g., kEre). 
                    # .title() cleans it up to standard casing (e.g., Kere)
                    clean_text = phonetic_text.title()
                    
                    st.success(f"**Result:** {clean_text}")
                except Exception as e:
                    st.error(f"Transliteration Error: {e}")
