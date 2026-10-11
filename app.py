import streamlit as st
import requests
import unicodedata

def convert_kannada(text, mode):
    url = "https://translate.googleapis.com/translate_a/single"
    
    # We explicitly separate the requests: 't' for Translation, 'rm' for Transliteration
    if mode == "Translation":
        params = {"client": "gtx", "sl": "kn", "tl": "en", "dt": "t", "q": text}
    else:
        params = {"client": "gtx", "sl": "kn", "tl": "en", "dt": "rm", "q": text}
        
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if mode == "Translation":
            # Extract translated text (e.g., Lake)
            result = "".join([item[0] for item in data[0] if item[0]])
            return result
            
        else:
            # Extract transliterated/romanized text (e.g., Kere)
            result = ""
            for item in data[0]:
                if len(item) >= 3 and item[2]:
                    result += item[2]
            
            if not result:
                return text # Failsafe
            
            # Remove special accents (turns Maḍivāḷa into Madivala)
            clean_text = ''.join(c for c in unicodedata.normalize('NFD', result) if unicodedata.category(c) != 'Mn')
            clean_text = clean_text.title()
            
            # Custom spelling preference for Madiwala
            clean_text = clean_text.replace("Madivala", "Madiwala")
            
            return clean_text
            
    except Exception as e:
        return f"Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Kannada Place Name Converter", page_icon="🌍")

st.title("Kannada Name Converter 🌍")

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
            # Keep the exact line breaks as you pasted them
            lines = user_input.split('\n')
            mode = "Translation" if "Translation" in option else "Transliteration"
            
            results = []
            for line in lines:
                if line.strip() == "":
                    results.append("") # Preserve blank lines
                else:
                    results.append(convert_kannada(line.strip(), mode))
            
            # Join it back exactly "down by down"
            final_output = "\n".join(results)
            
            st.write("### Result:")
            # Output in a single text box for easy Ctrl+C copying
            st.text_area("Copy your results from here:", value=final_output, height=200)
