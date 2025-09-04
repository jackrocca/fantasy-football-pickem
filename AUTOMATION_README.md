# 🤖 Automated NFL Odds Collection System

This system automatically collects NFL odds data twice daily and stores it in Firestore, ensuring you never miss valuable API data.

## 📋 Overview

- **Collection Schedule**: 9:00 AM and 9:00 PM PST daily
- **Data Storage**: Raw API responses stored in Firestore `raw_api_calls` collection
- **Automation Type**: Cron jobs running on your local system
- **Logging**: Comprehensive logs for monitoring and debugging

## 🚀 Quick Setup

### 1. Set Up the Cron Jobs

```bash
# Navigate to your project directory
cd "/Users/jrocca/Library/CloudStorage/GoogleDrive-jack@amrocca.com/My Drive/01_Projects/code-experiments/fantasy-football-pickem"

# Run the setup script
python setup_cron.py
```

The setup script will:
- ✅ Create log directories
- ✅ Check for existing cron jobs
- ✅ Install new cron jobs for 9AM and 9PM PST
- ✅ Offer to run a test execution

### 2. Verify Installation

```bash
# View your cron jobs
crontab -l

# You should see entries like:
# 0 17 * * * /path/to/.venv/bin/python /path/to/automated_odds_collector.py >> /path/to/logs/cron.log 2>&1
# 0 5 * * * /path/to/.venv/bin/python /path/to/automated_odds_collector.py >> /path/to/logs/cron.log 2>&1
```

## 📊 Monitoring

### View Logs
```bash
# Real-time log monitoring
tail -f logs/automated_odds_collector.log

# View cron execution logs
tail -f logs/cron.log

# View recent log entries
cat logs/automated_odds_collector.log | tail -50
```

### Check Firestore Data
1. Visit your Streamlit app's "Api Storage Test" page
2. Go to the "View Stored Data" tab
3. Filter by "AUTOMATED_GET_ODDS" to see automated collections

## 📁 File Structure

```
project/
├── automated_odds_collector.py    # Main automation script
├── setup_cron.py                 # Cron job setup utility
├── logs/                         # Log files directory
│   ├── automated_odds_collector.log
│   └── cron.log
└── utils/
    └── odds.py                   # Updated with raw storage system
```

## ⚙️ How It Works

### 1. Automated Script (`automated_odds_collector.py`)
- Runs independently of Streamlit
- Loads credentials from `.streamlit/secrets.toml`
- Makes API calls to fetch NFL odds
- Stores raw data in Firestore with metadata:
  - `API_TYPE`: "AUTOMATED_GET_ODDS"
  - `AUTOMATION_RUN`: true
  - `GAMES_COUNT`: Number of games collected

### 2. Cron Schedule
- **9:00 AM PST** (17:00 UTC): Morning collection
- **9:00 PM PST** (05:00 UTC next day): Evening collection
- Runs every day of the year

### 3. Data Storage
Each automated run creates a Firestore document with:
```json
{
  "API_TIMESTAMP": "2024-01-15T09:00:00",
  "API_TYPE": "AUTOMATED_GET_ODDS", 
  "API_PARAMETERS": {
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso"
  },
  "API_RESULTS": [...], // Raw NFL odds data
  "AUTOMATION_RUN": true,
  "GAMES_COUNT": 16
}
```

## 🛠️ Troubleshooting

### Cron Jobs Not Running
```bash
# Check if cron service is running (macOS)
sudo launchctl list | grep cron

# Check cron logs
tail -f /var/log/cron.log  # Linux
log show --predicate 'process == "cron"' --last 1h  # macOS
```

### Script Errors
```bash
# Test manual execution
python automated_odds_collector.py

# Check permissions
ls -la automated_odds_collector.py
```

### API Issues
- Verify your API key in `.streamlit/secrets.toml`
- Check API usage limits on The Odds API dashboard
- Review error logs for specific API error messages

### Firestore Connection Issues
- Verify Google Cloud credentials in `.streamlit/secrets.toml`
- Test Firestore connection via the Streamlit app
- Check Google Cloud project permissions

## 📈 Expected Data Volume

- **2 collections per day** × **365 days** = **730 API calls per year**
- Each call typically returns **16-32 NFL games** during season
- Off-season calls return fewer games but still preserve data
- Storage cost in Firestore is minimal for this volume

## 🔧 Customization

### Change Schedule
Edit the cron times in `setup_cron.py`:
```python
cron_entries = [
    # Change these times (in UTC)
    f"0 17 * * * {python_path} {script_path}",  # 9AM PST
    f"0 5 * * * {python_path} {script_path}"   # 9PM PST
]
```

### Add More Data Collection
Extend `automated_odds_collector.py` to collect additional endpoints:
- Sports list
- Event details
- Scores data
- Historical odds

## 🗑️ Removal

To remove the cron jobs:
```bash
# Edit crontab
crontab -e

# Delete the lines containing "automated_odds_collector.py"
# Save and exit

# Or completely clear crontab (careful!)
crontab -r
```

## 📞 Support

If you encounter issues:
1. Check the logs first: `tail -f logs/automated_odds_collector.log`
2. Test manual execution: `python automated_odds_collector.py`
3. Verify cron installation: `crontab -l`
4. Check Firestore data via the Streamlit app

---

**🎯 Goal Achieved**: Your valuable API calls are now automatically collected and preserved twice daily, ensuring you never lose paid data and have a complete historical record of NFL odds!
