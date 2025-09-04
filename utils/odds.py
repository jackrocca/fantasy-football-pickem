"""
Betting odds utilities for fetching and formatting NFL lines.
"""
import requests
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from utils.firestore_client import get_firestore_client


def store_raw_api_call(api_type: str, api_parameters: dict, api_results: dict) -> str:
    """Store raw API call data in Firestore.
    
    Args:
        api_type: The type of API call (e.g., 'GET_odds', 'GET_sports', 'GET_events')
        api_parameters: Dictionary of parameters passed to the API
        api_results: Raw JSON response from the API
        
    Returns:
        Document ID of the stored record
    """
    try:
        db = get_firestore_client()
        
        # Create the document data
        doc_data = {
            "API_TIMESTAMP": datetime.now(),
            "API_TYPE": api_type,
            "API_PARAMETERS": api_parameters,
            "API_RESULTS": api_results
        }
        
        # Store in the 'raw_api_calls' collection
        doc_ref = db.collection('raw_api_calls').add(doc_data)
        doc_id = doc_ref[1].id
        
        return doc_id
        
    except Exception as e:
        st.error(f"Failed to store raw API call: {str(e)}")
        return ""


def make_odds_api_request(endpoint: str, params: dict) -> tuple[dict, str]:
    """Make a request to The Odds API and store the raw response.
    
    Args:
        endpoint: The API endpoint (e.g., 'odds', 'sports', 'events')
        params: Parameters for the API request
        
    Returns:
        Tuple of (api_response_data, document_id)
    """
    api_key = get_api_key()
    
    if not api_key or api_key == "YOUR_API_KEY":
        # For mock data, we'll still store it but mark it as mock
        mock_response = {"mock_data": True, "endpoint": endpoint}
        doc_id = store_raw_api_call(f"MOCK_{endpoint.upper()}", params, mock_response)
        return mock_response, doc_id
    
    # Construct the full URL
    base_url = "https://api.the-odds-api.com/v4"
    url = f"{base_url}/{endpoint}"
    
    # Add API key to parameters
    full_params = {**params, 'api_key': api_key}
    
    try:
        response = requests.get(url, params=full_params, timeout=10)
        response.raise_for_status()
        
        api_results = response.json()
        
        # Store the raw API call
        api_type = f"GET_{endpoint.upper()}"
        doc_id = store_raw_api_call(api_type, full_params, api_results)
        
        return api_results, doc_id
        
    except Exception as e:
        # Store the error as well for debugging
        error_response = {
            "error": True,
            "error_message": str(e),
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat()
        }
        doc_id = store_raw_api_call(f"ERROR_{endpoint.upper()}", full_params, error_response)
        raise e


def get_raw_api_calls(api_type: str = None, limit: int = 10) -> list:
    """Retrieve raw API calls from Firestore.
    
    Args:
        api_type: Filter by specific API type (e.g., 'GET_ODDS')
        limit: Maximum number of records to return
        
    Returns:
        List of raw API call documents
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection('raw_api_calls')
        
        # Build query
        query = collection_ref.order_by('API_TIMESTAMP', direction='DESCENDING').limit(limit)
        
        if api_type:
            query = query.where('API_TYPE', '==', api_type)
        
        # Execute query
        docs = query.stream()
        
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['document_id'] = doc.id
            # Convert timestamp to string for JSON serialization
            if 'API_TIMESTAMP' in doc_data:
                doc_data['API_TIMESTAMP'] = doc_data['API_TIMESTAMP'].isoformat()
            results.append(doc_data)
        
        return results
        
    except Exception as e:
        st.error(f"Failed to retrieve raw API calls: {str(e)}")
        return []


def extract_draftkings_odds(game_data: dict) -> dict:
    """Extract DraftKings odds data from a single game's API response.
    
    Args:
        game_data: Single game data from API response
        
    Returns:
        Dictionary with extracted DraftKings odds data
    """
    odds_data = {
        'BOOKMAKER': None,
        'H2H_HOME': None,
        'H2H_AWAY': None,
        'SPREAD_POINTS_HOME': None,
        'SPREAD_LINE_HOME': None,
        'SPREAD_POINTS_AWAY': None,
        'SPREAD_LINE_AWAY': None,
        'OVER_POINTS': None,
        'OVER_LINE': None,
        'UNDER_POINTS': None,
        'UNDER_LINE': None
    }
    
    try:
        bookmakers = game_data.get('bookmakers', [])
        draftkings_data = None
        
        # Find DraftKings bookmaker
        for bookmaker in bookmakers:
            if bookmaker.get('key') == 'draftkings':
                draftkings_data = bookmaker
                odds_data['BOOKMAKER'] = bookmaker.get('title', 'DraftKings')
                break
        
        if not draftkings_data:
            return odds_data
        
        markets = draftkings_data.get('markets', [])
        home_team = game_data.get('home_team', '')
        away_team = game_data.get('away_team', '')
        
        for market in markets:
            market_key = market.get('key')
            outcomes = market.get('outcomes', [])
            
            if market_key == 'h2h':
                # Extract head-to-head odds
                for outcome in outcomes:
                    team_name = outcome.get('name', '')
                    price = outcome.get('price')
                    
                    if team_name == home_team:
                        odds_data['H2H_HOME'] = price
                    elif team_name == away_team:
                        odds_data['H2H_AWAY'] = price
            
            elif market_key == 'spreads':
                # Extract spread odds
                for outcome in outcomes:
                    team_name = outcome.get('name', '')
                    point = outcome.get('point')
                    price = outcome.get('price')
                    
                    if team_name == home_team:
                        odds_data['SPREAD_POINTS_HOME'] = point
                        odds_data['SPREAD_LINE_HOME'] = price
                    elif team_name == away_team:
                        odds_data['SPREAD_POINTS_AWAY'] = point
                        odds_data['SPREAD_LINE_AWAY'] = price
            
            elif market_key == 'totals':
                # Extract over/under odds
                for outcome in outcomes:
                    outcome_name = outcome.get('name', '')
                    point = outcome.get('point')
                    price = outcome.get('price')
                    
                    if outcome_name == 'Over':
                        odds_data['OVER_POINTS'] = point
                        odds_data['OVER_LINE'] = price
                    elif outcome_name == 'Under':
                        odds_data['UNDER_POINTS'] = point
                        odds_data['UNDER_LINE'] = price
    
    except Exception as e:
        # Log error but return partial data
        pass
    
    return odds_data


def create_game_snapshot(raw_api_doc_id: str, api_results: list) -> str:
    """Create a game snapshot from raw API results.
    
    Args:
        raw_api_doc_id: Document ID of the raw API call
        api_results: List of games from the API response
        
    Returns:
        Document ID of the created snapshot, or empty string if failed
    """
    try:
        db = get_firestore_client()
        
        snapshot_games = []
        
        for game in api_results:
            # Extract basic game info
            game_snapshot = {
                'SNAPSHOT_ID': raw_api_doc_id,
                'SNAPSHOT_CREATION_DATE': datetime.now(),
                'GAME_ID': game.get('id'),
                'GAMETIME': game.get('commence_time'),
                'HOME_TEAM': game.get('home_team'),
                'AWAY_TEAM': game.get('away_team')
            }
            
            # Extract DraftKings odds
            draftkings_odds = extract_draftkings_odds(game)
            game_snapshot.update(draftkings_odds)
            
            snapshot_games.append(game_snapshot)
        
        # Store the snapshot in Firestore
        snapshot_data = {
            'SNAPSHOT_ID': raw_api_doc_id,
            'SNAPSHOT_CREATION_DATE': datetime.now(),
            'TOTAL_GAMES': len(snapshot_games),
            'GAMES': snapshot_games
        }
        
        # Add to the 'game_snapshots' collection
        doc_ref = db.collection('game_snapshots').add(snapshot_data)
        snapshot_doc_id = doc_ref[1].id
        
        return snapshot_doc_id
        
    except Exception as e:
        st.error(f"Failed to create game snapshot: {str(e)}")
        return ""


def process_raw_api_call_to_snapshot(raw_api_doc_id: str) -> str:
    """Process a raw API call and create a game snapshot.
    
    Args:
        raw_api_doc_id: Document ID of the raw API call to process
        
    Returns:
        Document ID of the created snapshot, or empty string if failed
    """
    try:
        db = get_firestore_client()
        
        # Get the raw API call document
        raw_doc = db.collection('raw_api_calls').document(raw_api_doc_id).get()
        
        if not raw_doc.exists:
            st.error(f"Raw API document {raw_api_doc_id} not found")
            return ""
        
        raw_data = raw_doc.to_dict()
        api_results = raw_data.get('API_RESULTS', [])
        
        if not api_results:
            st.error(f"No API results found in document {raw_api_doc_id}")
            return ""
        
        # Create the snapshot
        snapshot_doc_id = create_game_snapshot(raw_api_doc_id, api_results)
        
        if snapshot_doc_id:
            st.success(f"✅ Created game snapshot: {snapshot_doc_id}")
        
        return snapshot_doc_id
        
    except Exception as e:
        st.error(f"Failed to process raw API call to snapshot: {str(e)}")
        return ""


def get_game_snapshots(limit: int = 10) -> list:
    """Retrieve game snapshots from Firestore.
    
    Args:
        limit: Maximum number of snapshots to return
        
    Returns:
        List of game snapshot documents
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection('game_snapshots')
        
        # Build query
        query = collection_ref.order_by('SNAPSHOT_CREATION_DATE', direction='DESCENDING').limit(limit)
        
        # Execute query
        docs = query.stream()
        
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['document_id'] = doc.id
            # Convert timestamp to string for JSON serialization
            if 'SNAPSHOT_CREATION_DATE' in doc_data:
                doc_data['SNAPSHOT_CREATION_DATE'] = doc_data['SNAPSHOT_CREATION_DATE'].isoformat()
            results.append(doc_data)
        
        return results
        
    except Exception as e:
        st.error(f"Failed to retrieve game snapshots: {str(e)}")
        return []


