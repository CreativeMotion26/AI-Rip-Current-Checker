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
        background-color: #f0f2f6;
        color: #262730;
        border: none;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .main {
        padding: 2rem;
    }
    .title {
        text-align: center;
        margin-bottom: 2rem;
    }
    .pagination-nav {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem;
        gap: 10px;
        margin-top: 2rem;
    }
    .page-item {
        width: 40px;
        height: 40px;
        border: 1px solid #ddd;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        background: white;
    }
    .page-item.active {
        background: #f63366;
        color: white;
        border: none;
    }
    .page-arrow {
        color: #666;
        font-size: 20px;
        cursor: pointer;
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
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'recorded_frames' not in st.session_state:
    st.session_state.recorded_frames = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

def navigate_to(page):
    if 1 <= page <= 5:
        st.session_state.page = page

def toggle_camera():
    st.session_state.camera_on = not st.session_state.camera_on
    if not st.session_state.camera_on:
        st.session_state.recording = False
        st.session_state.recorded_frames = []
        st.session_state.start_time = None

def start_recording():
    st.session_state.recording = True
    st.session_state.recorded_frames = []
    st.session_state.start_time = time.time()

def stop_camera():
    st.session_state.camera_on = False
    st.session_state.recording = False
    st.session_state.start_time = None

# Page 1: Instructions and Camera Access
def show_page_1():
    st.title("Rip Current Checker")
    st.subheader("Set Up Your Camera")
    
    # Camera icon and instructions
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### 📸")
    # Tips section
    st.markdown("""
    ### Tips for Best Result
    1. Set your camera to 4K resolution
    2. Stand a few meters from the water's edge
    3. Use landscape mode
    4. Take a 5-second video, holding steady
    """)
    
    # Camera functionality
    col1, col2 = st.columns([3, 1])
    with col1:
        st.button("Access Camera", key="access_camera", on_click=toggle_camera)
    with col2:
        st.button("Access Video", key="access_video", on_click=navigate_to, args=(2,))
    
    if st.session_state.camera_on:
        camera_placeholder = st.empty()
        timer_placeholder = st.empty()
        record_col1, record_col2 = st.columns([3, 1])
        
        with record_col1:
            if not st.session_state.recording:
                st.button("Start Recording", key="start_record", on_click=start_recording)
        with record_col2:
            st.button("Stop Camera", key="stop_camera", on_click=stop_camera)
            
        video_capture = cv2.VideoCapture(0)
        
        if video_capture.isOpened():
            try:
                while st.session_state.camera_on:
                    ret, frame = video_capture.read()
                    if ret:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        camera_placeholder.image(frame_rgb, channels="RGB")
                        
                        if st.session_state.recording:
                            st.session_state.recorded_frames.append(frame)
                            elapsed_time = time.time() - st.session_state.start_time
                            timer_placeholder.markdown(f"""
                                <div class="recording-timer">Recording: {elapsed_time:.1f}s / 5.0s</div>
                            """, unsafe_allow_html=True)
                            
                            if elapsed_time >= 5.0:
                                st.session_state.recording = False
                                st.session_state.camera_on = False
                                
                                if st.session_state.recorded_frames:
                                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                                    out = cv2.VideoWriter(temp_file.name, 
                                                        cv2.VideoWriter_fourcc(*'mp4v'), 
                                                        30, 
                                                        (frame.shape[1], frame.shape[0]))
                                    for f in st.session_state.recorded_frames:
                                        out.write(f)
                                    out.release()
                                    st.session_state.video_file = temp_file.name
                                    navigate_to(3)
                                break
            finally:
                video_capture.release()
        else:
            st.error("Could not access the camera. Please check your camera permissions.")
    
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
    st.success("done! click next to view result")  # Show completion message
    navigate_to(4)
    
    show_navigation(3)

# Page 4: Results
def show_page_4():
    st.title("Analysis Results")
    if st.session_state.analysis_complete:
        st.success("✅ 95% sure no-rip detected!")
        if len(st.session_state.history) < 9:
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
    
    if st.button("Check again!"):
                navigate_to(1)        
    show_navigation(5)

def show_navigation(current_page):
    # Create 7 columns for ← 1 2 3 4 5 →
    cols = st.columns(7)

    # Left arrow
    if current_page > 1:
        if cols[0].button("Previous", key="prev"):
            navigate_to(current_page - 1)
    else:
        cols[0].markdown("")  # placeholder

    # Right arrow
    if current_page < 5:
        if cols[1].button("Next", key="next"):
            navigate_to(current_page + 1)
    else:
        cols[6].markdown("")  # placeholder

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