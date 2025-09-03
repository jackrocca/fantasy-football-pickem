# Fantasy Football Pick'em League

A Streamlit web application for running a weekly fantasy football pick'em league with betting lines.

## Features

- **User Authentication**: Secure login with OIDC providers (Google, Auth0, etc.)
- **Weekly Picks**: Users select 4 picks per week (1 spread favorite, 1 underdog, 1 over, 1 under)
- **Live Betting Lines**: Fetches current NFL betting lines from The Odds API or ESPN
- **Scoring System**: 1 point per correct pick + bonus 5th point for perfect weeks
- **Scoreboard**: Season standings and weekly results
- **Pick Visibility**: Picks hidden until Thursday games start
- **Admin Panel**: Game management and result entry

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Authentication
Edit `.streamlit/secrets.toml`:
```toml
[auth]
provider = "google"  # or your OIDC provider
client_id = "your-client-id"
client_secret = "your-client-secret"
redirect_uri = "http://localhost:8501"
```

### 3. Optional: Configure Betting Lines API
For live betting lines, add to `.streamlit/secrets.toml`:
```toml
[odds_api]
key = "your-odds-api-key"
```
Get a free API key from [The Odds API](https://the-odds-api.com/)

### 4. Run the Application
```bash
streamlit run app.py
```

## Usage

1. **Login**: Users must authenticate to access the league
2. **Make Picks**: Submit exactly 4 picks before Thursday games start
3. **View Scoreboard**: Check season standings and weekly results
4. **Admin**: Update game data and enter final scores

## Database Schema

The application uses SQLite with tables for:
- `users`: Player accounts and authentication
- `games`: NFL games and betting lines
- `picks`: User selections per week
- `weekly_scores`: Calculated points and standings

## Scoring Rules

- 1 point for each correct pick
- Bonus 5th point for perfect weeks (4/4 correct)
- Picks must include: 1 spread favorite, 1 spread underdog, 1 over, 1 under