def find_wednesday_9am_snapshot(week: int, year: int) -> dict:
    """Find the game snapshot closest to Wednesday 9AM PST for a given week.
    
    Args:
        week: NFL week number
        year: Year
        
    Returns:
        Game snapshot document or empty dict if not found
    """
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        db = get_firestore_client()
        collection_ref = db.collection('game_snapshots')
        
        # Get recent snapshots to work with
        query = collection_ref.order_by('SNAPSHOT_CREATION_DATE', direction='DESCENDING').limit(50)
        
        docs = query.stream()
        snapshots = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['document_id'] = doc.id
            snapshots.append(doc_data)
        
        if not snapshots:
            st.warning("No game snapshots found in Firestore")
            return {}
        
        # Production logic: Find snapshot closest to Wednesday 9AM PST
        # For now in development, we'll use the most recent snapshot
        # but include logic for production use
        
        pst_tz = ZoneInfo("America/Los_Angeles")
        best_snapshot = None
        min_diff = float('inf')
        
        # Calculate target Wednesday 9AM PST for the given week
        # This is a simplified approach - in production you'd want more precise week calculation
        current_date = datetime.now(pst_tz)
        
        # For development: just use the most recent snapshot
        # In production: calculate exact Wednesday 9AM and find closest
        for snapshot in snapshots:
            snapshot_time = snapshot.get('SNAPSHOT_CREATION_DATE')
            
            if snapshot_time:
                # Convert to datetime if it's not already
                if isinstance(snapshot_time, str):
                    snapshot_time = datetime.fromisoformat(snapshot_time.replace('Z', '+00:00'))
                
                # For now, just pick the most recent (first in our ordered list)
                if best_snapshot is None:
                    best_snapshot = snapshot
                    break
        
        if not best_snapshot:
            best_snapshot = snapshots[0]  # Fallback to most recent
        
        # Log which snapshot we're using
        snapshot_date = best_snapshot.get('SNAPSHOT_CREATION_DATE', 'Unknown')
        if hasattr(snapshot_date, 'strftime'):
            snapshot_date_str = snapshot_date.strftime('%Y-%m-%d %H:%M:%S %Z')
        else:
            snapshot_date_str = str(snapshot_date)[:19] if isinstance(snapshot_date, str) else str(snapshot_date)
        
        # Snapshot date logged for debugging but not shown to users
        
        return best_snapshot
        
    except Exception as e:
        st.error(f"Failed to find Wednesday 9AM snapshot: {str(e)}")
        return {}


