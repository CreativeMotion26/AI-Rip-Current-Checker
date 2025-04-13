import streamlit as st
import cv2
import numpy as np
from pathlib import Path
import tempfile
import time

# Set page config
st.set_page_config(
    page_title="Rip Current Checker",
    page_icon="🌊",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #F8F9FA;
        color: #000000;
        border: none;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        font-size: 16px;
    }
    .main {
        padding: 2rem;
    }
    .title {
        text-align: center;
        margin-bottom: 2rem;
    }
    .nav-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        margin-top: 2rem;
        padding: 1rem;
    }
    .nav-item {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #dee2e6;
        border-radius: 50%;
        cursor: pointer;
        font-size: 14px;
        color: #6c757d;
        text-decoration: none;
        background: white;
    }
    .nav-item.active {
        background: #E94666;
        color: white;
        border: none;
    }
    .nav-arrow {
        color: #6c757d;
        font-size: 24px;
        cursor: pointer;
        text-decoration: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'video_file' not in st.session_state:
    st.session_state.video_file = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'history' not in st.session_state:
    st.session_state.history = []
if 'camera_on' not in st.session_state:
    st.session_state.camera_on = False

def navigate_to(page):
    st.session_state.page = page

def toggle_camera():
    st.session_state.camera_on = not st.session_state.camera_on

# Page 1: Instructions and Camera Access
def show_page_1():
    st.title("Rip Current Checker")
    
    # Tips section
    st.markdown("""
    ### Tips for Best Result
    1. Set your camera to 4K resolution
    2. Stand a few meters from the water's edge
    3. Use landscape mode
    4. Take a 5-second video, holding steady
    """)
    
    # Camera functionality
    if st.button("Access Camera", on_click=toggle_camera):
        st.session_state.camera_on = True
    
    if st.session_state.camera_on:
        camera_placeholder = st.empty()
        video_capture = cv2.VideoCapture(0)  # 0 is usually the default webcam
        
        if video_capture.isOpened():
            try:
                while st.session_state.camera_on:
                    ret, frame = video_capture.read()
                    if ret:
                        # Convert BGR to RGB
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        camera_placeholder.image(frame, channels="RGB")
                        
                        # Add a stop button
                        if st.button("Stop Camera"):
                            st.session_state.camera_on = False
                            break
            finally:
                video_capture.release()
        else:
            st.error("Could not access the camera. Please check your camera permissions.")
    
    st.button("Access Video", on_click=navigate_to, args=(2,))
    
    # Navigation
    show_navigation(1)

# Page 2: Video Upload
def show_page_2():
    st.title("Upload Video")
    
    uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'mov', 'avi'])
    
    if uploaded_file:
        st.session_state.video_file = uploaded_file
        st.video(uploaded_file)
        
        if st.button("Analyse"):
            navigate_to(3)
    
    show_navigation(2)

# Page 3: Analysis Progress
def show_page_3():
    st.title("Analysis in Progress")
    
    progress_text = "Analysis in progress...\nEstimated completion in 1 minute and 30 seconds..."
    progress_bar = st.progress(0)
    
    # Simulate progress
    for i in range(100):
        time.sleep(0.05)  # Simulate processing time
        progress_bar.progress(i + 1)
    
    st.session_state.analysis_complete = True
    navigate_to(4)
    
    show_navigation(3)

# Page 4: Results
def show_page_4():
    st.title("Analysis Results")
    
    if st.session_state.analysis_complete:
        st.markdown("### 95% sure no-rip detected!")
        
        # Add result to history
        if len(st.session_state.history) < 9:  # Limit history to 9 items
            st.session_state.history.append(("95% no-rip", time.strftime("%Y-%m-%d %H:%M")))
        
        if st.button("Check history"):
            navigate_to(5)
    
    show_navigation(4)

# Page 5: History
def show_page_5():
    st.title("History")
    
    # Display history in a grid
    col1, col2, col3 = st.columns(3)
    for idx, (result, timestamp) in enumerate(st.session_state.history):
        with [col1, col2, col3][idx % 3]:
            st.markdown(f"""
            <div style='border:1px solid #ddd; padding:10px; margin:5px; text-align:center;'>
                <h4>{result}</h4>
                <p>{timestamp}</p>
            </div>
            """, unsafe_allow_html=True)
    
    show_navigation(5)

# Navigation bar
def show_navigation(current_page):
    cols = st.columns([1, 8, 1])  # Create three columns for layout
    
    with cols[1]:  # Use the middle column for navigation
        st.markdown("""
            <div class="nav-container">
                <a class="nav-arrow">←</a>
        """, unsafe_allow_html=True)
        
        for i in range(1, 6):
            if i == current_page:
                st.markdown(f"""
                    <div class="nav-item active">{i}</div>
                """, unsafe_allow_html=True)
            else:
                if st.button(str(i), key=f"nav_{i}"):
                    navigate_to(i)
        
        st.markdown("""
                <a class="nav-arrow">→</a>
            </div>
        """, unsafe_allow_html=True)

# Main app logic
def main():
    if st.session_state.page == 1:
        show_page_1()
    elif st.session_state.page == 2:
        show_page_2()
    elif st.session_state.page == 3:
        show_page_3()
    elif st.session_state.page == 4:
        show_page_4()
    elif st.session_state.page == 5:
        show_page_5()

if __name__ == "__main__":
    main() 