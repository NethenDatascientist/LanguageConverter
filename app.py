import streamlit as st
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import unicodedata
import re

def convert_kannada(text, mode):
    if mode == "Translation":
        # ಗೂಗಲ್ API ಅನುವಾದಕ್ಕಾಗಿ
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "kn", "tl": "en", "dt": "t", "q": text}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = "".join([item[0] for item in data[0] if item[0]])
            
            # ಗೂಗಲ್ ಅನುವಾದದಲ್ಲಿ ಬರುವ ಸಾಮಾನ್ಯ ತಪ್ಪುಗಳನ್ನು ಸರಿಪಡಿಸಲು (ಉದಾಹರಣೆಗೆ: Sastri -> Shastri)
            result = result.replace("sastri", "shastri").replace("Sastri", "Shastri")
            
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    else:
        # 100% ನಿಖರವಾದ ಲಿಪ್ಯಂತರಕ್ಕಾಗಿ indic-transliteration
        try:
            # 1. IAST ಗೆ ಪರಿವರ್ತನೆ (ಇದು ಕೊನೆಯ 'a' ಅನ್ನು ಉಳಿಸಿಕೊಳ್ಳುತ್ತದೆ)
            iast_text = transliterate(text, sanscript.KANNADA, sanscript.IAST)
            
            # 2. 'ಶ' ಮತ್ತು 'ಷ' ಅಕ್ಷರಗಳಿಗೆ 'sh' ಶಬ್ದವನ್ನು ಸೇರಿಸುವುದು
            # IAST ನಲ್ಲಿ 'ಶ' = 'ś' ಮತ್ತು 'ಷ' = 'ṣ' ಆಗಿರುತ್ತದೆ. 
            iast_text = iast_text.replace('ś', 'sh').replace('Ś', 'Sh')
            iast_text = iast_text.replace('ṣ', 'sh').replace('Ṣ', 'Sh')
            
            # 3. ವಿಶೇಷ ಉಚ್ಚಾರಣಾ ಚಿಹ್ನೆಗಳನ್ನು ತೆಗೆಯುವುದು (ಉದಾ: ē -> e)
            clean_text = ''.join(c for c in unicodedata.normalize('NFD', iast_text) if unicodedata.category(c) != 'Mn')
            
            # 4. 'm' ಅನ್ನು 'n' ಆಗಿ ಬದಲಾಯಿಸುವುದು (Bam ಬದಲು Ban)
            clean_text = re.sub(r'm([kgcjtdsKGCJTDS])', r'n\1', clean_text)
            
            # 5. ಅಕ್ಷರಗಳ Standard capitalization
            clean_text = clean_text.title()
            
            # 6. Madiwala ನಂತಹ ನಿರ್ದಿಷ್ಟ ಪದಗಳ ಕಸ್ಟಮ್ ಸರಿಪಡಿಸುವಿಕೆ
            clean_text = clean_text.replace("Madivala", "Madiwala")
            
            return clean_text
        except Exception as e:
            return f"Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="Kannada Place Name Converter", page_icon="🌍")

st.title("KAN to ENG Translator & Transliterator🌍")
st.markdown("**Developed by Nethen**")

# 1. Input Area
user_input = st.text_area(
    "Paste your list here (line by line):", 
    value="ಬಂಡೇಕೊಡಿಗೇಹಳ್ಳಿ ಕೆರೆ\nಅಗರ ಕೆರೆ\nಮಡಿವಾಳ ಕೆರೆ\nಚಿಕ್ಕಲಿಂಗಶಾಸ್ತ್ರಿ ಕೆರೆ",
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
                    results.append("") # ಖಾಲಿ ಸಾಲುಗಳನ್ನು ಹಾಗೆಯೇ ಉಳಿಸಿಕೊಳ್ಳಲು
                else:
                    results.append(convert_kannada(line.strip(), mode))
            
            # ಲೈನ್‌ಗಳನ್ನು ಮತ್ತೆ ಒಟ್ಟುಗೂಡಿಸುವುದು
            final_output = "\n".join(results)
            
            st.write("### Result:")
            # ಸುಲಭವಾಗಿ ಕಾಪಿ ಮಾಡಲು ಒಂದೇ ಟೆಕ್ಸ್ಟ್ ಬಾಕ್ಸ್
            st.text_area("Copy your results from here:", value=final_output, height=200)
