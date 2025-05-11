import streamlit as st
import os
import tempfile
import json
import time
import requests
from PIL import Image
import base64
import uuid
import io

# Handle Google API imports with error checking
try:
    import google_auth_oauthlib.flow
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    GOOGLE_IMPORTS_SUCCESS = True
except ImportError:
    GOOGLE_IMPORTS_SUCCESS = False

# Set page configuration
st.set_page_config(
    page_title="Video Creator & YouTube Uploader",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for popup-style dialogs and Google sign-in
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
    .stButton button {
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .top-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .google-button {
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 4px;
        color: #757575;
        cursor: pointer;
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        font-weight: 500;
        height: 40px;
        letter-spacing: 0.25px;
        min-width: 240px;
        padding: 0 12px;
        text-align: center;
        transition: background-color .218s, border-color .218s, box-shadow .218s;
    }
    .google-button:hover {
        background-color: #f8f8f8;
        border-color: #c6c6c6;
        box-shadow: 0 1px 1px rgba(0,0,0,0.1);
    }
    .google-button:active {
        background-color: #f6f6f6;
    }
    .google-button img {
        height: 18px;
        margin-right: 12px;
        vertical-align: middle;
        width: 18px;
    }
    .google-button span {
        vertical-align: middle;
    }
    .processing-preview {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin-top: 15px;
        background-color: #f8f9fa;
    }
    .video-effect-option {
        margin: 10px;
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 5px;
        text-align: center;
        cursor: pointer;
    }
    .video-effect-option.selected {
        border: 2px solid #4285F4;
        background-color: #e8f0fe;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "google_user_info" not in st.session_state:
    st.session_state.google_user_info = None
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = None
if "youtube_credentials" not in st.session_state:
    st.session_state.youtube_credentials = None
if "video_file" not in st.session_state:
    st.session_state.video_file = None
if "image_file" not in st.session_state:
    st.session_state.image_file = None
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "selected_effect" not in st.session_state:
    st.session_state.selected_effect = "glitch"
if "video_processing_id" not in st.session_state:
    st.session_state.video_processing_id = None

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

# Google Authentication
def google_sign_in():
    """Implementation of Google Sign-In with OAuth"""
    if "google_auth_url" not in st.session_state:
        # Create OAuth flow for Google Sign-In
        try:
            # For production, use GOCSPX- client ID and secret from Google Cloud Console
            # For this example, we'll use placeholder credentials - replace with your own
            client_id = st.secrets.get("google_client_id", os.getenv("GOOGLE_CLIENT_ID"))
            client_secret = st.secrets.get("google_client_secret", os.getenv("GOOGLE_CLIENT_SECRET"))
            
            if not client_id or not client_secret:
                st.warning("Google OAuth credentials not configured. In a real app, you would set these in Streamlit secrets.")
                # For demo purposes, provide a mock sign-in option
                if st.button("Sign in with Google (Demo mode)"):
                    # Mock user info
                    st.session_state.google_user_info = {
                        "name": "Demo User",
                        "email": "demo@example.com",
                        "picture": "https://ui-avatars.com/api/?name=Demo+User"
                    }
                    st.success("✅ Signed in with Google (Demo mode)")
                    st.experimental_rerun()
                return
            
            # Create a flow instance to manage the OAuth 2.0 Authorization Grant Flow
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:8501/callback"]
                    }
                },
                scopes=[
                    'https://www.googleapis.com/auth/userinfo.email', 
                    'https://www.googleapis.com/auth/userinfo.profile',
                    'https://www.googleapis.com/auth/youtube.upload'
                ]
            )
            
            # Use the redirect URI where the authorization response will be sent
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            
            # Generate the authorization URL
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            st.session_state.google_auth_flow = flow
            st.session_state.google_auth_url = authorization_url
            
        except Exception as e:
            st.error(f"Error setting up Google authentication: {str(e)}")
    
    # Show Google sign-in button
    st.markdown("""
    <div style="display: flex; justify-content: center; margin: 20px 0;">
        <a href="#" id="google-signin" class="google-button">
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" alt="Google logo">
            <span>Sign in with Google</span>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Display the authentication URL and code input
    if "google_auth_url" in st.session_state:
        st.markdown(f"""
        <a href="{st.session_state.google_auth_url}" target="_blank" style="text-decoration: none;">
            <div style="text-align: center; background-color: #4285F4; color: white; padding: 10px; border-radius: 5px; margin: 10px 0;">
                Click to Open Google Sign-in Page
            </div>
        </a>
        """, unsafe_allow_html=True)
        
        auth_code = st.text_input("Enter the authorization code from Google:", key="google_auth_code")
        
        if auth_code:
            try:
                # Exchange authorization code for credentials
                flow = st.session_state.google_auth_flow
                flow.fetch_token(code=auth_code)
                credentials = flow.credentials
                
                # Store credentials
                st.session_state.youtube_credentials = credentials
                
                # Get user info
                user_info_service = build('oauth2', 'v2', credentials=credentials)
                user_info = user_info_service.userinfo().get().execute()
                
                st.session_state.google_user_info = user_info
                st.success(f"✅ Successfully signed in as {user_info['email']}")
                
                # Clear auth info now that we're logged in
                if "google_auth_url" in st.session_state:
                    del st.session_state.google_auth_url
                if "google_auth_flow" in st.session_state:
                    del st.session_state.google_auth_flow
                
                time.sleep(1)
                st.experimental_rerun()
                
            except Exception as e:
                st.error(f"Authentication error: {str(e)}")

# 1. MEDIA UPLOADER COMPONENT
def upload_media():
    """Upload image and audio files"""
    col1, col2 = st.columns(2)
    
    image_path = None
    audio_path = None
    
    with col1:
        st.markdown("### Upload Image")
        uploaded_image = st.file_uploader("Select an image file", type=["jpg", "jpeg", "png"], key="image_upload")
        if uploaded_image is not None:
            st.success("✅ Image uploaded!")
            st.image(Image.open(uploaded_image), width=300)
            
            # Save to temporary file
            image_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
            with open(image_path, "wb") as f:
                f.write(uploaded_image.getbuffer())
            
            # Also store the image bytes for API usage
            st.session_state.image_bytes = uploaded_image.getvalue()
    
    with col2:
        st.markdown("### Upload Audio")
        uploaded_audio = st.file_uploader("Select an audio file", type=["mp3", "wav"], key="audio_upload")
        if uploaded_audio is not None:
            st.success("✅ Audio uploaded!")
            st.audio(uploaded_audio)
            
            # Save to temporary file
            audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
            with open(audio_path, "wb") as f:
                f.write(uploaded_audio.getbuffer())
            
            # Also store the audio bytes for API usage
            st.session_state.audio_bytes = uploaded_audio.getvalue()
    
    return image_path, audio_path

# 2. VIDEO PROCESSOR COMPONENT - Cloud API Version
def process_video_with_api(image_bytes, audio_bytes, effect_type="glitch"):
    """Create a video using a cloud video processing API instead of FFmpeg"""
    if not image_bytes or not audio_bytes:
        show_popup("Missing Files", "Please upload both image and audio files first.", "warning")
        return None
    
    # Using the mock API for demonstration - in a real app, you'd call an actual service
    # E.g., Cloudinary, Kapwing, or a custom API endpoint you've created
    api_endpoint = "https://mockapi.videoprocessing.example/create"
    
    try:
        with st.spinner("Creating your video with effects... (Demo Mode)"):
            # In a real implementation, you would:
            # 1. Encode files for upload
            # 2. Make API request
            # 3. Get processing ID or result URL
            
            # For demo purposes, we'll simulate processing steps
            # Show a processing preview
            st.markdown("""
            <div class="processing-preview">
                <h4>Video Processing Preview</h4>
                <div style="display: flex; align-items: center;">
                    <div style="flex: 1; text-align: center;">
                        <p>Input Image</p>
                        <img src="data:image/jpeg;base64,{}" alt="Input Image" style="max-width: 150px; max-height: 150px;">
                    </div>
                    <div style="margin: 0 20px;">➡️</div>
                    <div style="flex: 1; text-align: center;">
                        <p>Effect: {}</p>
                        <div style="background-color: #eee; height: 150px; display: flex; align-items: center; justify-content: center;">
                            <div class="spinner"></div>
                            <p>Processing...</p>
                        </div>
                    </div>
                </div>
            </div>
            """.format(
                base64.b64encode(image_bytes).decode(),
                effect_type
            ), unsafe_allow_html=True)
            
            # Simulate API processing time
            progress_bar = st.progress(0)
            for i in range(101):
                time.sleep(0.05)
                progress_bar.progress(i)
            
            # Generate a unique ID for this video
            video_id = str(uuid.uuid4())
            
            # In a real app, this is where you would get the URL of the processed video
            # For demo, we'll use a sample video
            sample_videos = {
                "glitch": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "zoom": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
                "fade": "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
            }
            
            video_url = sample_videos.get(effect_type, sample_videos["glitch"])
            
            st.success("✅ Video created successfully!")
            st.video(video_url)
            
            # Store the video URL in session state
            st.session_state.video_url = video_url
            st.session_state.video_processing_id = video_id
            
            return video_url
            
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        return None

# 3. SEO GENERATOR COMPONENT
def generate_seo_content(title, description):
    """Generate SEO content using OpenAI API"""
    if not title:
        show_popup("Missing Title", "Please enter a video title first.", "warning")
        return None, None, None
    
    # Get OpenAI API key or set it from Google user info
    openai_api_key = None
    
    # If user is logged in with Google, get/set their OpenAI key
    if st.session_state.google_user_info:
        # In a real app, you could store API keys securely for each Google user
        openai_api_key = st.session_state.get("openai_api_key")
        
        if not openai_api_key:
            with st.expander("Set OpenAI API Key for Your Google Account", expanded=True):
                st.info(f"Logged in as: {st.session_state.google_user_info.get('email', 'Unknown')}")
                input_key = st.text_input("Enter your OpenAI API key:", type="password")
                if st.button("Save API Key"):
                    if input_key and input_key.startswith("sk-"):
                        st.session_state.openai_api_key = input_key
                        st.success("✅ API key saved to your Google account!")
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.error("Invalid API key format.")
    else:
        st.warning("Please sign in with Google to use AI features")
        return (f"SEO-Optimized: {title}", 
                f"Auto-generated description for {title}. {description}", 
                "video, content, youtube")
    
    # Use the API key if available
    if openai_api_key:
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
        except Exception as e:
            st.error(f"Error generating SEO content: {str(e)}")
    
    # Fallback content
    return (f"SEO-Optimized: {title}", 
            f"Auto-generated description for {title}. {description}", 
            "video, content, youtube")

# 4. YOUTUBE UPLOADER COMPONENT
def upload_to_youtube(video_url, title, description, tags):
    """Upload video to YouTube using Google credentials"""
    if not st.session_state.google_user_info or not st.session_state.youtube_credentials:
        show_popup("Authentication Required", "Please sign in with Google to upload videos to YouTube.", "warning")
        return False
    
    if not video_url:
        show_popup("No Video", "Please create a video first.", "warning")
        return False
    
    try:
        with st.spinner("Uploading video to YouTube..."):
            # Get credentials
            credentials = st.session_state.youtube_credentials
            
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
            
            # For demo, use the video URL without actual upload
            st.info("In a real app, the video would be downloaded from the processing API and then uploaded to YouTube.")
            
            # Simulate progress
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i in range(1, 101):
                status.text(f"Uploading: {i}%")
                progress_bar.progress(i)
                time.sleep(0.05)
            
            # This is where you would actually upload the video
            # In a real app, you would:
            # 1. Download the video from video_url
            # 2. Upload it to YouTube with MediaFileUpload
            
            # Simulate successful upload
            video_id = "demo_" + str(uuid.uuid4())[:8]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Show success popup
            show_popup("Upload Successful", f"Video uploaded to YouTube! [View your video]({video_url})", "success")
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
    
    # Check if user is logged in with Google
    if not st.session_state.google_user_info:
        st.info("Please sign in with Google to use all features")
        google_sign_in()
        st.stop()  # Stop execution until user is authenticated
    else:
        # Show user info in sidebar
        with st.sidebar:
            user = st.session_state.google_user_info
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <img src="{user.get('picture', '')}" style="width: 50px; height: 50px; border-radius: 50%; margin-right: 10px;">
                <div>
                    <p style="margin: 0; font-weight: bold;">{user.get('name', 'User')}</p>
                    <p style="margin: 0; font-size: 0.8em; color: #666;">{user.get('email', '')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Sign Out"):
                for key in ['google_user_info', 'youtube_credentials', 'openai_api_key']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_rerun()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        
        # Define steps
        steps = ["1. Upload Media", "2. Create Video", 
                "3. Video Information & SEO", "4. Upload to YouTube"]
                
        # Use radio button for navigation
        current_step_index = st.session_state.current_step - 1
        if current_step_index >= len(steps):
            current_step_index = 0
            
        step = st.radio("", steps, index=current_step_index, key="navigation")
        
        # Update current step based on selection
        for i, s in enumerate(steps):
            if step == s:
                st.session_state.current_step = i + 1
        
        st.markdown("---")
        st.markdown("### App Status")
        
        # Display authentication status
        if st.session_state.openai_api_key:
            st.success("✅ OpenAI: Connected")
        else:
            st.warning("❌ OpenAI: Not connected")
            
        if st.session_state.youtube_credentials:
            st.success("✅ YouTube: Connected")
        else:
            st.warning("❌ YouTube: Not connected")
    
    # Content based on selected step
    if st.session_state.current_step == 1:
        st.header("Step 1: Upload Media")
        image_path, audio_path = upload_media()
        
        if image_path and audio_path:
            # Store paths in session state
            st.session_state.image_file = image_path
            st.session_state.audio_file = audio_path
            
            st.success("Both files uploaded successfully!")
            
            # Show continue button without immediate rerun
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
            # Video effect selection
            st.subheader("Select Video Effect")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Glitch Effect", key="glitch_effect"):
                    st.session_state.selected_effect = "glitch"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "glitch":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px;'>✓ Selected</div>", unsafe_allow_html=True)
            
            with col2:
                if st.button("Zoom Effect", key="zoom_effect"):
                    st.session_state.selected_effect = "zoom"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "zoom":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px;'>✓ Selected</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Fade Effect", key="fade_effect"):
                    st.session_state.selected_effect = "fade"
                    st.experimental_rerun()
                if st.session_state.selected_effect == "fade":
                    st.markdown("<div style='background-color:#e8f0fe; padding:10px; border-radius:5px;'>✓ Selected</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Process video
            if st.button("Create Video", key="create_video") or "video_url" in st.session_state:
                if "video_url" not in st.session_state:
                    video_url = process_video_with_api(
                        st.session_state.image_bytes,
                        st.session_state.audio_bytes,
                        st.session_state.selected_effect
                    )
                    if video_url:
                        st.session_state.video_url = video_url
                else:
                    st.success("✅ Video already created!")
                    st.video(st.session_state.video_url)
                
                # Auto advance to next step
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
                video_title = st.text_input("Video Title", key="title_input")
                video_description = st.text_area("Video Description", key="desc_input")
                video_tags = st.text_input("Tags (comma-separated)", key="tags_input")
            
            with col2:
                st.video(st.session_state.video_url)
            
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
        
        if not st.session_state.google_user_info:
            st.warning("Please sign in with Google to upload to YouTube.")
            st.stop()
            
        # Check for video
        if "video_url" not in st.session_state:
            st.warning("Please create a video first.")
            if st.button("Go Back to Video Creation"):
                st.session_state.current_step = 2
                st.experimental_rerun()
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
            if st.button("Upload to YouTube"):
                upload_to_youtube(st.session_state.video_url, title, description, tags)

if __name__ == "__main__":
    main()