def get_locked_lines_for_week(week: int, year: int) -> dict:
    """Get locked lines for a week based on Wednesday 9AM PST snapshot.
    
    Args:
        week: NFL week number
        year: Year
        
    Returns:
        Dictionary with formatted picks options from locked snapshot
    """
    try:
        snapshot = find_wednesday_9am_snapshot(week, year)
        
        if not snapshot or not snapshot.get('GAMES'):
            return {
                "favorites": ["No locked lines available"],
                "underdogs": ["No locked lines available"], 
                "overs": ["No locked lines available"],
                "unders": ["No locked lines available"],
                "snapshot_info": "No snapshot found"
            }
        
        # Filter games to only include games from the specified week
        all_games = snapshot['GAMES']
        week_games = filter_games_by_week(all_games, week, year)
        
        # Get scores to filter out completed games
        game_ids = [game.get('GAME_ID') for game in week_games if game.get('GAME_ID')]
        game_scores = get_scores_for_games(game_ids)
        
        favorites = []
        underdogs = []
        overs = []
        unders = []
        
        for game in week_games:
            home_team = game.get('HOME_TEAM', '')
            away_team = game.get('AWAY_TEAM', '')
            
            # Skip games without DraftKings odds
            if not game.get('BOOKMAKER') or game.get('BOOKMAKER') != 'DraftKings':
                continue
            
            # Skip completed games (can't be picked)
            game_id = game.get('GAME_ID', '')
            if game_id in game_scores and game_scores[game_id].get('completed', False):
                continue
                
            spread_home = game.get('SPREAD_POINTS_HOME')
            spread_away = game.get('SPREAD_POINTS_AWAY')
            over_points = game.get('OVER_POINTS')
            under_points = game.get('UNDER_POINTS')
            
            if spread_home is not None and spread_away is not None:
                if spread_home < 0:  # Home team is favorite
                    favorites.append(f"{home_team} ({spread_home})")
                    underdogs.append(f"{away_team} (+{abs(spread_away)})")
                else:  # Away team is favorite
                    favorites.append(f"{away_team} ({spread_away})")
                    underdogs.append(f"{home_team} (+{abs(spread_home)})")
            
            if over_points is not None and under_points is not None:
                overs.append(f"{away_team} vs {home_team} o{over_points}")
                unders.append(f"{away_team} vs {home_team} u{under_points}")
        
        snapshot_date = snapshot.get('SNAPSHOT_CREATION_DATE', 'Unknown')
        if isinstance(snapshot_date, str):
            snapshot_date = snapshot_date[:19]  # Trim to readable format
        
        return {
            "favorites": favorites if favorites else ["No favorites available"],
            "underdogs": underdogs if underdogs else ["No underdogs available"],
            "overs": overs if overs else ["No overs available"], 
            "unders": unders if unders else ["No unders available"],
            "snapshot_info": f"Lines locked from snapshot: {snapshot_date}",
            "snapshot_id": snapshot.get('document_id', '')
        }
        
    except Exception as e:
        st.error(f"Failed to get locked lines for week: {str(e)}")
        return {
            "favorites": ["Error loading lines"],
            "underdogs": ["Error loading lines"],
            "overs": ["Error loading lines"], 
            "unders": ["Error loading lines"],
            "snapshot_info": "Error loading snapshot"
        }


def save_picks_to_firestore(username: str, week: int, year: int, picks_data: dict) -> str:
    """Save user picks to Firestore.
    
    Args:
        username: User's username
        week: NFL week number
        year: Year
        picks_data: Dictionary containing all pick data
        
    Returns:
        Document ID of saved picks, or empty string if failed
    """
    try:
        db = get_firestore_client()
        
        # Create the picks document
        picks_doc = {
            'USER': username,
            'WEEK': week,
            'YEAR': year,
            'FAVORITE_GAME_ID': picks_data.get('favorite_game_id', ''),
            'FAVORITE_TEAM': picks_data.get('favorite_team', ''),
            'FAVORITE_SPREAD': picks_data.get('favorite_spread', 0),
            'UNDERDOG_GAME_ID': picks_data.get('underdog_game_id', ''),
            'UNDERDOG_TEAM': picks_data.get('underdog_team', ''),
            'UNDERDOG_SPREAD': picks_data.get('underdog_spread', 0),
            'OVER_GAME_ID': picks_data.get('over_game_id', ''),
            'OVER_POINTS': picks_data.get('over_points', 0),
            'UNDER_GAME_ID': picks_data.get('under_game_id', ''),
            'UNDER_POINTS': picks_data.get('under_points', 0),
            'SUPER_SPREAD': picks_data.get('super_spread', False),
            'SUPER_SPREAD_GAME_ID': picks_data.get('super_spread_game_id', ''),
            'SUPER_SPREAD_FAVORITE_LINE': picks_data.get('super_spread_favorite_line', 0),
            'TOTAL_HELPER': picks_data.get('total_helper', ''),  # 'OVER' or 'UNDER' or ''
            'TOTAL_HELPER_GAME_ID': picks_data.get('total_helper_game_id', ''),
            'TOTAL_HELPER_ADJUSTMENT': picks_data.get('total_helper_adjustment', 0),
            'PERFECT_PREDICTION': picks_data.get('perfect_prediction', False),
            'SUBMISSION_TIMESTAMP': datetime.now()
        }
        
        # Check if picks already exist for this user/week/year
        existing_query = (db.collection('picks')
                         .where('USER', '==', username)
                         .where('WEEK', '==', week)
                         .where('YEAR', '==', year)
                         .limit(1))
        
        existing_docs = list(existing_query.stream())
        
        if existing_docs:
            # Update existing picks
            doc_ref = existing_docs[0].reference
            doc_ref.update(picks_doc)
            doc_id = existing_docs[0].id
            st.success(f"✅ Updated existing picks for Week {week}")
        else:
            # Create new picks
            doc_ref = db.collection('picks').add(picks_doc)
            doc_id = doc_ref[1].id
            st.success(f"✅ Saved new picks for Week {week}")
        
        return doc_id
        
    except Exception as e:
        st.error(f"Failed to save picks to Firestore: {str(e)}")
        return ""


def get_user_picks_from_firestore(username: str, week: int, year: int) -> dict:
    """Get user picks from Firestore.
    
    Args:
        username: User's username
        week: NFL week number
        year: Year
        
    Returns:
        Dictionary with user's picks or empty dict if not found
    """
    try:
        db = get_firestore_client()
        
        query = (db.collection('picks')
                .where('USER', '==', username)
                .where('WEEK', '==', week)
                .where('YEAR', '==', year)
                .limit(1))
        
        docs = list(query.stream())
        
        if docs:
            picks_data = docs[0].to_dict()
            picks_data['document_id'] = docs[0].id
            
            # Convert timestamp to string for display
            if 'SUBMISSION_TIMESTAMP' in picks_data:
                picks_data['SUBMISSION_TIMESTAMP'] = picks_data['SUBMISSION_TIMESTAMP'].isoformat()
            
            return picks_data
        else:
            return {}
            
    except Exception as e:
        st.error(f"Failed to get user picks from Firestore: {str(e)}")
        return {}


