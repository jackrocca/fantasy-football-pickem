#!/usr/bin/env python3
"""
GitHub Actions NFL Scores Collector
Runs on GitHub Actions schedule to collect and store NFL scores.
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

def collect_nfl_scores():
    """Collect NFL scores and store in Firestore."""
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
        
        # Prepare API request for NFL scores
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores"
        params = {
            'api_key': api_key,
            'daysFrom': 1,  # Get completed games from last 1 day (cost = 2)
            'dateFormat': 'iso'
        }
        
        logger.info("Making API request to fetch NFL scores...")
        
        # Make API request
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        scores_data = response.json()
        logger.info(f"Successfully fetched scores for {len(scores_data)} games from API")
        
        # Store raw API call first
        raw_doc_data = {
            "API_TIMESTAMP": datetime.now(),
            "API_TYPE": "GITHUB_ACTIONS_GET_SCORES",
            "API_PARAMETERS": params,
            "API_RESULTS": scores_data,
            "AUTOMATION_RUN": True,
            "AUTOMATION_SOURCE": "GITHUB_ACTIONS",
            "GAMES_COUNT": len(scores_data) if isinstance(scores_data, list) else 0
        }
        
        # Add raw data to Firestore
        raw_doc_ref = db.collection('raw_api_calls').add(raw_doc_data)
        raw_doc_id = raw_doc_ref[1].id
        
        logger.info(f"✅ Stored raw scores API data with document ID: {raw_doc_id}")
        
        # Process scores and create scores collection
        scores_games = []
        completed_count = 0
        
        for game in scores_data:
            # Only process completed games with scores
            if not game.get('completed', False) or not game.get('scores'):
                continue
                
            completed_count += 1
            
            # Extract team scores
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            home_score = 0
            away_score = 0
            
            for score in game.get('scores', []):
                team_name = score.get('name', '')
                try:
                    team_score = int(score.get('score', 0))
                except (ValueError, TypeError):
                    team_score = 0
                
                if team_name == home_team:
                    home_score = team_score
                elif team_name == away_team:
                    away_score = team_score
            
            total_points = home_score + away_score
            
            scores_games.append({
                'SNAPSHOT_ID': raw_doc_id,  # Link to raw API call
                'SNAPSHOT_CREATION_DATE': datetime.now(),
                'GAME_ID': game.get('id', ''),
                'HOME_TEAM': home_team,
                'HOME_TEAM_SCORE': home_score,
                'AWAY_TEAM': away_team,
                'AWAY_TEAM_SCORE': away_score,
                'TOTAL_GAME_POINTS': total_points
            })
        
        if scores_games:
            # Store scores snapshot
            scores_snapshot = {
                'SNAPSHOT_ID': raw_doc_id,
                'SNAPSHOT_CREATION_DATE': datetime.now(),
                'TOTAL_COMPLETED_GAMES': len(scores_games),
                'SCORES': scores_games
            }
            
            scores_doc_ref = db.collection('game_scores').add(scores_snapshot)
            scores_doc_id = scores_doc_ref[1].id
            
            logger.info(f"✅ Created scores snapshot with document ID: {scores_doc_id}")
            logger.info(f"📊 Processed {completed_count} completed games with scores")
        else:
            logger.info("ℹ️ No completed games with scores found")
        
        return True, raw_doc_id, completed_count
        
    except requests.RequestException as e:
        logger.error(f"❌ API request failed: {str(e)}")
        return False, None, 0
    except Exception as e:
        logger.error(f"❌ Failed to collect NFL scores: {str(e)}")
        return False, None, 0

def main():
    """Main execution function."""
    logger = setup_logging()
    
    # Log the start of execution
    current_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🏈 Starting GitHub Actions NFL scores collection at {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)
    
    try:
        # Collect scores data
        logger.info("Starting NFL scores collection...")
        success, doc_id, completed_count = collect_nfl_scores()
        
        if success:
            logger.info("🎉 GitHub Actions scores collection completed successfully!")
            logger.info(f"📄 Raw data document ID: {doc_id}")
            logger.info(f"🏈 Completed games processed: {completed_count}")
            
            # Set GitHub Actions output for potential use in other steps
            if os.environ.get('GITHUB_ACTIONS'):
                print(f"::set-output name=success::true")
                print(f"::set-output name=document_id::{doc_id}")
                print(f"::set-output name=completed_games::{completed_count}")
        else:
            logger.error("❌ GitHub Actions scores collection failed!")
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
    logger.info("📝 GitHub Actions NFL scores collection finished")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
