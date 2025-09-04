#!/usr/bin/env python3
"""
GitHub Actions NFL Odds Collector
Runs on GitHub Actions schedule to collect and store raw NFL odds data.
"""
import os
import json
import logging
from datetime import datetime

def setup_logging():
    """Set up logging for GitHub Actions runs."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def collect_nfl_odds():
    """Collect NFL odds data and store in Firestore."""
    logger = logging.getLogger(__name__)
    
    try:
        # Import required libraries
        from google.cloud import firestore
        from google.oauth2 import service_account
        import requests
        
        # Set up Firestore client using environment variables
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
        
        # Get API key from environment
        api_key = os.environ.get("ODDS_API_KEY")
        if not api_key:
            raise ValueError("ODDS_API_KEY environment variable not found")
        
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
            "API_TYPE": "GITHUB_ACTIONS_GET_ODDS",
            "API_PARAMETERS": params,
            "API_RESULTS": odds_data,
            "AUTOMATION_RUN": True,
            "AUTOMATION_SOURCE": "GITHUB_ACTIONS",
            "GAMES_COUNT": len(odds_data) if isinstance(odds_data, list) else 0
        }
        
        # Add to Firestore
        doc_ref = db.collection('raw_api_calls').add(doc_data)
        doc_id = doc_ref[1].id
        
        logger.info(f"✅ Successfully stored API data with document ID: {doc_id}")
        logger.info(f"📊 Stored {len(odds_data)} NFL games")
        
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
    current_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🚀 Starting GitHub Actions NFL odds collection at {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)
    
    try:
        # Collect odds data
        logger.info("Starting NFL odds collection...")
        success, doc_id, game_count = collect_nfl_odds()
        
        if success:
            logger.info("🎉 GitHub Actions collection completed successfully!")
            logger.info(f"📄 Document ID: {doc_id}")
            logger.info(f"🏈 Games collected: {game_count}")
            
            # Set GitHub Actions output for potential use in other steps
            if os.environ.get('GITHUB_ACTIONS'):
                print(f"::set-output name=success::true")
                print(f"::set-output name=document_id::{doc_id}")
                print(f"::set-output name=games_count::{game_count}")
        else:
            logger.error("❌ GitHub Actions collection failed!")
            if os.environ.get('GITHUB_ACTIONS'):
                print(f"::set-output name=success::false")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Unexpected error during execution: {str(e)}")
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::set-output name=success::false")
            print(f"::error::Unexpected error: {str(e)}")
        return 1
    
    logger.info("=" * 60)
    logger.info("📝 GitHub Actions NFL odds collection finished")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
