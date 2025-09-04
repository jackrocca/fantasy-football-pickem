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