def parse_pick_to_game_data(pick_string: str, snapshot_games: list) -> dict:
    """Parse a pick string to extract game data from snapshot.
    
    Args:
        pick_string: The formatted pick string (e.g., "Team (-7.5)" or "Team A vs Team B o47.5")
        snapshot_games: List of games from the snapshot
        
    Returns:
        Dictionary with game_id, team, and line information
    """
    try:
        if not pick_string or not snapshot_games:
            return {}
        
        # For spread picks: "Team Name (-X.X)" or "Team Name (+X.X)"
        if " (" in pick_string and pick_string.endswith(")"):
            team_name = pick_string.split(" (")[0]
            spread_str = pick_string.split("(")[1].replace(")", "")
            spread_value = float(spread_str)
            
            # Find the game this team is in
            for game in snapshot_games:
                if game.get('HOME_TEAM') == team_name or game.get('AWAY_TEAM') == team_name:
                    return {
                        'game_id': game.get('GAME_ID', ''),
                        'team': team_name,
                        'spread': spread_value,
                        'home_team': game.get('HOME_TEAM', ''),
                        'away_team': game.get('AWAY_TEAM', '')
                    }
        
        # For total picks: "Team A vs Team B oX.X" or "Team A vs Team B uX.X"
        elif " vs " in pick_string and (" o" in pick_string or " u" in pick_string):
            is_over = " o" in pick_string
            teams_part = pick_string.split(" o")[0] if is_over else pick_string.split(" u")[0]
            total_str = pick_string.split(" o")[1] if is_over else pick_string.split(" u")[1]
            total_value = float(total_str)
            
            teams = teams_part.split(" vs ")
            if len(teams) == 2:
                away_team = teams[0].strip()
                home_team = teams[1].strip()
                
                # Find the game
                for game in snapshot_games:
                    if (game.get('HOME_TEAM') == home_team and game.get('AWAY_TEAM') == away_team):
                        return {
                            'game_id': game.get('GAME_ID', ''),
                            'total_type': 'OVER' if is_over else 'UNDER',
                            'points': total_value,
                            'home_team': home_team,
                            'away_team': away_team
                        }
        
        return {}
        
    except Exception as e:
        return {}


def create_picks_data_from_form(favorite_pick: str, underdog_pick: str, over_pick: str, under_pick: str,
                                super_spread: bool, total_helper_choice: str, total_helper_adjustment: int,
                                perfect_prediction: bool, snapshot_games: list) -> dict:
    """Create picks data dictionary from form inputs.
    
    Args:
        favorite_pick: Favorite pick string
        underdog_pick: Underdog pick string  
        over_pick: Over pick string
        under_pick: Under pick string
        super_spread: Super spread powerup active
        total_helper_choice: Which pick to apply total helper to ('OVER' or 'UNDER' or '')
        total_helper_adjustment: Total helper adjustment value (always 5 or -5)
        perfect_prediction: Perfect prediction powerup active
        snapshot_games: List of games from snapshot
        
    Returns:
        Dictionary formatted for Firestore storage
    """
    picks_data = {}
    
    # Parse favorite pick
    if favorite_pick:
        fav_data = parse_pick_to_game_data(favorite_pick, snapshot_games)
        picks_data.update({
            'favorite_game_id': fav_data.get('game_id', ''),
            'favorite_team': fav_data.get('team', ''),
            'favorite_spread': fav_data.get('spread', 0)
        })
        
        # Super spread data
        if super_spread:
            picks_data.update({
                'super_spread_game_id': fav_data.get('game_id', ''),
                'super_spread_favorite_line': fav_data.get('spread', 0)
            })
    
    # Parse underdog pick
    if underdog_pick:
        und_data = parse_pick_to_game_data(underdog_pick, snapshot_games)
        picks_data.update({
            'underdog_game_id': und_data.get('game_id', ''),
            'underdog_team': und_data.get('team', ''),
            'underdog_spread': und_data.get('spread', 0)
        })
    
    # Parse over pick
    if over_pick:
        over_data = parse_pick_to_game_data(over_pick, snapshot_games)
        picks_data.update({
            'over_game_id': over_data.get('game_id', ''),
            'over_points': over_data.get('points', 0)
        })
        
    
    # Parse under pick
    if under_pick:
        under_data = parse_pick_to_game_data(under_pick, snapshot_games)
        picks_data.update({
            'under_game_id': under_data.get('game_id', ''),
            'under_points': under_data.get('points', 0)
        })
    
    # Handle Total Helper logic
    if total_helper_choice:
        if total_helper_choice == 'OVER' and over_pick:
            over_data = parse_pick_to_game_data(over_pick, snapshot_games)
            picks_data.update({
                'total_helper': 'OVER',
                'total_helper_game_id': over_data.get('game_id', ''),
                'total_helper_adjustment': total_helper_adjustment  # -5 for over (easier to hit)
            })
        elif total_helper_choice == 'UNDER' and under_pick:
            under_data = parse_pick_to_game_data(under_pick, snapshot_games)
            picks_data.update({
                'total_helper': 'UNDER',
                'total_helper_game_id': under_data.get('game_id', ''),
                'total_helper_adjustment': total_helper_adjustment  # +5 for under (easier to hit)
            })
    
    # Powerups
    picks_data.update({
        'super_spread': super_spread,
        'perfect_prediction': perfect_prediction
    })
    
    return picks_data


