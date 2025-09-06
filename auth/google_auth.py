"""
Google OAuth Authentication for Streamlit - Improved Version
"""
import streamlit as st
import requests
import json
import secrets
import hashlib

# OAuth 2.0 configuration
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

def generate_state():
    """Generate a random state parameter for CSRF protection."""
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

def authenticate_user():
    """Handle Google OAuth authentication."""
    
    # Check if user is already authenticated
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return True
    
    # Check for authorization code in URL
    if 'code' in st.query_params:
        try:
            # Verify state parameter (CSRF protection)
            if 'state' in st.query_params:
                stored_state = st.session_state.get('oauth_state')
                if stored_state and st.query_params['state'] != stored_state:
                    st.error("Invalid state parameter. Please try again.")
                    st.query_params.clear()
                    st.rerun()
                    return False
            
            # Exchange authorization code for access token
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'code': st.query_params['code'],
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI
            }
            
            response = requests.post(token_url, data=token_data)
            
            if response.status_code != 200:
                st.error(f"Token exchange failed: {response.status_code}")
                st.error(f"Response: {response.text}")
                st.query_params.clear()
                st.rerun()
                return False
            
            token_info = response.json()
            
            if 'access_token' in token_info:
                # Get user info
                user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {'Authorization': f"Bearer {token_info['access_token']}"}
                user_response = requests.get(user_info_url, headers=headers)
                
                if user_response.status_code != 200:
                    st.error(f"Failed to get user info: {user_response.status_code}")
                    st.error(f"Response: {user_response.text}")
                    st.query_params.clear()
                    st.rerun()
                    return False
                
                user_info = user_response.json()
                
                # Store user information in session state
                st.session_state.authenticated = True
                st.session_state.user_profile = {
                    "user_id": user_info['id'],
                    "email": user_info['email'],
                    "name": user_info.get('name', ''),
                    "picture": user_info.get('picture', ''),
                    "access_token": token_info['access_token']
                }
                
                # Clear URL parameters and state
                st.query_params.clear()
                if 'oauth_state' in st.session_state:
                    del st.session_state['oauth_state']
                st.rerun()
                
                return True
            else:
                st.error(f"Authentication failed: {token_info}")
                st.query_params.clear()
                st.rerun()
                return False
                
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.query_params.clear()
            st.rerun()
            return False
    
    # Show login button
    st.markdown("### 🔐 Sign in with Google")
    st.markdown("Please sign in to access your personalized autism support assistant.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Sign in with Google", type="primary", use_container_width=True):
            # Generate state parameter
            state = generate_state()
            st.session_state['oauth_state'] = state
            
            # Create authorization URL
            auth_url = (
                f"https://accounts.google.com/o/oauth2/auth?"
                f"client_id={CLIENT_ID}&"
                f"redirect_uri={REDIRECT_URI}&"
                f"scope=openid%20email%20profile&"
                f"response_type=code&"
                f"access_type=offline&"
                f"state={state}"
            )
            st.markdown(f'<a href="{auth_url}" target="_self">Click here to authenticate</a>', unsafe_allow_html=True)
    
    return False

def logout_user():
    """Logout user and clear session."""
    st.session_state.clear()
    st.rerun()

def get_user_id():
    """Get current user ID."""
    if st.session_state.get('authenticated') and st.session_state.get('user_profile'):
        return st.session_state.user_profile['user_id']
    return "default"