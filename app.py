import streamlit as st
import requests
import unicodedata

def convert_kannada(text, mode):
    # Using a highly stable Google API endpoint that avoids the strict rate limits
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "kn",
        "tl": "en",
        "dt": ["t", "rm"], # 't' gets the Translation, 'rm' gets the Romanization (Transliteration)
        "q": text
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        translation = ""
        transliteration = ""
        
        # Parse the Google API response safely
        for item in data[0]:
            if item[0] is not None:
                translation += item[0]
            if item[0] is None and len(item) >= 3 and item[2] is not None:
                transliteration += item[2]
                
        if mode == "Translation":
            return translation
        else:
            if not transliteration:
                transliteration = translation # Fallback
            
            # This removes weird accents (e.g., turning Baṇḍēkoḍigēhaḷḷi into Bandekodigehalli)
            clean_text = ''.join(c for c in unicodedata.normalize('NFD', transliteration) if unicodedata.category(c) != 'Mn')
            
            # Capitalize the first letter of each word
            return clean_text.title()
            
    except Exception as e:
        return f"Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Kannada Place Name Converter", page_icon="🌍")

st.title("Kannada Name Converter 🌍")
st.markdown("Convert multiple Kannada locations into English. You can add them **line by line** below.")

# 1. Typeable Multi-line Box
user_input = st.text_area(
    "Enter Kannada text here (one name per line):", 
    value="ಬಂಡೇಕೊಡಿಗೇಹಳ್ಳಿ ಕೆರೆ\nಅಗರ ಕೆರೆ\nಮಡಿವಾಳ ಕೆರೆ",
    height=150
)

# 2. Options
option = st.radio(
    "How would you like to convert?",
    ("Translation (e.g., Bandekodigehalli Lake)", "Transliteration (e.g., Bandekodigehalli Kere)")
)

# 3. Action Button
if st.button("Convert All"):
    if user_input.strip() == "":
        st.warning("Please enter some Kannada text.")
    else:
        with st.spinner("Converting..."):
            # Split the input "down by down" (line by line)
            lines = [line.strip() for line in user_input.split('\n') if line.strip() != ""]
            
            # Determine which mode to use based on the radio button
            mode = "Translation" if "Translation" in option else "Transliteration"
            
            st.write("### Results:")
            for line in lines:
                result = convert_kannada(line, mode)
                st.success(f"**Original:** {line}  \n**Result:** {result}")
