import streamlit as st
import os
import tempfile
import subprocess
import pickle
import time
import base64
from PIL import Image
import requests
import json
import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables for API keys
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Video Creator & YouTube Uploader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for popup-style dialogs
st.markdown("""
<style>
    .stAlert {
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .css-18e3th9 {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .css-1344jno {
        font-size: 18px !important;
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
    .small-text {
        font-size: 12px;
        color: #888888;
    }
    .auth-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "authenticated_youtube" not in st.session_state:
    st.session_state.authenticated_youtube = False
if "openai_key_set" not in st.session_state:
    st.session_state.openai_key_set = False
if "video_file" not in st.session_state:
    st.session_state.video_file = None
if "processing_done" not in st.session_state:
    st.session_state.processing_done = False
if "current_step" not in st.session_state:
    st.session_state.current_step = 1

# Function to create popup-like appearance
def show_popup(title, content, type="info"):
    # Simulate a popup with a special container
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
        uploaded_image = st.file_uploader("Select an image file", type=["jpg", "jpeg", "png"])
        if uploaded_image is not None:
            st.success("✅ Image uploaded!")
            st.image(Image.open(uploaded_image), width=300)
            
            # Save to temporary file
            image_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
            with open(image_path, "wb") as f:
                f.write(uploaded_image.getbuffer())
        else:
            image_path = None
    
    with col2:
        st.markdown("### Upload Audio")
        uploaded_audio = st.file_uploader("Select an audio file", type=["mp3", "wav"])
        if uploaded_audio is not None:
            st.success("✅ Audio uploaded!")
            st.audio(uploaded_audio)
            
            # Save to temporary file
            audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            with open(audio_path, "wb") as f:
                f.write(uploaded_audio.getbuffer())
        else:
            audio_path = None
    
    return image_path, audio_path

# 2. VIDEO PROCESSOR COMPONENT
def process_video(image_path, audio_path):
    """Create a video with glitch effect using FFmpeg"""
    if not image_path or not audio_path:
        show_popup("Missing Files", "Please upload both image and audio files first.", "warning")
        return None
    
    try:
        with st.spinner("Creating your video with glitch effects..."):
            # Create output path
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            
            # FFmpeg command to create a glitch effect
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1', '-i', image_path,  # Input image
                '-i', audio_path,  # Input audio
                '-filter_complex', 
                '[0:v]scale=1280:720,format=yuv420p,gblur=sigma=1:steps=1,eq=brightness=0.1:saturation=1.5:contrast=1.2,'
                'hue=h=sin(t)*10:s=sin(t)+1,curves=all=\'0/0 0.25/0.15 0.5/0.5 0.75/0.85 1/1\','
                'unsharp=5:5:1.5:5:5:0,noise=c0s=10:c0f=t+u[glitch]',
                '-map', '[glitch]', '-map', '1:a',  # Map video and audio
                '-c:v', 'libx264', '-preset', 'medium',  # Video codec
                '-c:a', 'aac',  # Audio codec
                '-shortest',  # End when the shortest input ends
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                output_path
            ]
            
            # Check if FFmpeg is installed
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            except FileNotFoundError:
                show_popup("FFmpeg Not Found", "Please install FFmpeg to create videos: https://ffmpeg.org/download.html", "error")
                return None
                
            # Run ffmpeg command
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                st.session_state.processing_done = True
                st.success("✅ Video created successfully!")
                st.video(output_path)
                return output_path
            else:
                st.error(f"Failed to create video. Error: {process.stderr}")
                return None
            
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        return None

# 3. SEO GENERATOR COMPONENT
def generate_seo_content(title, description):
    """Generate SEO content using OpenAI API"""
    if not title:
        show_popup("Missing Title", "Please enter a video title first.", "warning")
        return None, None, None
    
    # Get OpenAI API key
    openai_api_key = st.session_state.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        with st.expander("Set OpenAI API Key", expanded=True):
            input_key = st.text_input("Enter your OpenAI API key:", type="password")
            if st.button("Save API Key"):
                if input_key.startswith("sk-"):
                    st.session_state.openai_api_key = input_key
                    st.session_state.openai_key_set = True
                    st.success("✅ API key saved!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid API key format.")
        return (f"SEO-Optimized: {title}", 
                f"Auto-generated description for {title}. {description}", 
                "video, content, youtube")
    
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
                return (f"SEO-Optimized: {title}", 
                        f"Auto-generated description for {title}. {description}", 
                        "video, content, youtube")
            
    except Exception as e:
        st.error(f"Error generating SEO content: {str(e)}")
        return (f"SEO-Optimized: {title}", 
                f"Auto-generated description for {title}. {description}", 
                "video, content, youtube")

# 4. YOUTUBE UPLOADER COMPONENT
def authenticate_youtube():
    """Enhanced YouTube OAuth authentication with modal-style popup"""
    credentials_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials')
    os.makedirs(credentials_dir, exist_ok=True)
    credentials_path = os.path.join(credentials_dir, 'youtube_credentials.pickle')
    
    # If already authenticated, just return credentials
    if st.session_state.authenticated_youtube:
        with open(credentials_path, 'rb') as token:
            credentials = pickle.load(token)
        return credentials
    
    # Check for existing credentials
    if os.path.exists(credentials_path):
        try:
            with open(credentials_path, 'rb') as token:
                credentials = pickle.load(token)
            st.session_state.authenticated_youtube = True
            return credentials
        except Exception:
            if os.path.exists(credentials_path):
                os.remove(credentials_path)
    
    # Modal-style login popup
    if "show_login" not in st.session_state:
        st.session_state.show_login = False
    
    # Login button styled as a prominent button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Sign in with YouTube", key="login_youtube", 
                   help="Connect your YouTube account to upload videos"):
            st.session_state.show_login = True
    
    # Show modal popup when login button is clicked
    if st.session_state.show_login:
        modal_html = """
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background-color: rgba(0,0,0,0.7); z-index: 1000; 
                    display: flex; justify-content: center; align-items: center;">
            <div style="background-color: white; padding: 20px; border-radius: 10px; 
                        max-width: 500px; width: 90%; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <h2 style="color: #FF0000; display: flex; align-items: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="red">
                        <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                    </svg>
                    &nbsp;YouTube Sign In
                </h2>
                <div class="streamlit-container">
                    <!-- Streamlit content will be injected here -->
                </div>
            </div>
        </div>
        """
        st.markdown(modal_html, unsafe_allow_html=True)
        
        # Authentication content
        client_secret_file = st.file_uploader("Upload your client_secret.json file", 
                                             type=["json"], key="popup_secret")
        
        # Close button
        if st.button("Cancel", key="close_popup"):
            st.session_state.show_login = False
            st.experimental_rerun()
        
        if client_secret_file:
            # Save client secret file
            client_secret_path = os.path.join(credentials_dir, 'client_secret.json')
            with open(client_secret_path, 'wb') as f:
                f.write(client_secret_file.getbuffer())
            
            # Create OAuth flow with improved UX
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                client_secret_path,
                scopes=['https://www.googleapis.com/auth/youtube.upload']
            )
            
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
            
            # Display nicer auth link with automatic window opening
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{auth_url}" target="_blank" style="background-color: #4285F4; color: white; 
                   padding: 10px 15px; border-radius: 5px; text-decoration: none; font-weight: bold;">
                   Open Google Sign In
                </a>
                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                    (A new window will open for secure authentication)
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Auto-focus on the code input field
            auth_code = st.text_input("Enter the authorization code:", key="popup_auth_code")
            
            if auth_code:
                try:
                    # Exchange auth code for credentials
                    flow.fetch_token(code=auth_code)
                    credentials = flow.credentials
                    
                    # Save credentials securely
                    with open(credentials_path, 'wb') as token:
                        pickle.dump(credentials, token)
                    
                    st.session_state.authenticated_youtube = True
                    st.session_state.show_login = False
                    st.success("✅ Successfully signed in to YouTube!")
                    time.sleep(1)  # Brief pause to show success message
                    st.experimental_rerun()
                    return credentials
                except Exception as e:
                    st.error(f"Authentication error: {str(e)}")
    
    return None

def upload_to_youtube(video_file, title, description, tags):
    """Upload video to YouTube with OAuth authentication"""
    # First authenticate
    credentials = authenticate_youtube()
    
    if credentials:
        try:
            # Build YouTube API client
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Prepare request body
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags.split(',') if tags else [],
                    'categoryId': '22'  # Category for People & Blogs
                },
                'status': {
                    'privacyStatus': 'private',  # Start as private for safety
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Upload video
            with st.spinner("Uploading video to YouTube..."):
                # Check if file exists and is valid
                if not os.path.exists(video_file) or os.path.getsize(video_file) == 0:
                    show_popup("Invalid Video File", "The video file is missing or invalid.", "error")
                    return False
                
                media = MediaFileUpload(video_file, mimetype='video/mp4', resumable=True)
                
                # Execute the request with progress bar
                request = youtube.videos().insert(
                    part='snippet,status',
                    body=body,
                    media_body=media
                )
                
                response = None
                progress_bar = st.progress(0)
                with st.empty():
                    status = st.empty()
                    for i in range(1, 101):
                        status.text(f"Uploading: {i}%")
                        progress_bar.progress(i)
                        if i == 100:
                            response = request.execute()
                        time.sleep(0.1)
                
                # Get video details
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Show success popup
                show_popup("Upload Successful", f"Video uploaded to YouTube! [View your video]({video_url})", "success")
                return True
        except Exception as e:
            st.error(f"Error uploading to YouTube: {str(e)}")
            return False
    else:
        show_popup("Authentication Required", "Please authenticate with YouTube before uploading.", "warning")
        return False

# MAIN APP
def main():
    # App header with logo
    st.markdown('<div class="top-header">', unsafe_allow_html=True)
    st.title("🎬 Video Creator & YouTube Uploader")
    st.write("Create videos with effects and upload to YouTube with AI-generated SEO content")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        step = st.radio("", ["1. Upload Media", "2. Create Video", 
                            "3. Video Information & SEO", "4. Upload to YouTube"], 
                       index=st.session_state.current_step - 1,
                       key="navigation")
        
        # Update current step
        for i, s in enumerate(["1. Upload Media", "2. Create Video", 
                              "3. Video Information & SEO", "4. Upload to YouTube"]):
            if step == s:
                st.session_state.current_step = i + 1
        
        st.markdown("---")
        st.markdown("### App Status")
        
        # Display authentication status
        if st.session_state.authenticated_youtube:
            st.success("✅ YouTube: Connected")
        else:
            st.warning("❌ YouTube: Not connected")
            
        if st.session_state.openai_key_set:
            st.success("✅ OpenAI: Connected")
        else:
            st.warning("❌ OpenAI: Not connected")
    
    # Content based on selected step
    if st.session_state.current_step == 1:
        st.header("Step 1: Upload Media")
        image_file, audio_file = upload_media()
        
        if image_file and audio_file:
            st.session_state.image_file = image_file
            st.session_state.audio_file = audio_file
            
            # Auto advance to next step
            if st.button("Continue to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
    
    elif st.session_state.current_step == 2:
        st.header("Step 2: Create Video with Effects")
        
        # Check if we have media files
        if not hasattr(st.session_state, 'image_file') or not hasattr(st.session_state, 'audio_file'):
            st.warning("Please upload image and audio files first.")
            if st.button("Go Back to Media Upload"):
                st.session_state.current_step = 1
                st.experimental_rerun()
        else:
            # Process video
            if st.button("Create Video with Glitch Effect") or st.session_state.get('processing_done', False):
                video_file = process_video(st.session_state.image_file, st.session_state.audio_file)
                if video_file:
                    st.session_state.video_file = video_file
                    
                    # Auto advance to next step
                    if st.button("Continue to Video Information"):
                        st.session_state.current_step = 3
                        st.experimental_rerun()
    
    elif st.session_state.current_step == 3:
        st.header("Step 3: Video Information & SEO")
        
        # Check if we have a video
        if not st.session_state.get('video_file'):
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            # Video Information
            col1, col2 = st.columns([2, 1])
            
            with col1:
                video_title = st.text_input("Video Title", key="title_input")
                video_description = st.text_area("Video Description", key="desc_input")
                video_tags = st.text_input("Tags (comma-separated)", key="tags_input")
            
            with col2:
                st.video(st.session_state.video_file)
            
            # Generate SEO content
            if st.button("Generate SEO Content with AI"):
                seo_title, seo_description, seo_tags = generate_seo_content(video_title, video_description)
                
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
                
                # Auto advance to next step
                if st.button("Continue to YouTube Upload"):
                    st.session_state.current_step = 4
                    st.experimental_rerun()
    
    elif st.session_state.current_step == 4:
        st.header("Step 4: Upload to YouTube")
        
        # Check for video file
        if not st.session_state.get('video_file'):
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
        else:
            # YouTube Authentication
            authenticate_youtube()
            
            # If authenticated, show upload form
            if st.session_state.authenticated_youtube:
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
                if st.button("Upload to YouTube"):
                    # Upload video
                    upload_to_youtube(st.session_state.video_file, title, description, tags)

if __name__ == "__main__":
    main()
