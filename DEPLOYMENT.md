# Deployment Guide for Fantasy Football Pick'em League

## Quick Setup (Just Add Your Credentials)

### 1. Set Up Google OAuth (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set Application type to "Web application"
6. Add Authorized redirect URIs:
   - For local testing: `http://localhost:8501/oauth2callback`
   - For Streamlit Cloud: `https://your-app-name.streamlit.app/oauth2callback`

### 2. Configure Secrets

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and fill in your values:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"  # Update for production
cookie_secret = "your-strong-random-secret-here"      # Generate a random 32+ char string
client_id = "your-google-client-id"
client_secret = "your-google-client-secret" 
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

# Optional: For live betting lines (get free API key from the-odds-api.com)
[odds_api]
key = "your-odds-api-key"
```

### 3. Deploy to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Click "New app"
4. Connect your GitHub account and select this repository
5. Set Main file path: `app.py`
6. In "Advanced settings" → "Secrets", paste your production secrets:

```toml
[auth]
redirect_uri = "https://your-app-name.streamlit.app/oauth2callback"
cookie_secret = "your-strong-random-secret"
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[odds_api]
key = "your-odds-api-key"
```

7. Click "Deploy"

### 4. Update Google OAuth Redirect URI

After deployment, update your Google OAuth client with the production redirect URI:
`https://your-app-name.streamlit.app/oauth2callback`

## Local Development

```bash
pip install -r requirements.txt
python setup_sample_data.py  # Initialize with test data
streamlit run app.py
```

## Features Available Immediately

- ✅ User authentication with Google
- ✅ Sample NFL games with betting lines
- ✅ Pick submission with validation
- ✅ Scoreboard and standings
- ✅ Pick visibility controls
- ✅ Bonus point system

## Admin Functions

Use the Admin tab to:
- Update with real NFL game data
- Enter final scores manually
- Calculate weekly results
- View API usage stats

## Tips

- The app works with sample data immediately after setup
- Add The Odds API key for live betting lines
- Use the "Load Sample Games" button for testing
- All picks are automatically hidden until games start

That's it! Your pick'em league is ready to go.