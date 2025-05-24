import streamlit as st
import requests
import re
import cv2
import numpy as np
from pathlib import Path
import tempfile
import time
from ultralytics import YOLO
import torch
import xml.etree.ElementTree as ET  # For loading water polygon
from shapely.geometry import Point, Polygon  # For water polygon logic
import os
import smtplib                 # For sending emails
from email.mime.text import MIMEText # For formatting emails

# ─── Streamlit page config & CSS ───────────────────────────────
st.set_page_config(page_title="Swimmer Detection", page_icon="🏊‍♂️", layout="centered")
st.markdown("""
<style>
.stButton>button { width:100%; background:#f0f2f6; color:#262730; border:none;
  padding:10px; border-radius:5px; margin:5px 0; }
.stSlider > div[data-baseweb="slider"] { color: #f63366; }
.big-title { font-size: 2.5rem; font-weight: 700; margin-bottom: 1rem; }
.section-header { font-size: 1.3rem; font-weight: 600; margin-top: 2rem; margin-bottom: 0.5rem; }
.result-count { font-size: 1.2rem; font-weight: 500; color: #f63366; }
</style>
""", unsafe_allow_html=True)

# ─── Session state defaults ─────────────────────────────────────
defaults = {
    'page': 1,
    'video_file': None,
    'video_url': "",
    'analysis_complete': False,
    'people_in_water_count': 0,
    'people_on_beach_count': 0,
    'processed_video_path': None
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

def navigate_to(page: int):
    st.session_state.page = max(1, min(3, page))

# ─── PAGE 1: Upload or Paste URL (with .m3u8 scraping) ──────────
def show_page_1():
    st.markdown('<div class="big-title">🏊‍♂️ Swimmer Detection App</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">1️⃣ Upload or Paste Video URL</div>', unsafe_allow_html=True)
    st.write("Upload a local video or paste a public video/stream URL (e.g. Surfline link). For best results, use a short video.")

    # 1. capture raw input
    raw_url = st.text_input("Public video/stream URL:", st.session_state.video_url).strip()

    # 2. if it's not a direct .mp4/.mov/.avi/.m3u8, try to scrape an HLS playlist
    final_url = ""
    if raw_url:
        if raw_url.lower().endswith(('.mp4', '.mov', '.avi', '.m3u8')):
            final_url = raw_url
        else:
            st.info("Fetching page and looking for an HLS (`.m3u8`) playlist…")
            try:
                r = requests.get(raw_url, timeout=10)
                m = re.search(r'https://[^\s"\'<>]+?\.m3u8', r.text)
                if m:
                    final_url = m.group(0)
                    st.success("Found stream: " + final_url)
                else:
                    st.error("No `.m3u8` link found on that page.")
            except Exception as e:
                st.error(f"Failed to fetch page: {e}")

    # 3. save into session
    st.session_state.video_url = final_url

    # 4. preview side-by-side
    col1, col2 = st.columns(2)
    with col1:
        if final_url:
            st.video(final_url)
    with col2:
        uploaded = st.file_uploader("Or upload a 5-minute video:", type=['mp4','mov','avi'])
        if uploaded:
            st.session_state.video_file = uploaded
            st.session_state.video_url = ""  # clear any scraped URL
            st.video(uploaded)

    # 5. proceed
    if st.button("➡️ Analyse"):
        if not (st.session_state.video_file or st.session_state.video_url):
            st.warning("Please upload a file or supply a working video/stream URL.")
        else:
            st.session_state.analysis_complete = False
            navigate_to(2)

# ─── PAGE 2: Analysis In Progress ────────────────────────────────
MODEL_PATH           = "best.pt"
ANNOTATIONS_XML_PATH = "annotations.xml"
PERSON_CLASS_ID      = 0

@st.cache_resource
def load_model(path):
    try:
        model = YOLO(path)
        if torch.cuda.is_available():
            model.to("cuda")
        return model
    except Exception as e:
        st.error(f"Error loading model '{path}': {e}")
        return None

@st.cache_data
def load_polygon(xml_path, label="water"):
    p = Path(xml_path)
    if not p.exists():
        st.error(f"Annotation XML not found: {xml_path}")
        return None
    tree = ET.parse(p)
    root = tree.getroot()
    pts = []
    for poly in root.findall(".//polygon"):
        if poly.attrib.get("label") == label:
            for pt in poly.attrib["points"].split(';'):
                x, y = map(float, pt.split(','))
                pts.append((x, y))
            break
    if not pts:
        st.error(f"No polygon with label='{label}' in XML")
        return None
    return Polygon(pts)

# --- Email Notification Function ---
def send_email_notification(subject, body_text, recipient_email):
    sender_email = "kjm4540@gmail.com"
    sender_app_password = "Tkadk106"
    smtp_server_address = "smtp.gmail.com"
    smtp_port_str = "587"

    if not all([sender_email, sender_app_password, smtp_server_address, smtp_port_str, recipient_email]):
        error_msg = "Email configuration (SENDER_EMAIL, SENDER_APP_PASSWORD, SMTP_SERVER, SMTP_PORT, LIFEGUARD_RECIPIENT_EMAIL) missing in environment variables. Email not sent."
        st.error(error_msg)
        print(f"ERROR: {error_msg}")
        return False

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        error_msg = f"Invalid SMTP_PORT: '{smtp_port_str}'. Must be an integer. Email not sent."
        st.error(error_msg)
        print(f"ERROR: {error_msg}")
        return False

    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_server_address, smtp_port) as server:
            server.ehlo()  # Say hello to server
            server.starttls() # Enable security
            server.ehlo()  # Say hello again after TLS
            server.login(sender_email, sender_app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            st.info(f"Email notification sent to {recipient_email}!")
            print(f"Email notification sent to {recipient_email}.")
        return True
    except Exception as e:
        st.error(f"Failed to send email notification: {e}")
        print(f"Error sending email: {e}")
        return False

def process_video(source, model, water_poly, max_frames_to_process=None):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        st.error(f"Cannot open video/stream: {source}")
        return None, 0, 0

    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    if max_frames_to_process is not None:
        total = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or -1, max_frames_to_process)
    else:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or -1

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.close()
    out = cv2.VideoWriter(tmp.name,
                          cv2.VideoWriter_fourcc(*'mp4v'),
                          fps, (w, h))

    water_count = beach_count = 0
    progress = st.progress(0.0)
    status = st.empty()
    frame_i = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)[0]
        for box in results.boxes:
            if int(box.cls[0]) != PERSON_CLASS_ID:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx, cy = (x1 + x2)//2, y2
            in_water = water_poly.contains(Point(cx, cy))
            color = (255, 0, 0) if in_water else (0, 255, 0)
            label = "Water" if in_water else "Beach"
            if in_water:
                water_count += 1
            else:
                beach_count += 1

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        text = f"In Water: {water_count} | On Beach: {beach_count}"
        cv2.putText(frame, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        out.write(frame)
        frame_i += 1

        if total > 0:
            progress.progress(frame_i/total)
            status.text(f"Frame {frame_i}/{total}")
        else:
            status.text(f"Frame {frame_i}")

        if max_frames_to_process and frame_i >= max_frames_to_process:
            break

    cap.release()
    out.release()
    return tmp.name, water_count, beach_count

def show_page_2():
    st.markdown('<div class="section-header">2️⃣ Processing & Results</div>', unsafe_allow_html=True)
    src_file = st.session_state.video_file
    src_url  = st.session_state.video_url

    if not (src_file or src_url):
        st.warning("Upload a file or paste a URL first.")
        if st.button("⏪ Back"): navigate_to(1)
        return

    # --- Frame slider for user control ---
    st.markdown("<b>How many frames to process?</b>", unsafe_allow_html=True)
    max_frames = st.slider("Select number of frames for quick analysis", min_value=10, max_value=200, value=30, step=5)

    model      = load_model(MODEL_PATH)
    water_poly = load_polygon(ANNOTATIONS_XML_PATH, label="water")
    if not (model and water_poly):
        if st.button("⏪ Back to Upload"): navigate_to(1)
        return

    # Only run analysis if not already done for this session
    if not st.session_state.analysis_complete:
        if src_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(src_file.name).suffix) as tmp_video_file:
                tmp_video_file.write(src_file.getbuffer())
                source_for_processing = tmp_video_file.name
        else:
            source_for_processing = src_url

        out_path, wc, bc = process_video(source_for_processing, model, water_poly, max_frames_to_process=max_frames)
        if src_file and 'source_for_processing' in locals() and os.path.exists(source_for_processing):
            if source_for_processing != src_file:
                try:
                    os.unlink(source_for_processing)
                except Exception as e:
                    st.warning(f"Could not delete temp video file {source_for_processing}: {e}")

        if out_path:
            st.session_state.processed_video_path   = out_path
            st.session_state.people_in_water_count  = wc
            st.session_state.people_on_beach_count  = bc
            st.session_state.analysis_complete      = True
            st.success("✅ Analysis complete!")

            # --- Email Notification Logic ---
            if wc > 0:
                lifeguard_email = os.environ.get('LIFEGUARD_RECIPIENT_EMAIL')
                if lifeguard_email:
                    email_subject = "Lifeguard Alert: Swimmers Detected in Water"
                    email_body = f"""Automated Alert System:\n\nNumber of people detected in the water: {wc}\nNumber of people detected on the beach: {bc}\n\nPlease review the video footage from the system and assess the situation immediately."""
                    send_email_notification(email_subject, email_body, lifeguard_email)
                else:
                    st.warning("LIFEGUARD_RECIPIENT_EMAIL environment variable not set. Cannot send email alert.")
            else:
                st.info("No people detected in the water, so no email alert sent.")
        else:
            st.error("Video processing did not complete successfully.")
            if st.button("⏪ Back to Upload"): navigate_to(1)
            return

    # --- Show results directly after analysis ---
    st.markdown('<div class="section-header">🎬 Annotated Video</div>', unsafe_allow_html=True)
    st.video(st.session_state.processed_video_path)
    st.markdown('<div class="section-header">📊 Final Counts</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-count">In Water: <b>{st.session_state.people_in_water_count}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-count">On Beach: <b>{st.session_state.people_on_beach_count}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-count">Total: <b>{st.session_state.people_in_water_count + st.session_state.people_on_beach_count}</b></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("🔄 Analyse Another Video"):
        for k in ['video_file','video_url','analysis_complete']:
            st.session_state[k] = defaults[k]
        navigate_to(1)

# ─── PAGE 3: Results ─────────────────────────────────────────────
def show_page_3():
    st.title("3️⃣ Results")
    if not st.session_state.analysis_complete:
        st.warning("No results to show yet.")
        if st.button("⏪ Back"): navigate_to(2)
        return

    st.subheader("Annotated Video")
    st.video(st.session_state.processed_video_path)

    st.subheader("Final Counts")
    st.markdown(f"- **In Water:** {st.session_state.people_in_water_count}")
    st.markdown(f"- **On Beach:** {st.session_state.people_on_beach_count}")
    st.markdown(f"- **Total:** {st.session_state.people_in_water_count + st.session_state.people_on_beach_count}")

    if st.button("🔄 Analyse Again"):
        for k in ['video_file','video_url','analysis_complete']:
            st.session_state[k] = defaults[k]
        navigate_to(1)

# ─── App entrypoint ─────────────────────────────────────────────
def main():
    if st.session_state.page == 1:
        show_page_1()
    elif st.session_state.page == 2:
        show_page_2()
    else:
        show_page_3()

if __name__ == "__main__":
    main()