def filter_games_by_week(games: list, target_week: int, target_year: int) -> list:
    """Filter games to only include those from a specific NFL week.
    
    Args:
        games: List of games from snapshot
        target_week: NFL week number to filter for
        target_year: Year
        
    Returns:
        List of games from the specified week
    """
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        if not games:
            return []
        
        pst_tz = ZoneInfo("America/Los_Angeles")
        
        # Calculate the date range for the target NFL week
        # NFL weeks typically run Thursday to Wednesday (next week)
        # For 2025 season, Week 1 starts Thursday September 5th
        
        # Define the actual NFL Week 1 start date for 2025
        # This should be adjusted for each season based on the actual NFL schedule
        if target_year == 2025:
            # 2025 NFL Season starts Thursday, September 5th
            # But we need to include games that start Wednesday evening PST (Thursday night games)
            week_1_start = datetime(2025, 9, 4, hour=12, tzinfo=pst_tz)  # Wednesday noon, Sep 4
        else:
            # Fallback calculation for other years
            # Assumes Week 1 starts first Thursday after September 1st
            week_1_base = datetime(target_year, 9, 1, tzinfo=pst_tz)
            days_to_thursday = (3 - week_1_base.weekday()) % 7  # Thursday = 3
            if days_to_thursday == 0 and week_1_base.weekday() != 3:
                days_to_thursday = 7
            week_1_thursday = week_1_base + timedelta(days=days_to_thursday)
            # Start from Wednesday before the Thursday
            week_1_start = week_1_thursday - timedelta(days=1, hours=12)  # Wednesday noon
        
        # Calculate target week range
        # Each week runs from Wednesday noon to next Wednesday 11:59 AM
        target_week_start = week_1_start + timedelta(weeks=target_week-1)
        target_week_end = target_week_start + timedelta(days=6, hours=23, minutes=59)  # Next Tuesday 11:59 PM
        
        filtered_games = []
        
        for game in games:
            game_time_str = game.get('GAMETIME')
            if not game_time_str:
                continue
                
            try:
                # Parse the ISO datetime from the game
                game_time_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                game_time_pst = game_time_utc.astimezone(pst_tz)
                
                # Check if game falls within the target week range
                if target_week_start <= game_time_pst <= target_week_end:
                    filtered_games.append(game)
                    
            except Exception as e:
                # Skip games with unparseable times
                continue
        
        return filtered_games
        
    except Exception as e:
        st.error(f"Failed to filter games by week: {str(e)}")
        return games  # Return all games if filtering fails


def is_week_complete(week: int, year: int) -> bool:
    """Check if an NFL week is complete (after Monday Night Football).
    
    Args:
        week: NFL week number
        year: Year
        
    Returns:
        True if the week is complete, False otherwise
    """
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        pst_tz = ZoneInfo("America/Los_Angeles")
        current_time = datetime.now(pst_tz)
        
        # Calculate when the week ends (Tuesday 6 AM after Monday Night Football)
        week_1_start = datetime(year, 9, 5, tzinfo=pst_tz)
        days_to_thursday = (3 - week_1_start.weekday()) % 7
        if days_to_thursday == 0 and week_1_start.weekday() != 3:
            days_to_thursday = 7
            
        first_thursday = week_1_start + timedelta(days=days_to_thursday)
        target_week_start = first_thursday + timedelta(weeks=week-1)
        week_end = target_week_start + timedelta(days=5, hours=6)  # Tuesday 6 AM
        
        return current_time > week_end
        
    except Exception as e:
        return False


def fetch_scores_and_store(days_from: int = 1) -> str:
    """Fetch NFL scores from The Odds API and store in Firestore.
    
    Args:
        days_from: Number of days from now to get scores (default: 1)
        
    Returns:
        Document ID of the stored scores snapshot, or empty string if failed
    """
    try:
        # Fetch scores using the existing API wrapper
        scores_data, doc_id = fetch_scores_from_api(days_from=days_from)
        
        if not scores_data or isinstance(scores_data, dict) and scores_data.get("mock_data"):
            st.warning("No real scores data available (using mock data or API unavailable)")
            return ""
        
        # Process and store scores in the scores collection
        db = get_firestore_client()
        
        # Create scores snapshot
        scores_games = []
        
        for game in scores_data:
            # Only process completed games with scores
            if not game.get('completed', False) or not game.get('scores'):
                continue
                
            # Extract team scores
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            home_score = 0
            away_score = 0
            
            for score in game.get('scores', []):
                team_name = score.get('name', '')
                team_score = int(score.get('score', 0))
                
                if team_name == home_team:
                    home_score = team_score
                elif team_name == away_team:
                    away_score = team_score
            
            total_points = home_score + away_score
            
            scores_games.append({
                'SNAPSHOT_ID': doc_id,  # Link to raw API call
                'SNAPSHOT_CREATION_DATE': datetime.now(),
                'GAME_ID': game.get('id', ''),
                'HOME_TEAM': home_team,
                'HOME_TEAM_SCORE': home_score,
                'AWAY_TEAM': away_team,
                'AWAY_TEAM_SCORE': away_score,
                'TOTAL_GAME_POINTS': total_points
            })
        
        if not scores_games:
            st.info("No completed games with scores found")
            return ""
        
        # Store scores snapshot
        scores_snapshot = {
            'SNAPSHOT_ID': doc_id,
            'SNAPSHOT_CREATION_DATE': datetime.now(),
            'TOTAL_COMPLETED_GAMES': len(scores_games),
            'SCORES': scores_games
        }
        
        scores_doc_ref = db.collection('game_scores').add(scores_snapshot)
        scores_doc_id = scores_doc_ref[1].id
        
        st.success(f"✅ Stored {len(scores_games)} completed games with scores")
        
        return scores_doc_id
        
    except Exception as e:
        st.error(f"Failed to fetch and store scores: {str(e)}")
        return ""


