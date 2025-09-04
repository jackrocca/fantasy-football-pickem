#!/usr/bin/env python3
"""
Automated NFL Odds Collector
Runs twice daily (9AM and 9PM PST) to collect and store raw NFL odds data.
"""
import os
import sys
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# Add the project root to Python path so we can import our modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up logging
def setup_logging():
    """Set up logging for automated runs."""
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "automated_odds_collector.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def load_secrets():
    """Load secrets from the secrets file for non-Streamlit environment."""
    secrets_file = os.path.join(project_root, ".streamlit", "secrets.toml")
    
    if not os.path.exists(secrets_file):
        raise FileNotFoundError(f"Secrets file not found: {secrets_file}")
    
    # Simple TOML parser for our specific needs
    secrets = {}
    current_section = None
    
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                if current_section not in secrets:
                    secrets[current_section] = {}
            elif '=' in line and current_section:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                # Handle escaped newlines in private keys
                if key == 'private_key':
                    value = value.replace('\\n', '\n')
                secrets[current_section][key] = value
    
    return secrets

def setup_environment():
    """Set up environment variables from secrets for non-Streamlit execution."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Loading secrets from .streamlit/secrets.toml...")
        secrets = load_secrets()
        
        # Set up Google Cloud credentials
        if "gcp_service_account" in secrets:
            logger.info("Found gcp_service_account in secrets")
            # Create a temporary service account file
            temp_creds_file = os.path.join(project_root, "temp_service_account.json")
            with open(temp_creds_file, 'w') as f:
                json.dump(secrets["gcp_service_account"], f)
            
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_file
            logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS to: {temp_creds_file}")
        else:
            logger.error("No gcp_service_account found in secrets")
            return False
        
        # Set up API keys
        if "api_keys" in secrets and "the_odds_api" in secrets["api_keys"]:
            os.environ["ODDS_API_KEY"] = secrets["api_keys"]["the_odds_api"]
            logger.info("Set ODDS_API_KEY from secrets")
        else:
            logger.error("No api_keys.the_odds_api found in secrets")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup environment: {str(e)}")
        return False

def cleanup_temp_files():
    """Clean up temporary files created during execution."""
    temp_creds_file = os.path.join(project_root, "temp_service_account.json")
    if os.path.exists(temp_creds_file):
        os.remove(temp_creds_file)

def collect_nfl_odds():
    """Collect NFL odds data and store in Firestore."""
    logger = logging.getLogger(__name__)
    
    try:
        # Import here after environment is set up
        from google.cloud import firestore
        from google.oauth2 import service_account
        import requests
        
        # Set up Firestore client
        creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_file or not os.path.exists(creds_file):
            raise ValueError(f"Google Cloud credentials file not found: {creds_file}")
        
        logger.info(f"Using credentials file: {creds_file}")
        credentials = service_account.Credentials.from_service_account_file(creds_file)
        
        # Get project ID from credentials file
        with open(creds_file, 'r') as f:
            creds_data = json.load(f)
            project_id = creds_data.get("project_id")
            if not project_id:
                raise ValueError("No project_id found in credentials file")
        
        logger.info(f"Connecting to Firestore project: {project_id}")
        db = firestore.Client(project=project_id, credentials=credentials)
        
        # Get API key
        api_key = os.environ.get("ODDS_API_KEY")
        if not api_key:
            raise ValueError("Odds API key not found")
        
        # Prepare API request
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
        params = {
            'api_key': api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american',
            'dateFormat': 'iso'
        }
        
        logger.info("Making API request to fetch NFL odds...")
        
        # Make API request
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        odds_data = response.json()
        logger.info(f"Successfully fetched {len(odds_data)} games from API")
        
        # Store raw API call in Firestore
        doc_data = {
            "API_TIMESTAMP": datetime.now(),
            "API_TYPE": "AUTOMATED_GET_ODDS",
            "API_PARAMETERS": params,
            "API_RESULTS": odds_data,
            "AUTOMATION_RUN": True,
            "GAMES_COUNT": len(odds_data) if isinstance(odds_data, list) else 0
        }
        
        # Add to Firestore
        doc_ref = db.collection('raw_api_calls').add(doc_data)
        doc_id = doc_ref[1].id
        
        logger.info(f"✅ Successfully stored API data with document ID: {doc_id}")
        logger.info(f"📊 Stored {len(odds_data)} NFL games")
        
        # Create game snapshot from the raw data
        logger.info("Creating game snapshot from raw data...")
        try:
            from utils.odds import create_game_snapshot
            
            snapshot_doc_id = create_game_snapshot(doc_id, odds_data)
            if snapshot_doc_id:
                logger.info(f"✅ Created game snapshot with document ID: {snapshot_doc_id}")
            else:
                logger.warning("⚠️ Failed to create game snapshot")
                
        except Exception as e:
            logger.error(f"❌ Error creating game snapshot: {str(e)}")
        
        return True, doc_id, len(odds_data)
        
    except requests.RequestException as e:
        logger.error(f"❌ API request failed: {str(e)}")
        return False, None, 0
    except Exception as e:
        logger.error(f"❌ Failed to collect NFL odds: {str(e)}")
        return False, None, 0

def main():
    """Main execution function."""
    logger = setup_logging()
    
    # Log the start of execution
    pst_tz = ZoneInfo("America/Los_Angeles")
    current_time = datetime.now(pst_tz)
    logger.info("=" * 60)
    logger.info(f"🚀 Starting automated NFL odds collection at {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("=" * 60)
    
    try:
        # Setup environment
        logger.info("Setting up environment...")
        if not setup_environment():
            logger.error("❌ Failed to setup environment")
            return 1
        
        logger.info("✅ Environment setup complete")
        
        # Collect odds data
        logger.info("Starting NFL odds collection...")
        success, doc_id, game_count = collect_nfl_odds()
        
        if success:
            logger.info("🎉 Automated collection completed successfully!")
            logger.info(f"📄 Document ID: {doc_id}")
            logger.info(f"🏈 Games collected: {game_count}")
        else:
            logger.error("❌ Automated collection failed!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Unexpected error during execution: {str(e)}")
        return 1
    
    finally:
        # Cleanup
        cleanup_temp_files()
        logger.info("🧹 Cleanup completed")
        logger.info("=" * 60)
        logger.info("📝 Automated NFL odds collection finished")
        logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
