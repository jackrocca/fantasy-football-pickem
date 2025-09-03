# 🏈 Fantasy Football Pick'em League

A Streamlit-based web application for running a weekly fantasy football pick'em league with integrated betting lines, scoring, and season-long standings.

## Features

- **Secure Authentication**: User login system with admin privileges
- **Weekly Picks**: Select 4 picks per week (1 Favorite, 1 Underdog, 1 Over, 1 Under)
- **Live Betting Lines**: Integration with The Odds API with smart caching to preserve API credits
- **Powerups**: Special one-time abilities (Perfect Powerup, Line Helper)
- **Automatic Scoring**: Points calculation with perfect week bonuses
- **Admin Panel**: Tools for managing results, users, and league settings
- **Season Standings**: Track performance across the entire season

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd pickem-v2

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `.streamlit/secrets.toml` to add your users and API key:

```toml
[users]
john = "password123"
sarah = "mypassword"
mike = "league2024"
alice = "pickem123"

[admins]
john = true
alice = true

[api_keys]
the_odds_api = "YOUR_API_KEY"
```

**Get a free API key from [The Odds API](https://the-odds-api.com/)**

### 3. Run the Application

```bash
streamlit run Home.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure

```
fantasy-pickem/
│
├── Home.py                 # Main entry (login + dashboard)
│
├── /pages
│   ├── Pickem.py           # Weekly pick form
│   ├── Admin.py            # Admin panel
│
├── /utils
│   ├── auth.py             # Authentication
│   ├── odds.py             # Fetch/format betting lines
│   ├── scoring.py          # Scoring + powerups logic
│   ├── storage.py          # Read/write CSVs
│
├── /data
│   ├── picks.csv           # User picks
│   ├── results.csv         # Game results
│   ├── standings.csv       # Season standings
│
├── .streamlit/
│   └── secrets.toml        # User credentials + API keys
│
├── requirements.txt        # Dependencies
└── README.md               # This file
```

## How to Play

### For Users

1. **Login**: Use your username and password to access the app
2. **Make Picks**: Navigate to "Weekly Picks" and select:
   - 1 Spread Favorite (team you think will cover as favorite)
   - 1 Spread Underdog (team you think will cover as underdog) 
   - 1 Over (game total you think will go over the line)
   - 1 Under (game total you think will go under the line)
3. **Powerups**: Use special abilities (one-time per season):
   - **Perfect Powerup**: Perfect week = 8 points, otherwise 0 points
   - **Line Helper**: Adjust any Over/Under line by ±5 points
4. **View Results**: Check the dashboard for weekly scores and season standings

### Scoring System

- **+1 point** per correct pick
- **+1 bonus point** for perfect week (4/4) = **5 total points**
- **Perfect Powerup**: Perfect week = 8 points, imperfect = 0 points
- **Tie-breakers**: # of perfect weeks, then total correct picks

### Pick Deadlines

- Picks can be submitted/changed until **Thursday kickoff**
- After Thursday, picks are locked and visible to all users

## Admin Functions

### For Administrators

1. **Results Entry**: Input game scores and betting line results
2. **User Management**: View user activity and add new members
3. **Scoring**: Manually trigger scoring calculations
4. **Odds Cache**: Manage API calls and cached betting data
5. **League Settings**: Export data, reset seasons, manage locks

### Adding New Users

1. Edit `.streamlit/secrets.toml`
2. Add new entry under `[users]`: `username = "password"`
3. For admin access, add `username = true` under `[admins]`
4. Restart the application

## API Configuration

### The Odds API (Recommended)

1. Sign up at [The Odds API](https://the-odds-api.com/)
2. Get your free API key (500 requests/month)
3. Add to `.streamlit/secrets.toml`:
   ```toml
   [api_keys]
   the_odds_api = "your_api_key_here"
   ```

### Mock Data (Testing)

If no API key is provided, the app will use mock NFL data for testing.

### API Caching System

The app automatically caches odds data to preserve your API credits:

- **Automatic Caching**: Odds are cached for 24 hours after each API call
- **Smart Usage**: Cache is checked first before making new API calls
- **Admin Control**: Admins can manually refresh odds when needed
- **Credit Protection**: Prevents excessive API usage and preserves your monthly limit

**Best Practices:**
- Refresh odds once per week (Tuesday/Wednesday when lines are set)
- Monitor API usage in the Admin Panel
- Let the cache handle routine requests automatically

## Data Storage

The app uses CSV files for data storage:

- **picks.csv**: All user picks with timestamps and powerups
- **results.csv**: Game results for scoring calculations  
- **standings.csv**: Season-long user statistics
- **odds_cache.csv**: Cached betting lines to preserve API credits

Data can be exported through the Admin Panel or accessed directly from the `/data` folder.

## Troubleshooting

### Common Issues

1. **Login Failed**: Check username/password in `secrets.toml`
2. **No Games Available**: Verify API key or check The Odds API status
3. **Picks Not Saving**: Ensure all 4 picks are selected
4. **Admin Access Denied**: Verify user is listed under `[admins]` in `secrets.toml`

### File Permissions

Ensure the app has write permissions to the `/data` directory for CSV operations.

### API Limits

The free tier of The Odds API includes 500 requests/month. Each app load fetches odds once.

## Advanced Configuration

### Custom Scoring

Modify `utils/scoring.py` to customize:
- Point values per correct pick
- Perfect week bonuses
- Powerup effects
- Tie-breaker logic

### Additional Powerups

Add new powerups by extending:
- `utils/scoring.py` (logic)
- `pages/Pickem.py` (UI)
- `utils/storage.py` (data storage)

### Database Migration

To use SQLite instead of CSV:
1. Install SQLite dependencies
2. Replace `utils/storage.py` functions
3. Create database schema
4. Migrate existing CSV data

## Contributing

This is a self-contained application designed for small leagues. Feel free to modify and extend based on your league's needs.

## License

This project is open source and available under the MIT License.

---

**Questions?** Check the Admin Panel for system information and data exports.