def get_game_scores(limit: int = 10) -> list:
    """Retrieve game scores from Firestore.
    
    Args:
        limit: Maximum number of score snapshots to return
        
    Returns:
        List of game score documents
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection('game_scores')
        
        # Build query
        query = collection_ref.order_by('SNAPSHOT_CREATION_DATE', direction='DESCENDING').limit(limit)
        
        # Execute query
        docs = query.stream()
        
        results = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['document_id'] = doc.id
            # Convert timestamp to string for JSON serialization
            if 'SNAPSHOT_CREATION_DATE' in doc_data:
                doc_data['SNAPSHOT_CREATION_DATE'] = doc_data['SNAPSHOT_CREATION_DATE'].isoformat()
            results.append(doc_data)
        
        return results
        
    except Exception as e:
        st.error(f"Failed to retrieve game scores: {str(e)}")
        return []


def get_scores_for_games(game_ids: list) -> dict:
    """Get scores for specific games by their IDs.
    
    Args:
        game_ids: List of game IDs to get scores for
        
    Returns:
        Dictionary mapping game_id to score data
    """
    try:
        if not game_ids:
            return {}
        
        # Get recent scores
        scores_snapshots = get_game_scores(limit=50)
        game_scores = {}
        
        for snapshot in scores_snapshots:
            for score_game in snapshot.get('SCORES', []):
                game_id = score_game.get('GAME_ID')
                if game_id in game_ids and game_id not in game_scores:
                    game_scores[game_id] = {
                        'home_team': score_game.get('HOME_TEAM', ''),
                        'away_team': score_game.get('AWAY_TEAM', ''),
                        'home_score': score_game.get('HOME_TEAM_SCORE', 0),
                        'away_score': score_game.get('AWAY_TEAM_SCORE', 0),
                        'total_points': score_game.get('TOTAL_GAME_POINTS', 0),
                        'completed': True
                    }
        
        return game_scores
        
    except Exception as e:
        st.error(f"Failed to get scores for games: {str(e)}")
        return {}


def get_api_key():
    """Get The Odds API key from secrets."""
    try:
        return st.secrets["api_keys"]["the_odds_api"]
    except Exception:
        return None


def get_cache_file_path():
    """Get the path to the odds cache file."""
    return os.path.join("data", "odds_cache.csv")


def get_current_week_year():
    """Get current week and year for caching."""
    # Import here to avoid circular imports
    from utils.storage import get_current_week
    return get_current_week()


# Odds API Endpoint Wrappers
def fetch_sports_from_api() -> tuple[dict, str]:
    """Fetch available sports from The Odds API.
    
    Returns:
        Tuple of (sports_data, document_id)
    """
    params = {}
    return make_odds_api_request("sports", params)


def fetch_odds_from_api(sport: str = "americanfootball_nfl", 
                       regions: str = "us", 
                       markets: str = "h2h,spreads,totals",
                       odds_format: str = "american",
                       date_format: str = "iso") -> tuple[dict, str]:
    """Fetch odds for a specific sport from The Odds API.
    
    Args:
        sport: Sport key (default: americanfootball_nfl)
        regions: Regions to get odds for (default: us)
        markets: Markets to include (default: h2h,spreads,totals)
        odds_format: Format for odds (default: american)
        date_format: Format for dates (default: iso)
        
    Returns:
        Tuple of (odds_data, document_id)
    """
    params = {
        'regions': regions,
        'markets': markets,
        'oddsFormat': odds_format,
        'dateFormat': date_format
    }
    endpoint = f"sports/{sport}/odds"
    return make_odds_api_request(endpoint, params)


def fetch_events_from_api(sport: str = "americanfootball_nfl",
                         date_format: str = "iso") -> tuple[dict, str]:
    """Fetch events for a specific sport from The Odds API.
    
    Args:
        sport: Sport key (default: americanfootball_nfl)
        date_format: Format for dates (default: iso)
        
    Returns:
        Tuple of (events_data, document_id)
    """
    params = {
        'dateFormat': date_format
    }
    endpoint = f"sports/{sport}/events"
    return make_odds_api_request(endpoint, params)


def fetch_scores_from_api(sport: str = "americanfootball_nfl",
                         days_from: int = 3,
                         date_format: str = "iso") -> tuple[dict, str]:
    """Fetch scores for a specific sport from The Odds API.
    
    Args:
        sport: Sport key (default: americanfootball_nfl)
        days_from: Number of days from now to get scores (default: 3)
        date_format: Format for dates (default: iso)
        
    Returns:
        Tuple of (scores_data, document_id)
    """
    params = {
        'daysFrom': days_from,
        'dateFormat': date_format
    }
    endpoint = f"sports/{sport}/scores"
    return make_odds_api_request(endpoint, params)


def fetch_event_odds_from_api(sport: str, event_id: str,
                             regions: str = "us",
                             markets: str = "h2h,spreads,totals",
                             odds_format: str = "american",
                             date_format: str = "iso") -> tuple[dict, str]:
    """Fetch odds for a specific event from The Odds API.
    
    Args:
        sport: Sport key
        event_id: Event ID
        regions: Regions to get odds for (default: us)
        markets: Markets to include (default: h2h,spreads,totals)
        odds_format: Format for odds (default: american)
        date_format: Format for dates (default: iso)
        
    Returns:
        Tuple of (event_odds_data, document_id)
    """
    params = {
        'regions': regions,
        'markets': markets,
        'oddsFormat': odds_format,
        'dateFormat': date_format
    }
    endpoint = f"sports/{sport}/events/{event_id}/odds"
    return make_odds_api_request(endpoint, params)


def fetch_event_markets_from_api(sport: str, event_id: str,
                                regions: str = "us",
                                odds_format: str = "american",
                                date_format: str = "iso") -> tuple[dict, str]:
    """Fetch available markets for a specific event from The Odds API.
    
    Args:
        sport: Sport key
        event_id: Event ID
        regions: Regions to get markets for (default: us)
        odds_format: Format for odds (default: american)
        date_format: Format for dates (default: iso)
        
    Returns:
        Tuple of (markets_data, document_id)
    """
    params = {
        'regions': regions,
        'oddsFormat': odds_format,
        'dateFormat': date_format
    }
    endpoint = f"sports/{sport}/events/{event_id}/markets"
    return make_odds_api_request(endpoint, params)


def fetch_participants_from_api(sport: str, event_id: str) -> tuple[dict, str]:
    """Fetch participants for a specific event from The Odds API.
    
    Args:
        sport: Sport key
        event_id: Event ID
        
    Returns:
        Tuple of (participants_data, document_id)
    """
    params = {}
    endpoint = f"sports/{sport}/events/{event_id}/participants"
    return make_odds_api_request(endpoint, params)


def get_current_week_date_range():
    """Get the date range for the current NFL week (Thursday to Monday).
    
    For pick'em purposes:
    - If it's Wednesday or earlier, look ahead to the upcoming Thursday
    - If it's Thursday or later, use the current week's Thursday
    """
    pst_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pst_tz)
    
    # Find the next Thursday (or current Thursday if today is Thursday)
    current_weekday = today.weekday()  # Monday=0, Tuesday=1, ..., Sunday=6
    thursday_weekday = 3  # Thursday=3
    
    if current_weekday <= 2:  # Monday, Tuesday, or Wednesday
        # Look ahead to the upcoming Thursday
        days_to_add = thursday_weekday - current_weekday
        week_start = today + timedelta(days=days_to_add)
    elif current_weekday == thursday_weekday:  # Thursday
        # Use today as the start
        week_start = today
    else:  # Friday, Saturday, or Sunday
        # Go back to this week's Thursday
        days_to_subtract = current_weekday - thursday_weekday
        week_start = today - timedelta(days=days_to_subtract)
    
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Week ends on the following Tuesday at 6 AM (to capture Monday night games)
    week_end = week_start + timedelta(days=5, hours=6)  # Tuesday 6 AM
    
    return week_start, week_end


def filter_games_for_current_week(odds_data):
    """Filter odds data to only include games for the current NFL week."""
    week_start, week_end = get_current_week_date_range()
    
    filtered_games = []
    
    for game in odds_data:
        commence_time_str = game.get("commence_time", "")
        if not commence_time_str:
            continue
            
        try:
            # Parse the ISO datetime from the API (UTC)
            game_time_utc = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
            # Convert to PST/PDT for comparison
            pst_tz = ZoneInfo("America/Los_Angeles")
            game_time_local = game_time_utc.astimezone(pst_tz)
            
            # Check if game falls within current week range
            if week_start <= game_time_local <= week_end:
                filtered_games.append(game)
                
        except Exception as e:
            # If we can't parse the time, skip this game
            continue
    
    return filtered_games


def load_cached_odds(week, year):
    """Load cached odds for a specific week and year."""
    cache_file = get_cache_file_path()
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        cache_df = pd.read_csv(cache_file)
        
        # Find cached data for this week/year
        cached_row = cache_df[(cache_df['week'] == week) & (cache_df['year'] == year)]
        
        if len(cached_row) > 0:
            odds_json = cached_row.iloc[0]['odds_data']
            cache_date = cached_row.iloc[0]['cache_date']
            
            # Parse the cached JSON data
            odds_data = json.loads(odds_json)
            
            # Check if cache is still fresh (within 24 hours)
            cache_datetime = datetime.fromisoformat(cache_date)
            pst_tz = ZoneInfo("America/Los_Angeles")
            current_time = datetime.now(pst_tz)
            # Make cache_datetime timezone-aware if it isn't already
            if cache_datetime.tzinfo is None:
                cache_datetime = cache_datetime.replace(tzinfo=pst_tz)
            if current_time - cache_datetime < timedelta(hours=24):
                return odds_data
            else:
                return None
                
    except Exception as e:
        return None
    
    return None


def save_odds_to_cache(week, year, odds_data):
    """Save odds data to cache."""
    cache_file = get_cache_file_path()
    
    try:
        # Load existing cache or create new
        if os.path.exists(cache_file):
            cache_df = pd.read_csv(cache_file)
        else:
            cache_df = pd.DataFrame(columns=['week', 'year', 'cache_date', 'odds_data'])
        
        # Remove existing cache for this week/year
        cache_df = cache_df[~((cache_df['week'] == week) & (cache_df['year'] == year))]
        
        # Add new cache entry
        pst_tz = ZoneInfo("America/Los_Angeles")
        new_cache = pd.DataFrame([{
            'week': week,
            'year': year,
            'cache_date': datetime.now(pst_tz).isoformat(),
            'odds_data': json.dumps(odds_data)
        }])
        
        cache_df = pd.concat([cache_df, new_cache], ignore_index=True)
        cache_df.to_csv(cache_file, index=False)
        
    except Exception as e:
        pass  # Silent error handling for caching


def fetch_nfl_odds(force_refresh=False):
    """Fetch NFL odds from The Odds API or cache."""
    current_week, current_year = get_current_week_year()
    
    # Check cache first unless force refresh is requested
    if not force_refresh:
        cached_odds = load_cached_odds(current_week, current_year)
        if cached_odds is not None:
            return cached_odds
    
    # If no cache or force refresh, fetch from API using new raw storage system
    try:
        # Use the new API wrapper that stores raw data
        odds_data, doc_id = fetch_odds_from_api()
        
        # If we got mock data, handle it differently
        if isinstance(odds_data, dict) and odds_data.get("mock_data"):
            mock_data = get_mock_odds()
            filtered_mock = filter_games_for_current_week(mock_data)
            save_odds_to_cache(current_week, current_year, filtered_mock)
            return filtered_mock
        
        # Filter to only include current week's games
        filtered_odds = filter_games_for_current_week(odds_data)
        
        # Save filtered data to cache
        save_odds_to_cache(current_week, current_year, filtered_odds)
        
        # Log the successful API call with raw storage
        if doc_id:
            st.info(f"✅ API call stored with ID: {doc_id}")
        
        return filtered_odds
        
    except Exception as e:
        # Fallback to mock data if API fails
        mock_data = get_mock_odds()
        filtered_mock = filter_games_for_current_week(mock_data)
        save_odds_to_cache(current_week, current_year, filtered_mock)
        return filtered_mock


def get_mock_odds():
    """Return mock NFL odds data for testing."""
    # Generate dates for the current week (Thursday to Monday) in PST/PDT
    pst_tz = ZoneInfo("America/Los_Angeles")
    today = datetime.now(pst_tz)
    days_since_thursday = (today.weekday() - 3) % 7
    if days_since_thursday == 0:
        week_start = today
    else:
        week_start = today - timedelta(days=days_since_thursday)
    
    # Create mock games for Thursday, Sunday, and Monday (convert to UTC for API consistency)
    utc_tz = ZoneInfo("UTC")
    thursday_game = week_start.replace(hour=20, minute=15).astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    sunday_game1 = (week_start + timedelta(days=3)).replace(hour=13, minute=0).astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    sunday_game2 = (week_start + timedelta(days=3)).replace(hour=16, minute=25).astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    monday_game = (week_start + timedelta(days=4)).replace(hour=20, minute=15).astimezone(utc_tz).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return [
        {
            "id": "game1",
            "sport_title": "NFL",
            "commence_time": thursday_game,
            "home_team": "San Francisco 49ers",
            "away_team": "Green Bay Packers",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "San Francisco 49ers", "point": -6.5},
                                {"name": "Green Bay Packers", "point": 6.5}
                            ]
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 47.5},
                                {"name": "Under", "point": 47.5}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": "game2",
            "sport_title": "NFL",
            "commence_time": sunday_game1,
            "home_team": "Kansas City Chiefs",
            "away_team": "Miami Dolphins",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Kansas City Chiefs", "point": -3.0},
                                {"name": "Miami Dolphins", "point": 3.0}
                            ]
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 51.5},
                                {"name": "Under", "point": 51.5}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": "game3",
            "sport_title": "NFL",
            "commence_time": sunday_game2,
            "home_team": "Buffalo Bills",
            "away_team": "Pittsburgh Steelers",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Buffalo Bills", "point": -7.0},
                                {"name": "Pittsburgh Steelers", "point": 7.0}
                            ]
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 43.5},
                                {"name": "Under", "point": 43.5}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": "game4",
            "sport_title": "NFL",
            "commence_time": monday_game,
            "home_team": "Dallas Cowboys",
            "away_team": "Tampa Bay Buccaneers",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Dallas Cowboys", "point": -2.5},
                                {"name": "Tampa Bay Buccaneers", "point": 2.5}
                            ]
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 49.0},
                                {"name": "Under", "point": 49.0}
                            ]
                        }
                    ]
                }
            ]
        }
    ]


def format_odds_for_picks(odds_data):
    """Format odds data for pick selection interface."""
    formatted_games = []
    
    for game in odds_data:
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        
        # Get the first bookmaker's odds (we'll use DraftKings if available)
        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            continue
            
        markets = bookmakers[0].get("markets", [])
        
        # Extract spread and total information
        spread_info = None
        total_info = None
        
        for market in markets:
            if market["key"] == "spreads":
                spread_info = market["outcomes"]
            elif market["key"] == "totals":
                total_info = market["outcomes"]
        
        if spread_info and total_info:
            # Determine favorite and underdog
            home_spread = next((o["point"] for o in spread_info if o["name"] == home_team), 0)
            away_spread = next((o["point"] for o in spread_info if o["name"] == away_team), 0)
            
            if home_spread < 0:  # Home team is favorite
                favorite = f"{home_team} ({home_spread})"
                underdog = f"{away_team} (+{abs(away_spread)})"
            else:  # Away team is favorite
                favorite = f"{away_team} ({away_spread})"
                underdog = f"{home_team} (+{abs(home_spread)})"
            
            # Get total
            total_line = total_info[0]["point"]
            over = f"{away_team} vs {home_team} o{total_line}"
            under = f"{away_team} vs {home_team} u{total_line}"
            
            formatted_games.append({
                "game_id": game["id"],
                "matchup": f"{away_team} @ {home_team}",
                "commence_time": game.get("commence_time", ""),
                "favorite": favorite,
                "underdog": underdog,
                "over": over,
                "under": under,
                "spread_line": abs(home_spread) if home_spread < 0 else abs(away_spread),
                "total_line": total_line
            })
    
    return formatted_games


def get_picks_options(force_refresh=False):
    """Get formatted picks options for the current week."""
    odds_data = fetch_nfl_odds(force_refresh=force_refresh)
    formatted_games = format_odds_for_picks(odds_data)
    
    if not formatted_games:
        return {
            "favorites": ["No games available"],
            "underdogs": ["No games available"],
            "overs": ["No games available"],
            "unders": ["No games available"]
        }
    
    return {
        "favorites": [game["favorite"] for game in formatted_games],
        "underdogs": [game["underdog"] for game in formatted_games],
        "overs": [game["over"] for game in formatted_games],
        "unders": [game["under"] for game in formatted_games]
    }


def apply_line_helper(line, adjustment):
    """Apply line helper powerup adjustment to over/under line."""
    return line + adjustment


def get_formatted_games_display(force_refresh=False):
    """Get formatted games for display section (e.g., 'Niners (+5.5) @ Titans (-5.5) o/u53.5')."""
    odds_data = fetch_nfl_odds(force_refresh=force_refresh)
    formatted_games = format_odds_for_picks(odds_data)
    
    if not formatted_games:
        return []
    
    display_games = []
    
    for game in formatted_games:
        # Parse team info from formatted game data
        matchup = game["matchup"]  # "Away Team @ Home Team"
        away_team, home_team = matchup.split(" @ ")
        
        # Get spread info from favorite/underdog
        favorite_info = game["favorite"]  # "Team Name (-X.X)"
        underdog_info = game["underdog"]  # "Team Name (+X.X)"
        
        # Extract spread values
        fav_spread = favorite_info.split("(")[1].replace(")", "")  # "-X.X"
        dog_spread = underdog_info.split("(")[1].replace(")", "")  # "+X.X"
        
        # Determine which team is home/away favorite/underdog
        if favorite_info.startswith(home_team.split()[0]):  # Home team is favorite
            home_line = fav_spread
            away_line = dog_spread
        else:  # Away team is favorite
            away_line = fav_spread
            home_line = dog_spread
        
        # Get total line
        total_line = game["total_line"]
        
        # Create shortened team names (first word usually)
        away_short = get_team_short_name(away_team)
        home_short = get_team_short_name(home_team)
        
        # Format as requested: "Niners (+5.5) @ Titans (-5.5) o/u53.5"
        formatted_display = f"{away_team} @ {home_team} ({home_line})"
        
        display_games.append({
            "formatted_text": formatted_display,
            "away_team": away_team,
            "home_team": home_team,
            "away_short": away_short,
            "home_short": home_short,
            "commence_time": game["commence_time"],
            "total_line": total_line
        })
    
    return display_games


def get_team_short_name(team_name):
    """Get a shortened version of team name for display."""
    # Common NFL team short names mapping
    short_names = {
        "San Francisco 49ers": "Niners",
        "Green Bay Packers": "Packers", 
        "Kansas City Chiefs": "Chiefs",
        "Miami Dolphins": "Dolphins",
        "Buffalo Bills": "Bills",
        "Pittsburgh Steelers": "Steelers",
        "Dallas Cowboys": "Cowboys",
        "Tampa Bay Buccaneers": "Bucs",
        "New England Patriots": "Patriots",
        "New York Giants": "Giants",
        "New York Jets": "Jets",
        "Philadelphia Eagles": "Eagles",
        "Washington Commanders": "Commanders",
        "Chicago Bears": "Bears",
        "Detroit Lions": "Lions",
        "Minnesota Vikings": "Vikings",
        "Atlanta Falcons": "Falcons",
        "Carolina Panthers": "Panthers",
        "New Orleans Saints": "Saints",
        "Tampa Bay Buccaneers": "Bucs",
        "Arizona Cardinals": "Cardinals",
        "Los Angeles Rams": "Rams",
        "San Francisco 49ers": "Niners",
        "Seattle Seahawks": "Seahawks",
        "Denver Broncos": "Broncos",
        "Las Vegas Raiders": "Raiders",
        "Los Angeles Chargers": "Chargers",
        "Baltimore Ravens": "Ravens",
        "Cincinnati Bengals": "Bengals",
        "Cleveland Browns": "Browns",
        "Houston Texans": "Texans",
        "Indianapolis Colts": "Colts",
        "Jacksonville Jaguars": "Jaguars",
        "Tennessee Titans": "Titans"
    }
    
    return short_names.get(team_name, team_name.split()[-1])  # Default to last word (usually team name)
