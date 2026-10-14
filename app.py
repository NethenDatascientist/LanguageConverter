import streamlit as st
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import unicodedata
import re
import json
import uuid
import ipaddress
import urllib.request
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta


# --- ADVANCED SILENT VISITOR TRACKER & EMAIL ALERT ---
def parse_user_agent_simple(ua):
    """Translates the raw User-Agent string into a clean Device, OS, and Browser summary."""
    if not ua or ua == "Unknown":
        return "Unknown Device | Unknown Browser"

    # Detect OS / Device
    if "iPhone" in ua:
        os_match = re.search(r"iPhone OS ([\d_]+)", ua)
        os_ver = os_match.group(1).replace("_", ".") if os_match else ""
        os_str = f"Apple iPhone (iOS {os_ver})".strip()
    elif "iPad" in ua:
        os_str = "Apple iPad (iPadOS)"
    elif "Android" in ua:
        and_match = re.search(r"Android\s+([\d.]+)(?:;\s*([^;)]+))?", ua)
        if and_match:
            ver = and_match.group(1)
            model = and_match.group(2).strip() if and_match.group(2) else "Phone"
            os_str = f"Android {ver} ({model})"
        else:
            os_str = "Android Device"
    elif "Windows NT 10.0" in ua:
        os_str = "Windows 10/11 PC (64-bit)" if "Win64" in ua or "x64" in ua else "Windows 10/11 PC"
    elif "Windows NT" in ua:
        os_str = "Windows PC (Older Version)"
    elif "Mac OS X" in ua:
        os_str = "Apple Mac (macOS)"
    elif "X11" in ua or "Linux" in ua:
        os_str = "Linux Server / Desktop (X11)"
    else:
        os_str = "Unknown OS"

    # Detect Browser (order matters because Chrome/Edge include 'Safari')
    if "Edg/" in ua or "EdgA/" in ua or "EdgiOS/" in ua:
        m = re.search(r"Edg[A-Za-z]*/([\d.]+)", ua)
        browser_str = f"Microsoft Edge ({m.group(1) if m else ''})"
    elif "OPR/" in ua or "Opera" in ua:
        m = re.search(r"OPR/([\d.]+)", ua)
        browser_str = f"Opera ({m.group(1) if m else ''})"
    elif "SamsungBrowser/" in ua:
        m = re.search(r"SamsungBrowser/([\d.]+)", ua)
        browser_str = f"Samsung Internet ({m.group(1) if m else ''})"
    elif "Firefox/" in ua or "FxiOS/" in ua:
        m = re.search(r"(?:Firefox|FxiOS)/([\d.]+)", ua)
        browser_str = f"Mozilla Firefox ({m.group(1) if m else ''})"
    elif "CriOS/" in ua:
        m = re.search(r"CriOS/([\d.]+)", ua)
        browser_str = f"Google Chrome on iOS ({m.group(1) if m else ''})"
    elif "Chrome/" in ua:
        m = re.search(r"Chrome/([\d.]+)", ua)
        browser_str = f"Google Chrome ({m.group(1) if m else ''})"
    elif "Safari/" in ua and "Version/" in ua:
        m = re.search(r"Version/([\d.]+)", ua)
        browser_str = f"Apple Safari ({m.group(1) if m else ''})"
    else:
        browser_str = "Other / Bot Browser"

    return f"{os_str} | {browser_str}"


def extract_best_ip(headers):
    """Checks all proxy headers and filters out internal 10.x.x.x IPs to find the public IP."""
    candidates = []
    header_keys = [
        "Cf-Connecting-Ip",
        "True-Client-Ip",
        "X-Real-Ip",
        "X-Client-Ip",
        "X-Forwarded-For",
    ]

    for key in header_keys:
        val = headers.get(key) or headers.get(key.lower())
        if val:
            for part in val.split(","):
                ip_str = part.strip()
                if ip_str and ip_str not in candidates:
                    candidates.append(ip_str)

    ctx_ip = getattr(st.context, "ip_address", None)
    if ctx_ip and ctx_ip not in candidates:
        candidates.append(ctx_ip)

    # Pick the first public (non-private, non-loopback) IP if available
    public_ip = None
    for cand in candidates:
        try:
            ip_obj = ipaddress.ip_address(cand)
            if not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local):
                public_ip = cand
                break
        except ValueError:
            continue

    best_ip = public_ip or (candidates[0] if candidates else "Unknown")
    all_ips_str = ", ".join(candidates) if candidates else "Unknown"
    return best_ip, all_ips_str


