# Deployment Guide for Fantasy Football Pick'em League

## Super Quick Setup (2 minutes)

### 1. Configure Users and Passwords

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and add your league members:

```toml
[users]
john = "password123"
sarah = "mypassword"
mike = "league2024"
alice = "pickem123"
# Add more users as needed

# Optional: For live betting lines (get free API key from the-odds-api.com)
[odds_api]
key = "your-odds-api-key"
```

### 2. Deploy to Streamlit Cloud

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Click "New app" 
3. Connect your GitHub account and select the `fantasy-football-pickem` repository
4. Set Main file path: `app.py`
5. In "Advanced settings" → "Secrets", paste your user configuration:

```toml
[users]
john = "password123"
sarah = "mypassword"
mike = "league2024"
alice = "pickem123"

[odds_api]
key = "your-odds-api-key"
```

6. Click "Deploy"

That's it! No OAuth setup required.

## Local Development

```bash
pip install -r requirements.txt
python setup_sample_data.py  # Initialize with test data
streamlit run app.py
```

## Features Available Immediately

- ✅ Simple username/password authentication
- ✅ Sample NFL games with betting lines
- ✅ Pick submission with validation  
- ✅ Scoreboard and standings
- ✅ Pick visibility controls
- ✅ Bonus point system

## How It Works

1. **Login**: Users select their username and enter password
2. **Make Picks**: Choose exactly 4 picks (1 favorite, 1 underdog, 1 over, 1 under)
3. **Automatic Scoring**: App calculates results when you enter final scores
4. **Bonus Points**: Perfect weeks (4/4) earn a 5th bonus point
5. **Pick Visibility**: All picks hidden until Thursday games start

## Admin Functions

Use the Admin tab to:
- Update with real NFL game data (or use sample data)
- Enter final scores manually
- Calculate weekly results automatically
- View game status

## Super Simple Setup

1. Just add usernames/passwords to secrets.toml
2. Deploy to Streamlit Cloud
3. Done! No OAuth complexity needed

Your pick'em league is ready to go!