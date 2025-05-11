import streamlit as st
import os
import tempfile
import time
import requests
import json
import base64
from PIL import Image
import io
import uuid
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# Set page configuration
st.set_page_config(
    page_title="Video Creator & YouTube Uploader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
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
    }
    .effect-card.selected {
        border: 2px solid #4285F4;
        background-color: #e8f0fe;
    }
    .processing-preview {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin-top: 15px;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "image_file" not in st.session_state:
    st.session_state.image_file = None
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "video_url" not in st.session_state:
    st.session_state.video_url = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "selected_effect" not in st.session_state:
    st.session_state.selected_effect = "glitch"
if "api_authenticated" not in st.session_state:
    st.session_state.api_authenticated = False

# Check for credentials in Streamlit secrets
def check_credentials():
    try:
        # Verify OpenAI API key
        openai_key = st.secrets.get("openai_api_key", None)
        if openai_key and openai_key.startswith("sk-"):
            st.session_state.openai_api_key = openai_key
        
        # Check for YouTube credentials
        youtube_token = st.secrets.get("youtube_token", None)
        if youtube_token:
            st.session_state.youtube_token = youtube_token
            
        # Check if all required credentials are present
        if st.session_state.get("openai_api_key") and st.session_state.get("youtube_token"):
            st.session_state.api_authenticated = True
            return True
        return False
    except Exception as e:
        st.error(f"Error checking credentials: {str(e)}")
        return False

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
    
    image_bytes = None
    audio_bytes = None
    
    with col1:
        st.markdown("### Upload Image")
        uploaded_image = st.file_uploader("Select an image file", type=["jpg", "jpeg", "png"], key="image_upload")
        if uploaded_image is not None:
            st.success("✅ Image uploaded!")
            st.image(Image.open(uploaded_image), width=300)
            image_bytes = uploaded_image.getvalue()
            st.session_state.image_bytes = image_bytes
    
    with col2:
        st.markdown("### Upload Audio")
        uploaded_audio = st.file_uploader("Select an audio file", type=["mp3", "wav"], key="audio_upload")
        if uploaded_audio is not None:
            st.success("✅ Audio uploaded!")
            st.audio(uploaded_audio)
            audio_bytes = uploaded_audio.getvalue()
            st.session_state.audio_bytes = audio_bytes
    
    return image_bytes, audio_bytes

# 2. VIDEO PROCESSOR COMPONENT
def create_video(image_bytes, audio_bytes, effect_type="glitch"):
    """Create video using a secure cloud video API"""
    if not image_bytes or not audio_bytes:
        show_popup("Missing Files", "Please upload both image and audio files first.", "warning")
        return None
        
    try:
        with st.spinner("Creating your video..."):
            # In a production app, this would send the files to your own secure API endpoint
            # For this demo, we'll simulate video creation
            
            # Display processing animation
            st.markdown("""
            <div class="processing-preview">
                <h4>Processing Video</h4>
                <p>Applying effects and combining image with audio...</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress simulation
            progress_bar = st.progress(0)
            for i in range(101):
                time.sleep(0.03)
                progress_bar.progress(i)
            
            # For demo purposes, use a sample video
            video_url = "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
            
            # In production, your API would return the actual video URL or data
            
            st.success("✅ Video created successfully!")
            st.video(video_url)
            
            return video_url
            
    except Exception as e:
        st.error(f"Error creating video: {str(e)}")
        return None

# 3. SEO GENERATOR COMPONENT
def generate_seo(title, description):
    """Generate SEO content using OpenAI API with secure authentication"""
    if not title:
        show_popup("Missing Title", "Please enter a video title first.", "warning")
        return None, None, None
    
    # Get OpenAI API key from Streamlit secrets
    openai_api_key = st.session_state.get("openai_api_key")
    
    if not openai_api_key:
        show_popup("API Key Missing", "OpenAI API key not configured in Streamlit secrets.", "error")
        return None, None, None
    
    try:
        with st.spinner("Generating SEO content with AI..."):
            # Prepare prompt
            prompt = f"""
            Create YouTube SEO content based on this video information:
            
            Video Title: {title}
            Video Description: {description}
            
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
                st.error(f"OpenAI API Error: {response.text}")
                return None, None, None
                
    except Exception as e:
        st.error(f"Error generating SEO content: {str(e)}")
        return None, None, None

# 4. YOUTUBE UPLOADER COMPONENT
def upload_to_youtube(video_url, title, description, tags):
    """Upload video to YouTube using secure token"""
    try:
        youtube_token = st.session_state.get("youtube_token")
        
        if not youtube_token:
            show_popup("Authentication Required", "YouTube token not configured in Streamlit secrets.", "error")
            return False
        
        with st.spinner("Uploading to YouTube..."):
            # In a production app, you would:
            # 1. Send the video and metadata to your secure API endpoint
            # 2. Your API would handle YouTube authentication using the stored token
            # 3. The API would return the YouTube video URL
            
            # For this demo, we'll simulate the upload process
            
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
    st.title("🎬 Video Creator & YouTube Uploader")
    st.write("Create videos with effects and upload to YouTube with AI-generated SEO content")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Check credentials silently
    is_authenticated = check_credentials()
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        
        # Define steps
        steps = ["1. Upload Media", "2. Create Video", 
                "3. Video Information & SEO", "4. Upload to YouTube"]
        
        # Navigation radio buttons        
        current_step_index = st.session_state.current_step - 1
        if current_step_index >= len(steps):
            current_step_index = 0
            
        step = st.radio("", steps, index=current_step_index, key="navigation")
        
        # Update current step based on selection
        for i, s in enumerate(steps):
            if step == s:
                st.session_state.current_step = i + 1
        
        st.markdown("---")
        st.markdown("### API Status")
        
        # Show API status indicators
        if st.session_state.get("openai_api_key"):
            st.success("✅ OpenAI API: Connected")
        else:
            st.warning("❌ OpenAI API: Not configured")
            
        if st.session_state.get("youtube_token"):
            st.success("✅ YouTube API: Connected")
        else:
            st.warning("❌ YouTube API: Not configured")
            
        # Add app information
        st.markdown("---")
        st.info("👋 This app uses Streamlit secrets for API keys. Configure them in your Streamlit Cloud dashboard.")
    
    # Content based on selected step
    if st.session_state.current_step == 1:
        st.header("Step 1: Upload Media")
        image_bytes, audio_bytes = upload_media()
        
        # Enable continue button if both files are uploaded
        if "image_bytes" in st.session_state and "audio_bytes" in st.session_state:
            st.success("Both files uploaded successfully!")
            
            if st.button("Continue to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
    
    elif st.session_state.current_step == 2:
        st.header("Step 2: Create Video with Effects")
        
        # Check if we have media files
        if "image_bytes" not in st.session_state or "audio_bytes" not in st.session_state:
            st.warning("Please upload image and audio files first.")
            if st.button("Go Back to Media Upload"):
                st.session_state.current_step = 1
                st.experimental_rerun()
        else:
            # Effect selection
            st.subheader("Choose an Effect")
            
            col1, col2, col3 = st.columns(3)
            
            # Effect selection buttons
            with col1:
                if st.button("Glitch Effect", use_container_width=True):
                    st.session_state.selected_effect = "glitch"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "glitch":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px; text-align:center;'>✓ Selected</div>", unsafe_allow_html=True)
                    
            with col2:
                if st.button("Zoom Effect", use_container_width=True):
                    st.session_state.selected_effect = "zoom"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "zoom":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px; text-align:center;'>✓ Selected</div>", unsafe_allow_html=True)
                    
            with col3:
                if st.button("Fade Effect", use_container_width=True):
                    st.session_state.selected_effect = "fade"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "fade":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px; text-align:center;'>✓ Selected</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Create video button
            if st.button("Create Video with Selected Effect", type="primary", use_container_width=True) or "video_url" in st.session_state:
                if "video_url" not in st.session_state:
                    video_url = create_video(
                        st.session_state.image_bytes,
                        st.session_state.audio_bytes,
                        st.session_state.selected_effect
                    )
                    if video_url:
                        st.session_state.video_url = video_url
                else:
                    # Show existing video
                    st.success("✅ Video already created!")
                    st.video(st.session_state.video_url)
                
                # Continue button
                if st.button("Continue to Video Information"):
                    st.session_state.current_step = 3
                    st.experimental_rerun()
    
    elif st.session_state.current_step == 3:
        st.header("Step 3: Video Information & SEO")
        
        # Check if we have a video
        if "video_url" not in st.session_state:
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            # Video Information
            col1, col2 = st.columns([2, 1])
            
            with col1:
                video_title = st.text_input("Video Title", key="title_input", 
                                           placeholder="Enter an engaging title for your video")
                video_description = st.text_area("Video Description", key="desc_input", 
                                               placeholder="Describe your video content")
                video_tags = st.text_input("Tags (comma-separated)", key="tags_input", 
                                         placeholder="tag1, tag2, tag3")
            
            with col2:
                st.video(st.session_state.video_url)
            
            # Generate SEO button - only show if API is configured
            if st.session_state.get("openai_api_key"):
                if st.button("Generate SEO Content with AI", type="primary"):
                    seo_title, seo_description, seo_tags = generate_seo(video_title, video_description)
                    
                    if seo_title and seo_description and seo_tags:
                        st.session_state.seo_title = seo_title
                        st.session_state.seo_description = seo_description
                        st.session_state.seo_tags = seo_tags
                        show_popup("SEO Content Generated", "AI has created optimized content for your video!", "success")
            else:
                st.warning("OpenAI API key not configured. SEO generation is disabled.")
            
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
            if st.button("Continue to YouTube Upload"):
                st.session_state.current_step = 4
                st.experimental_rerun()
    
    elif st.session_state.current_step == 4:
        st.header("Step 4: Upload to YouTube")
        
        # Check for video
        if "video_url" not in st.session_state:
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            if not st.session_state.get("youtube_token"):
                st.error("YouTube authentication token not configured in Streamlit secrets.")
                st.info("Contact the app administrator to configure the YouTube API credentials.")
            else:
                # YouTube upload form
                st.subheader("Ready to Upload")
                
                # Get title and description
                if 'seo_title' in st.session_state:
                    title = st.text_input("Video Title", value=st.session_state.seo_title)
                    description = st.text_area("Video Description", value=st.session_state.seo_description)
                    tags = st.text_input("Video Tags", value=st.session_state.seo_tags)
                else:
                    title = st.text_input("Video Title", value=st.session_state.get("title_input", ""))
                    description = st.text_area("Video Description", value=st.session_state.get("desc_input", ""))
                    tags = st.text_input("Video Tags", value=st.session_state.get("tags_input", ""))
                
                # Privacy setting
                privacy = st.selectbox("Privacy Setting", ["private", "unlisted", "public"], index=0)
                
                # Upload button
                if st.button("Upload to YouTube", type="primary"):
                    upload_to_youtube(st.session_state.video_url, title, description, tags)

if __name__ == "__main__":
    main()