def get_visitor_info(extra_details=None):
    """Captures all available network, device, browser, session, and location metadata."""
    headers = getattr(st.context, "headers", {}) or {}

    # 1. Session ID (to track multiple actions by the same visitor tab)
    if "tracker_session_id" not in st.session_state:
        st.session_state.tracker_session_id = str(uuid.uuid4())[:8]
    session_id = st.session_state.tracker_session_id

    # 2. IP Resolution
    best_ip, all_ips_str = extract_best_ip(headers)

    # 3. Browser, OS, and Client Hint Headers
    user_agent = headers.get("User-Agent", "Unknown")
    readable_device = parse_user_agent_simple(user_agent)
    sec_ch_ua = headers.get("Sec-Ch-Ua", "Not provided").replace('"', "")
    platform_hint = headers.get("Sec-Ch-Ua-Platform", "Not provided").strip('"')
    mobile_hint = headers.get("Sec-Ch-Ua-Mobile", "")
    is_mobile = (
        "Yes (Mobile)"
        if mobile_hint == "?1" or any(k in user_agent for k in ["Mobile", "Android", "iPhone"])
        else "No (Desktop)"
    )

    # 4. Referer, URL, & Query Parameters
    referer = headers.get("Referer") or headers.get("referer") or "Direct Link / Bookmark / App"
    app_url = getattr(st.context, "url", None) or headers.get("Host", "Unknown URL")
    is_embedded = getattr(st.context, "is_embedded", False)
    query_params = dict(st.query_params) if hasattr(st, "query_params") else {}
    query_str = json.dumps(query_params, ensure_ascii=False) if query_params else "None"

    # 5. Timezone, Language, & UI Theme
    tz = getattr(st.context, "timezone", None) or "Unknown Timezone"
    tz_offset = getattr(st.context, "timezone_offset", None)
    tz_display = f"{tz} (UTC offset: {tz_offset} min)" if tz_offset is not None else tz
    locale = getattr(st.context, "locale", None) or "Unknown"
    accept_lang = headers.get("Accept-Language", "Unknown")

    theme_obj = getattr(st.context, "theme", None)
    theme_type = getattr(theme_obj, "type", "Unknown") if theme_obj else "Unknown"

    # 6. Cloud Proxy Country Hint (if Cloudflare/GCP passes it)
    cloud_country = (
        headers.get("Cf-Ipcountry")
        or headers.get("X-Appengine-Country")
        or headers.get("X-Country-Code")
        or "N/A"
    )

    # 7. Cookies Summary (keys only, for privacy/clarity)
    cookies = getattr(st.context, "cookies", {}) or {}
    cookie_keys = ", ".join(list(cookies.keys())) if cookies else "None"

    # 8. Extended Geolocation & Network Lookup from IP
    location_str = "Location unavailable (Private/Proxy IP)"
    coords_str = "Unavailable"
    isp_str = "Unknown ISP"
    network_flags = "Unavailable"

    if best_ip and best_ip not in ["Unknown", "127.0.0.1", "::1"]:
        try:
            ip_obj = ipaddress.ip_address(best_ip)
            if not ip_obj.is_private:
                fields = "status,country,regionName,city,zip,lat,lon,isp,org,as,mobile,proxy,hosting"
                url = f"http://ip-api.com/json/{best_ip}?fields={fields}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "success":
                        city = data.get("city", "")
                        region = data.get("regionName", "")
                        country = data.get("country", "")
                        pincode = data.get("zip", "")
                        location_str = f"{city}, {region}, {country} (PIN: {pincode})"
                        coords_str = f"{data.get('lat')}, {data.get('lon')} (https://www.google.com/maps?q={data.get('lat')},{data.get('lon')})"
                        isp_str = f"{data.get('isp', '')} | Org: {data.get('org', '')} | {data.get('as', '')}"
                        network_flags = (
                            f"Cellular/Mobile Network: {data.get('mobile')} | "
                            f"VPN/Proxy: {data.get('proxy')} | "
                            f"DataCenter/Bot: {data.get('hosting')}"
                        )
        except Exception:
            pass

    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime(
        "%Y-%m-%d %I:%M:%S %p IST"
    )

    report = (
        f"• Time (IST): {ist_now}\n"
        f"• Session ID: {session_id}\n"
        f"• Easy Summary: {readable_device}\n"
        f"• Mobile Device: {is_mobile}\n"
        f"• Primary IP: {best_ip}\n"
        f"• All Detected IPs: {all_ips_str}\n"
        f"• Cloud Country Header: {cloud_country}\n"
        f"• Location: {location_str}\n"
        f"• Approx Coordinates: {coords_str}\n"
        f"• ISP & Org: {isp_str}\n"
        f"• Connection Flags: {network_flags}\n"
        f"• Came From (Referer): {referer}\n"
        f"• Accessed URL: {app_url} (Embedded: {is_embedded})\n"
        f"• URL Query Tags: {query_str}\n"
        f"• System Timezone: {tz_display}\n"
        f"• Primary Locale: {locale} (All Languages: {accept_lang})\n"
        f"• Browser Theme: {theme_type}\n"
        f"• OS Platform Hint: {platform_hint}\n"
        f"• Browser Brand Hint: {sec_ch_ua}\n"
        f"• Active Cookies: {cookie_keys}\n"
        f"• Raw User-Agent: {user_agent}\n"
    )

    if extra_details:
        report += f"• Action Details: {extra_details}\n"

    return report


def notify_visit(event_label="Opened the App", extra_details=None):
    """Prints visitor details to Streamlit console logs and sends an email alert."""
    try:
        info = get_visitor_info(extra_details=extra_details)
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
            
            # Log when the user clicks Convert All, including a sample of their input text
            non_empty_lines = [l.strip() for l in lines if l.strip()]
            sample_preview = ", ".join(non_empty_lines[:5])
            if len(non_empty_lines) > 5:
                sample_preview += f" ... (+{len(non_empty_lines) - 5} more)"
            
            notify_visit(
                event_label=f"Clicked Convert All ({mode} - {len(non_empty_lines)} lines)",
                extra_details=f"Input Sample: {sample_preview}"
            )
            
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
