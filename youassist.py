import streamlit as st
import os
import tempfile
import time
import base64
import requests
import json
from PIL import Image
import io
import uuid

# Set page configuration
st.set_page_config(
    page_title="Video Creator & YouTube Uploader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling with animated effects
st.markdown("""
<style>
    .stAlert {
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .stButton button {
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .top-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .effect-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin: 5px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .effect-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .effect-card.selected {
        border: 2px solid #4285F4;
        background-color: #e8f0fe;
    }
    .processing-preview {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        margin-top: 15px;
        background-color: #f8f9fa;
    }
    /* Animation effects */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .pulse {
        animation: pulse 2s infinite;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .fadeIn {
        animation: fadeIn 1s forwards;
    }
    .video-timeline {
        height: 80px;
        background: #2d2d2d;
        border-radius: 8px;
        padding: 10px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        overflow-x: auto;
    }
    .timeline-segment {
        min-width: 100px;
        height: 60px;
        background: #3a3a3a;
        margin-right: 5px;
        border-radius: 5px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
    }
    .timeline-segment:hover {
        background: #4a4a4a;
    }
    .timeline-segment img {
        max-height: 50px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "video_url" not in st.session_state:
    st.session_state.video_url = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "selected_effect" not in st.session_state:
    st.session_state.selected_effect = "glitch"
if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "image_bytes" not in st.session_state:
    st.session_state.image_bytes = None
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None
if "api_authenticated" not in st.session_state:
    st.session_state.api_authenticated = False

# Function to create popup-like appearance
def show_popup(title, content, type="info"):
    color = "#ffffff"
    if type == "success":
        color = "#d4edda"
    elif type == "error":
        color = "#f8d7da"
    elif type == "warning":
        color = "#fff3cd"
    elif type == "info":
        color = "#d1ecf1"
    
    with st.container():
        st.markdown(f"""
        <div style="background-color: {color}; padding: 15px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
            <h3>{title}</h3>
            <p>{content}</p>
        </div>
        """, unsafe_allow_html=True)

# 1. MEDIA UPLOADER COMPONENT
def upload_media():
    """Upload image and audio files"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Upload Image")
        # Fixed file_uploader by explicitly specifying allowed extensions without the dot
        uploaded_image = st.file_uploader("Select an image file", type=["jpg", "jpeg", "png"], key="image_upload", 
                                         help="Upload a JPEG or PNG image to use in your video")
        if uploaded_image is not None:
            st.success("✅ Image uploaded!")
            try:
                img = Image.open(uploaded_image)
                st.image(img, width=300)
                # Store image bytes for later use
                img_bytes = uploaded_image.getvalue()
                st.session_state.image_bytes = img_bytes
                # Convert image format if needed
                if uploaded_image.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    pass
                else:
                    # Ensure proper format
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    st.session_state.image_bytes = buf.getvalue()
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")
    
    with col2:
        st.markdown("### Upload Audio")
        uploaded_audio = st.file_uploader("Select an audio file", type=["mp3", "wav"], key="audio_upload",
                                         help="Upload MP3 or WAV audio to use as your video soundtrack")
        if uploaded_audio is not None:
            st.success("✅ Audio uploaded!")
            st.audio(uploaded_audio)
            # Store audio bytes
            st.session_state.audio_bytes = uploaded_audio.getvalue()
    
    return st.session_state.image_bytes is not None, st.session_state.audio_bytes is not None

# 2. VIDEO PROCESSOR COMPONENT WITH AVEEPLAYER-LIKE FEATURES
def create_video_with_effects():
    """Create video with AveePlyer-style effects"""
    
    if not st.session_state.get("image_bytes") or not st.session_state.get("audio_bytes"):
        show_popup("Missing Files", "Please upload both image and audio files first.", "warning")
        return None
    
    # Show effect options with visual previews
    st.subheader("Select Video Effect")
    
    # Define available effects with preview images
    effects = {
        "glitch": {"name": "Glitch Effect", "desc": "Digital distortion with color artifacts"},
        "zoom": {"name": "Zoom Pulse", "desc": "Rhythmic zoom effects synced to audio"},
        "fade": {"name": "Color Fade", "desc": "Smooth color transitions and fades"},
        "particles": {"name": "Particle Swarm", "desc": "Dynamic particle animations"},
        "spectrum": {"name": "Audio Spectrum", "desc": "Visualize audio frequencies"}
    }
    
    # Create columns for effect selection
    cols = st.columns(3)
    for i, (effect_id, effect) in enumerate(effects.items()):
        with cols[i % 3]:
            is_selected = st.session_state.selected_effect == effect_id
            card_style = "effect-card selected" if is_selected else "effect-card"
            
            # Create clickable card
            st.markdown(f"""
            <div class="{card_style}" id="{effect_id}-card">
                <h4>{effect["name"]}</h4>
                <p style="font-size: 0.8em; color: #666;">{effect["desc"]}</p>
                <div style="height: 60px; background: #f0f0f0; border-radius: 5px; 
                     display: flex; align-items: center; justify-content: center; margin-top: 10px;">
                    <span style="color: #888;">Effect Preview</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add button with label (fixing the empty label warning)
            if st.button(f"Select {effect['name']}", key=f"effect_{effect_id}", help=f"Apply {effect['name']} to your video"):
                st.session_state.selected_effect = effect_id
                st.experimental_rerun()
    
    st.markdown("---")
    
    # Timeline editor (AveePlyer-style)
    st.subheader("Video Timeline")
    st.markdown("""
    <div class="video-timeline">
        <div class="timeline-segment" title="Introduction">
            <span>Intro</span>
        </div>
        <div class="timeline-segment" title="Main Effect">
            <span>Effect</span>
        </div>
        <div class="timeline-segment" title="Transition">
            <span>Transition</span>
        </div>
        <div class="timeline-segment" title="Outro">
            <span>Outro</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Advanced options
    with st.expander("Advanced Effects Settings"):
        intensity = st.slider("Effect Intensity", min_value=0, max_value=100, value=50, 
                             help="Adjust the intensity of the selected effect")
        duration = st.slider("Effect Duration (seconds)", min_value=5, max_value=60, value=15,
                           help="Set the duration of your video")
        col1, col2 = st.columns(2)
        with col1:
            sync_to_audio = st.checkbox("Sync to Audio Beat", value=True,
                                      help="Synchronize effects with audio beats")
        with col2:
            add_text = st.checkbox("Add Text Overlay", value=False,
                                 help="Add text overlay to your video")
        
        if add_text:
            text_overlay = st.text_input("Text Overlay", 
                                        help="Enter text to display on your video")
    
    # Process video button
    if st.button("Create Video", type="primary", use_container_width=True, help="Process and create your video"):
        with st.spinner("Creating your video with effects..."):
            # Show processing interface
            st.markdown("""
            <div class="processing-preview fadeIn">
                <h4>Processing Video</h4>
                <p>Applying selected effects and rendering your video...</p>
                <div style="display: flex; margin: 20px 0;">
                    <div style="flex: 1; text-align: center;">
                        <p>Input Image</p>
                        <div style="max-height: 150px; overflow: hidden; margin: 0 auto; width: 150px;">
                            <img src="data:image/jpeg;base64,{}" alt="Input" style="width: 100%;">
                        </div>
                    </div>
                    <div style="margin: 0 20px; display: flex; align-items: center;">➡️</div>
                    <div style="flex: 1; text-align: center;">
                        <p>Effect: {}</p>
                        <div class="pulse" style="background-color: #eee; height: 150px; width: 150px; margin: 0 auto; 
                             display: flex; align-items: center; justify-content: center;">
                            <p>Processing...</p>
                        </div>
                    </div>
                </div>
            </div>
            """.format(
                base64.b64encode(st.session_state.image_bytes).decode() if st.session_state.image_bytes else "",
                effects[st.session_state.selected_effect]["name"]
            ), unsafe_allow_html=True)
            
            # Simulate processing with progress bar
            progress_bar = st.progress(0)
            for i in range(101):
                time.sleep(0.03)
                progress_bar.progress(i)
            
            # For demonstration, use a sample video URL
            # In a real app, this would be the output from a video processing service
            sample_videos = {
                "glitch": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "zoom": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "fade": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "particles": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "spectrum": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
            }
            
            video_url = sample_videos.get(st.session_state.selected_effect, sample_videos["glitch"])
            st.session_state.video_url = video_url
            
            st.success("✅ Video created successfully!")
            st.video(video_url)
            
            return video_url
    
    # Show existing video if already created
    if st.session_state.video_url:
        st.subheader("Your Video")
        st.video(st.session_state.video_url)
        return st.session_state.video_url
            
    return None

# 3. SEO GENERATOR COMPONENT
def generate_seo(title, description):
    """Generate SEO content using OpenAI API with secure authentication"""
    if not title:
        show_popup("Missing Title", "Please enter a video title first.", "warning")
        return None, None, None
    
    try:
        # Get OpenAI API key from secrets
        openai_api_key = None
        try:
            openai_api_key = st.secrets["openai_api_key"]
        except:
            openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            st.warning("OpenAI API key not configured. Using sample SEO content instead.")
            # Return sample SEO content for demo
            return (
                f"🔥 {title} - Amazing Visual Experience",
                f"{description}\n\nCheck out this amazing visual experience with stunning effects! Don't forget to like and subscribe for more content like this.",
                "music video, visual effects, audio visualization, AveePlyer, cool effects, motion graphics"
            )
        
        with st.spinner("Generating SEO content with AI..."):
            # Prepare prompt
            prompt = f"""
            Create YouTube SEO content based on this video information:
            
            Video Title: {title}
            Video Description: {description}
            
            The video has AveePlyer-style visual effects with music.
            
            Please provide:
            1. A catchy, SEO-optimized title (max 70 characters)
            2. A detailed description with relevant keywords (300-500 chars)
            3. Ten relevant hashtags/tags (comma-separated)
            
            Format your response exactly as:
            TITLE: [your title]
            DESCRIPTION: [your description]
            TAGS: [tag1], [tag2], [tag3], ...
            """
            
            # Make request to OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_api_key}"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a YouTube SEO expert."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse response
                lines = content.split('\n')
                seo_title = ""
                seo_description = ""
                seo_tags = ""
                
                for line in lines:
                    if line.startswith('TITLE:'):
                        seo_title = line[6:].strip()
                    elif line.startswith('DESCRIPTION:'):
                        seo_description = line[12:].strip()
                    elif line.startswith('TAGS:'):
                        seo_tags = line[5:].strip()
                
                return seo_title, seo_description, seo_tags
            else:
                st.error(f"OpenAI API Error: {response.status_code}")
                # Fallback to sample content
                return (
                    f"🔥 {title} - Amazing Visual Experience",
                    f"{description}\n\nCheck out this amazing visual experience with stunning effects! Don't forget to like and subscribe for more content like this.",
                    "music video, visual effects, audio visualization, AveePlyer, cool effects, motion graphics"
                )
    except Exception as e:
        st.error(f"Error generating SEO content: {str(e)}")
        # Fallback content
        return (
            f"🔥 {title} - Amazing Visual Experience",
            f"{description}\n\nCheck out this amazing visual experience with stunning effects! Don't forget to like and subscribe for more content like this.",
            "music video, visual effects, audio visualization, AveePlyer, cool effects, motion graphics"
        )

# 4. YOUTUBE UPLOADER COMPONENT
def upload_to_youtube(video_url, title, description, tags):
    """Upload video to YouTube using secure token"""
    try:
        # Get YouTube token from secrets
        youtube_token = None
        try:
            youtube_token = st.secrets["youtube_token"]
        except:
            youtube_token = os.getenv("YOUTUBE_TOKEN")
        
        if not youtube_token:
            show_popup("Demo Mode", "YouTube upload is in demo mode. In a real app, this would upload to your YouTube channel.", "info")
        
        with st.spinner("Uploading to YouTube..."):
            # Display upload progress
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i in range(1, 101):
                status.text(f"Uploading: {i}%")
                progress_bar.progress(i)
                time.sleep(0.03)
            
            # Simulate successful upload
            video_id = f"demo_{uuid.uuid4().hex[:8]}"
            mock_youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            show_popup("Upload Successful", f"Video uploaded to YouTube! [View your video]({mock_youtube_url})", "success")
            return True
    except Exception as e:
        st.error(f"Error uploading to YouTube: {str(e)}")
        return False

# MAIN APP
def main():
    # App header with logo
    st.markdown('<div class="top-header">', unsafe_allow_html=True)
    st.title("🎬 AveePlyer-Style Video Creator")
    st.write("Create stunning music visualization videos and upload to YouTube")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        
        # Define steps
        steps = ["1. Upload Media", "2. Create Video", 
                "3. Video Information & SEO", "4. Upload to YouTube"]
        
        # Navigation radio buttons with proper label        
        current_step_index = st.session_state.current_step - 1
        if current_step_index >= len(steps):
            current_step_index = 0
            
        step = st.radio("Navigation", steps, index=current_step_index, key="navigation")
        
        # Update current step based on selection
        for i, s in enumerate(steps):
            if step == s:
                st.session_state.current_step = i + 1
        
        # App information
        st.markdown("---")
        st.info("👋 This app creates music visualization videos with effects similar to AveePlyer.")
    
    # Content based on selected step
    if st.session_state.current_step == 1:
        st.header("Step 1: Upload Media")
        image_uploaded, audio_uploaded = upload_media()
        
        # Enable continue button if both files are uploaded
        if image_uploaded and audio_uploaded:
            st.success("Both files uploaded successfully!")
            
            if st.button("Continue to Video Creation", help="Proceed to video creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
    
    elif st.session_state.current_step == 2:
        st.header("Step 2: Create Video with Effects")
        
        # Check if we have media files
        if "image_bytes" not in st.session_state or "audio_bytes" not in st.session_state:
            st.warning("Please upload image and audio files first.")
            if st.button("Go Back to Media Upload", help="Return to upload media"):
                st.session_state.current_step = 1
                st.experimental_rerun()
        else:
            # Process video with AveePlyer-style effects
            video_url = create_video_with_effects()
            
            # Continue button
            if video_url and st.button("Continue to Video Information", help="Proceed to add video metadata"):
                st.session_state.current_step = 3
                st.experimental_rerun()
    
    elif st.session_state.current_step == 3:
        st.header("Step 3: Video Information & SEO")
        
        # Check if we have a video
        if "video_url" not in st.session_state:
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation", help="Return to video creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            # Video Information
            col1, col2 = st.columns([2, 1])
            
            with col1:
                video_title = st.text_input("Video Title", key="title_input", 
                                           placeholder="Enter an engaging title for your video",
                                           label_visibility="visible")
                video_description = st.text_area("Video Description", key="desc_input", 
                                               placeholder="Describe your video content",
                                               label_visibility="visible")
                video_tags = st.text_input("Tags (comma-separated)", key="tags_input", 
                                         placeholder="tag1, tag2, tag3",
                                         label_visibility="visible")
            
            with col2:
                st.video(st.session_state.video_url)
            
            # Generate SEO button
            if st.button("Generate SEO Content with AI", help="Use AI to generate optimized titles and descriptions"):
                seo_title, seo_description, seo_tags = generate_seo(video_title, video_description)
                
                if seo_title and seo_description and seo_tags:
                    st.session_state.seo_title = seo_title
                    st.session_state.seo_description = seo_description
                    st.session_state.seo_tags = seo_tags
                    show_popup("SEO Content Generated", "AI has created optimized content for your video!", "success")
            
            # Display SEO content if available
            if 'seo_title' in st.session_state:
                with st.expander("View SEO-Optimized Content", expanded=True):
                    st.subheader("SEO Title")
                    st.write(st.session_state.seo_title)
                    
                    st.subheader("SEO Description")
                    st.write(st.session_state.seo_description)
                    
                    st.subheader("SEO Tags")
                    st.write(st.session_state.seo_tags)
            
            # Continue button
            if st.button("Continue to YouTube Upload", help="Proceed to YouTube upload"):
                st.session_state.current_step = 4
                st.experimental_rerun()
    
    elif st.session_state.current_step == 4:
        st.header("Step 4: Upload to YouTube")
        
        # Check for video
        if "video_url" not in st.session_state:
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation", help="Return to video creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            # YouTube upload form
            st.subheader("Ready to Upload")
            
            # Get title and description
            if 'seo_title' in st.session_state:
                title = st.text_input("Video Title", value=st.session_state.seo_title, 
                                     label_visibility="visible")
                description = st.text_area("Video Description", value=st.session_state.seo_description, 
                                         label_visibility="visible")
                tags = st.text_input("Video Tags", value=st.session_state.seo_tags, 
                                   label_visibility="visible")
            else:
                title = st.text_input("Video Title", value=st.session_state.get("title_input", ""),
                                     label_visibility="visible")
                description = st.text_area("Video Description", value=st.session_state.get("desc_input", ""),
                                         label_visibility="visible")
                tags = st.text_input("Video Tags", value=st.session_state.get("tags_input", ""),
                                   label_visibility="visible")
            
            # Privacy setting
            privacy = st.selectbox("Privacy Setting", ["private", "unlisted", "public"], index=0,
                                 label_visibility="visible")
            
            # Upload button
            if st.button("Upload to YouTube", help="Upload your video to YouTube"):
                upload_to_youtube(st.session_state.video_url, title, description, tags)

if __name__ == "__main__":
    main()
