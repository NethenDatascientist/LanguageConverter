import streamlit as st
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import unicodedata
import re
import json
import urllib.request
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta


# --- SILENT VISITOR TRACKER & EMAIL ALERT ---
def get_visitor_info():
    """Captures visitor IP, approximate location/ISP, device, and timestamp silently."""
    headers = getattr(st.context, "headers", {}) or {}

    # 1. Get real client IP (prioritize X-Forwarded-For on Streamlit Cloud)
    forwarded = headers.get("X-Forwarded-For", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = getattr(st.context, "ip_address", None) or "Unknown"

    # 2. Browser & System details
    user_agent = headers.get("User-Agent", "Unknown Device/Browser")
    platform = headers.get("Sec-Ch-Ua-Platform", "Unknown OS").strip('"')
    tz = getattr(st.context, "timezone", None) or "Unknown Timezone"
    locale = getattr(st.context, "locale", None) or headers.get(
        "Accept-Language", "Unknown"
    )

    # 3. Geolocation lookup from IP
    location_str = "Location unavailable"
    isp_str = "Unknown ISP"
    if ip and ip not in ["Unknown", "127.0.0.1", "::1"]:
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "success":
                    location_str = f"{data.get('city', '')}, {data.get('regionName', '')}, {data.get('country', '')}"
                    isp_str = data.get("isp", "Unknown ISP")
        except Exception:
            pass

    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime(
        "%Y-%m-%d %I:%M:%S %p IST"
    )

    return (
        f"• Time: {ist_now}\n"
        f"• IP Address: {ip}\n"
        f"• Location: {location_str}\n"
        f"• ISP / Network: {isp_str}\n"
        f"• Platform: {platform}\n"
        f"• Timezone: {tz}\n"
        f"• Language: {locale}\n"
        f"• User Agent: {user_agent}\n"
    )


def notify_visit(event_label="Opened the App"):
    """Prints visitor details to Streamlit console logs and sends an email alert."""
    try:
        info = get_visitor_info()
        print(
            f"\n--- 🔔 VISITOR TRACKER ({event_label}) ---\n{info}------------------------------------------",
            flush=True,
        )

        sender_email = st.secrets.get("NOTIFY_EMAIL")
        app_password = st.secrets.get("NOTIFY_APP_PASSWORD")
        receiver_email = st.secrets.get("RECEIVER_EMAIL", "dsdanethen@gmail.com")

        if sender_email and app_password:
            msg = EmailMessage()
            msg["Subject"] = f"🔔 KAN-ENG Converter: {event_label}"
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg.set_content(
                f"Hello Nethen,\n\nActivity detected on your KAN-ENG Place Name Converter ({event_label}):\n\n{info}"
            )

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
    except Exception:
        pass
# --- END TRACKER FUNCTIONS ---


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

st.title("KAN-ENG Converter")
st.markdown("**Developed by Nethen**")

# Trigger once per session as soon as someone opens the link
if "visit_tracked" not in st.session_state:
    notify_visit("Opened the App Link")
    st.session_state.visit_tracked = True

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
            
            # Log when the user clicks Convert All
            non_empty_count = len([l for l in lines if l.strip()])
            notify_visit(f"Clicked Convert All ({mode} - {non_empty_count} lines)")
            
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
