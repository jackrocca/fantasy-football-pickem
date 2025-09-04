# 🌩️ Streamlit Cloud + GitHub Actions Automation

This guide sets up automated NFL odds collection using GitHub Actions that runs on a schedule and stores data in Firestore, compatible with your Streamlit Cloud deployment.

## 🏗️ Architecture Overview

```
GitHub Actions (Scheduled) → The Odds API → Firestore ← Streamlit Cloud App
```

- **GitHub Actions**: Runs twice daily (9AM & 9PM PST) to collect data
- **Firestore**: Stores raw API responses for both automated and manual collections
- **Streamlit Cloud**: Your app reads from the same Firestore database

## 🚀 Setup Instructions

### 1. Push Your Code to GitHub

First, make sure your latest code is pushed to your GitHub repository:

```bash
git add .
git commit -m "Add automated NFL odds collection with GitHub Actions"
git push origin main
```

### 2. Set Up GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, then add these secrets:

#### Required Secrets:

**`ODDS_API_KEY`**
```
47ffefdd54760f7b66e51e715619516b
```

**`GCP_SERVICE_ACCOUNT_KEY`**
```json
{
  "type": "service_account",
  "project_id": "fantasy-pickem",
  "private_key_id": "e597455801249386e0ed95367c775d938195ccf4",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCfU2lCiuCW8+UB\nqi+3OvHCmJuIF+6L+27h4RMADHa1IbQodtJBsaLSo8yTuuzQj7XWS+krqSnZ8ivx\nHqg0Dm1sOY6L2lHa0SQlfYOCgvO2zAFZdTr/xQU/PSXoGnT30BdvIyDSBQkY5K/k\nZal6h5hAcA34Oaq75kyCqs2hP1bTQmKOal3JmG35W6fvji/bSei7cKaQpUYHIJUz\nMpoAa0gSYudLGukmDFKFh7bj3CgShl0DDaZ6tW+Jk62DLblahfJd29/iHb8kJrEn\ndNOySCKq0en8BkKdGf8OScWzqSJEr66lEL2nSciAsbtBx95Mhg6Zg1sPCop+nZ5K\na4qCy7KBAgMBAAECggEAJXaFf6IMITKEHJoZ0inIAwvDNoL6EmwyrGYyA4bquriM\nFh+qXMwaDxF43xvK51eDWDpNP3jtYFPzRSUCRAtIa3Q1MmlJafxXVYFn1N5Z1Bew\nEYrhLpbzHuWP7j2aV1LUz8sgwoFwnCvZuAi3ixorEKvIfR+CJ+CFCQyEgW/VSKMq\nIyW5M8i+6qHK/1+b1R3nnHAfy5MsS9ZxcSfOmC//pPu8M1nwMZYBAHgATUwJIT5h\nMbWcNfC8zBgEE3hUBWNA8pGNodbndlWDKLRGr5tMYSY6YU8IIlGjGVvHsgx/dXpg\nEXF1H4tCCpvL/05deIQbepl23FDh+PBPWp8R5sa+aQKBgQDbDyXOZHjWDiTh4wl5\n2Oo5V7L59kk2tMIx4EakklPaOQYKlzS7WpwWY0cfQ/5YJyptlGUK2XueooOqeBkq\nvUR3CZHAIovvLF6ikPTxkqRCDUfsyJwND4GoItuvfD67ARDvEjb2qBik0udwjGoo\nyIti52KB4IDv5QYMfePOur1jCwKBgQC6MY5ydszRYB8fmsdOszxayujUceiSPtHs\nhHCQhngM+zrA4A2XbOjVIL2Slf4zG8a/OJaAZIH4By2DVZB+1khBDiSTg9JhaDuF\n3Ni80Ex2UhMVfwMN5J2ZSXnUu4QHNeafNx+0+N9yDy0G6Sh4Ks9P2YSIaj9XQWhi\niYqMia54IwKBgBY6UUHCHCjMQp3RJdMBWbL73SNUBFXSvanF8iUc2/lWs/A7K5Sf\nOxtic4MOqS5Uuw9ncWFKdCrCns2bZiJaFipmBC4U01IvlGK2hsREdvpk0pmKOZtx\nqVxgPR5vYwYis48ur/kTUXzYEbfv542/27TrealoGG0/Nf/qfkUp2bHFAoGBAIig\n8tGF4bhGm7AaaOSUW9aYDRBP4gTm+i5f5SX4tsF33V5JS0/xyE0U8GdPj7A7UrVh\nNfdTSZgS1FAKirS4U18BnM9urQNzdDI/o/+xrloo0f41LK2WNBuWskLrsu+Dmw78\naVToRzcwca8fiuXbLDOA/2MG7CIASjP8j+Ge6psXAoGAe94x3zj8wLfAR4I7sJ8y\nze7aNnjl0w7q+eYkiYwSDYbX8+GLDayZjz69z9wieK5v0ELmtp3s3zA9ZW+V6frs\naQQVIrdtJdNlWknTRY8Diz0bDJIBfNP7z6IQcWfn57VUlU6FQL7SuRMX1SkUX28y\nBgovtavCgTvBR/yCLM04PhE="
  "client_email": "pickem-service@fantasy-pickem.iam.gserviceaccount.com",
  "client_id": "114379808114570268970",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/pickem-service%40fantasy-pickem.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

### 3. Enable GitHub Actions

1. Go to your repository → Actions tab
2. If prompted, enable GitHub Actions for your repository
3. The workflow should appear as "Automated NFL Odds Collection"

### 4. Test the Automation

#### Manual Test:
1. Go to Actions tab in your GitHub repository
2. Click "Automated NFL Odds Collection" workflow
3. Click "Run workflow" → "Run workflow" to test manually

#### Check Results:
- View the workflow logs to see if it ran successfully
- Check your Streamlit app's "Api Storage Test" page
- Look for entries with `API_TYPE: "GITHUB_ACTIONS_GET_ODDS"`

## 📅 Schedule Details

The automation runs twice daily:
- **9:00 AM PST** (17:00 UTC)
- **9:00 PM PST** (05:00 UTC next day)

**Note**: During Daylight Saving Time (PDT), the times shift by 1 hour:
- **9:00 AM PDT** (16:00 UTC) 
- **9:00 PM PDT** (04:00 UTC next day)

## 📊 Data Structure

Each automated run creates a Firestore document:

```json
{
  "API_TIMESTAMP": "2024-01-15T17:00:00Z",
  "API_TYPE": "GITHUB_ACTIONS_GET_ODDS",
  "API_PARAMETERS": {
    "regions": "us", 
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso"
  },
  "API_RESULTS": [...], // Raw NFL odds data
  "AUTOMATION_RUN": true,
  "AUTOMATION_SOURCE": "GITHUB_ACTIONS",
  "GAMES_COUNT": 16
}
```

## 🔍 Monitoring & Troubleshooting

### View Automation Logs
1. GitHub Repository → Actions tab
2. Click on any workflow run to see detailed logs
3. Check the "Run NFL odds collection" step for API results

### Check Data in Streamlit
1. Open your Streamlit Cloud app
2. Go to "Api Storage Test" page
3. Filter by "GITHUB_ACTIONS_GET_ODDS" to see automated collections

### Common Issues

**Workflow not running:**
- Check that secrets are properly set
- Verify the workflow file is in `.github/workflows/`
- Ensure repository has Actions enabled

**API errors:**
- Check that `ODDS_API_KEY` secret is correct
- Verify API usage limits on The Odds API dashboard

**Firestore errors:**
- Ensure `GCP_SERVICE_ACCOUNT_KEY` is properly formatted JSON
- Check Google Cloud project permissions
- Verify the service account has Firestore write permissions

## 💰 Cost Considerations

- **GitHub Actions**: Free tier includes 2,000 minutes/month (plenty for this use case)
- **The Odds API**: 2 calls/day × 365 days = 730 calls/year
- **Firestore**: Minimal storage and read/write costs for this volume

## 🛠️ Customization

### Change Schedule
Edit `.github/workflows/collect-nfl-odds.yml`:
```yaml
schedule:
  # Change these cron expressions (UTC times)
  - cron: '0 17 * * *'  # 9AM PST
  - cron: '0 5 * * *'   # 9PM PST
```

### Add More Data Collection
Extend `github_actions_collector.py` to collect additional endpoints:
- Sports list
- Event details  
- Scores data
- Historical odds

## 🎯 Benefits

✅ **Fully Cloud-Based**: No local infrastructure required
✅ **Streamlit Cloud Compatible**: Works seamlessly with your deployment
✅ **Reliable Scheduling**: GitHub Actions handles the timing
✅ **Cost Effective**: Uses free tiers for automation
✅ **Scalable**: Easy to extend for more data collection
✅ **Monitored**: Full logging and error tracking
✅ **Version Controlled**: Automation code is in your repository

## 🚀 Next Steps

1. **Push the code** to your GitHub repository
2. **Set up the secrets** in GitHub repository settings  
3. **Test manually** using "Run workflow" button
4. **Monitor the first scheduled runs** to ensure everything works
5. **Check your Streamlit app** to see the collected data

Your NFL odds data will now be automatically collected twice daily and available in your Streamlit Cloud app! 🎉
