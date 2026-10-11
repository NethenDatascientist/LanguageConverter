import streamlit as st
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import unicodedata
import re

def convert_kannada(text, mode):
    if mode == "Translation":
        # Uses Google API just for translation
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "kn", "tl": "en", "dt": "t", "q": text}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return "".join([item[0] for item in data[0] if item[0]])
        except Exception as e:
            return f"Error: {str(e)}"
    
    else:
        # Uses indic-transliteration for 100% accurate, offline Romanization
        try:
            # 1. Convert to IAST (This perfectly preserves 'a' at the end of words like Agara)
            iast_text = transliterate(text, sanscript.KANNADA, sanscript.IAST)
            
            # 2. Strip off special phonetic accents (turns ē -> e, ḍ -> d)
            clean_text = ''.join(c for c in unicodedata.normalize('NFD', iast_text) if unicodedata.category(c) != 'Mn')
            
            # 3. Fix the Anusvara (the 'Bam' vs 'Ban' problem). 
            # Changes 'm' to 'n' if it comes right before consonants like d, t, k, g, c, j, s.
            clean_text = re.sub(r'm([kgcjtdsKGCJTDS])', r'n\1', clean_text)
            
            # 4. Standardize capitalization
            clean_text = clean_text.title()
            
            # 5. Apply your specific override for Madivala -> Madiwala
            clean_text = clean_text.replace("Madivala", "Madiwala")
            
            return clean_text
        except Exception as e:
            return f"Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Kannada Place Name Converter", page_icon="🌍")

st.title("Kannada to English Translator & Transliterator 🌍")
st.caption("Developed by Nethen")

# 1. Input Area
user_input = st.text_area(
    "Paste your list here (line by line):", 
    value="ಬಂಡೇಕೊಡಿಗೇಹಳ್ಳಿ ಕೆರೆ\nಅಗರ ಕೆರೆ\nಮಡಿವಾಳ ಕೆರೆ",
    height=150
)

# 2. Options
option = st.radio(
    "Choose output format:",
    ("Translation (e.g., Bandekodigehalli Lake)", "Transliteration (e.g., Bandekodigehalli Kere)")
)

# 3. Action
if st.button("Convert All"):
    if user_input.strip() == "":
        st.warning("Please enter some text.")
    else:
        with st.spinner("Converting..."):
            lines = user_input.split('\n')
            mode = "Translation" if "Translation" in option else "Transliteration"
            
            results = []
            for line in lines:
                if line.strip() == "":
                    results.append("") # Preserve blank lines perfectly
                else:
                    results.append(convert_kannada(line.strip(), mode))
            
            # Join it back exactly "down by down"
            final_output = "\n".join(results)
            
            st.write("### Result:")
            # Output in a single text box for easy Ctrl+C copying
            st.text_area("Copy your results from here:", value=final_output, height=200)
