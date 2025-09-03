import requests
import sqlite3
import json
from datetime import datetime, timedelta
import time
import pytz
import logging

class NFLDataFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Fantasy-Pickem-League/1.0'})
        
    def get_nfl_games_and_odds(self):
        """Fetch current week's NFL games and betting lines"""
        if not self.api_key:
            # Fallback to ESPN for game schedule (free)
            return self._get_espn_games()
            
        url = f"{self.base_url}/sports/americanfootball_nfl/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american',
            'bookmakers': 'draftkings,fanduel'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Check API quota
            remaining_requests = response.headers.get('x-requests-remaining')
            if remaining_requests:
                logging.info(f"Odds API requests remaining: {remaining_requests}")
            
            return self._parse_odds_api_response(response.json())
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching from Odds API: {e}")
            return self._get_espn_games()
        except Exception as e:
            logging.error(f"Unexpected error with Odds API: {e}")
            return self._get_espn_games()
    
    def _parse_odds_api_response(self, data):
        """Parse The Odds API response into our database format"""
        games = []
        for game in data:
            home_team = game['home_team']
            away_team = game['away_team']
            commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            
            # Extract betting lines from bookmakers
            spread = None
            total = None
            moneyline_home = None
            moneyline_away = None
            
            if game.get('bookmakers'):
                # Use first available bookmaker (DraftKings or FanDuel)
                bookmaker = game['bookmakers'][0]
                
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                spread = outcome.get('point')
                    elif market['key'] == 'totals':
                        total = market['outcomes'][0].get('point')
                    elif market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                moneyline_home = outcome.get('price')
                            else:
                                moneyline_away = outcome.get('price')
            
            games.append({
                'home_team': home_team,
                'away_team': away_team,
                'game_date': commence_time,
                'spread': spread,
                'total': total,
                'moneyline_home': moneyline_home,
                'moneyline_away': moneyline_away
            })
        
        return games
    
    def _get_espn_games(self):
        """Fallback: Get NFL games from ESPN API (free, but no betting lines)"""
        current_year = datetime.now().year
        url = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{current_year}/types/2/events"
        
        try:
            response = self.session.get(url, params={'limit': 100}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            games = []
            current_week_start = self._get_current_week_start_date()
            week_end = current_week_start + timedelta(days=7)
            
            for item in data.get('items', [])[:20]:  # Limit to avoid rate limits
                try:
                    # Get game details
                    game_response = self.session.get(item['$ref'], timeout=10)
                    game_response.raise_for_status()
                    game_data = game_response.json()
                    
                    # Check if game is in current week
                    game_date = datetime.fromisoformat(game_data['date'].replace('Z', '+00:00'))
                    if not (current_week_start <= game_date <= week_end):
                        continue
                    
                    # Parse game info
                    if len(game_data.get('competitions', [])) > 0:
                        competition = game_data['competitions'][0]
                        competitors = competition.get('competitors', [])
                        
                        if len(competitors) >= 2:
                            home_team = None
                            away_team = None
                            
                            for competitor in competitors:
                                if competitor.get('homeAway') == 'home':
                                    home_team = competitor['team']['abbreviation']
                                else:
                                    away_team = competitor['team']['abbreviation']
                            
                            if home_team and away_team:
                                games.append({
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'game_date': game_date,
                                    'spread': None,  # No betting lines from ESPN
                                    'total': None,
                                    'moneyline_home': None,
                                    'moneyline_away': None
                                })
                    
                    # Rate limiting
                    time.sleep(0.1)
                    
                except Exception as game_error:
                    logging.warning(f"Error processing game {item.get('$ref', 'unknown')}: {game_error}")
                    continue
                
            return games
            
        except Exception as e:
            logging.error(f"Error fetching from ESPN: {e}")
            return self._get_fallback_games()
    
    def store_games_in_db(self, games):
        """Store games and betting lines in SQLite database"""
        conn = sqlite3.connect('pickem_league.db')
        cursor = conn.cursor()
        
        current_week = self._get_current_nfl_week()
        current_season = datetime.now().year
        
        for game in games:
            cursor.execute('''
                INSERT OR REPLACE INTO games 
                (week, season, game_date, home_team, away_team, spread, total, moneyline_home, moneyline_away)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_week,
                current_season,
                game.get('game_date'),
                game.get('home_team'),
                game.get('away_team'),
                game.get('spread'),
                game.get('total'),
                game.get('moneyline_home'),
                game.get('moneyline_away')
            ))
        
        conn.commit()
        conn.close()
        return len(games)
    
    def _get_current_week_start_date(self):
        """Get the start date of the current NFL week (Thursday)"""
        now = datetime.now()
        
        # Find the most recent Thursday
        days_since_thursday = (now.weekday() + 4) % 7  # Thursday is 3, adjust for Monday=0
        thursday = now - timedelta(days=days_since_thursday)
        
        # Set to beginning of day
        return thursday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_current_nfl_week(self):
        """Calculate current NFL week based on date"""
        now = datetime.now()
        
        # NFL season typically starts first Thursday in September
        if now.month < 9:
            return 1
        elif now.month > 12 or (now.month == 1 and now.day < 15):
            return 18  # Playoffs/Super Bowl
        else:
            # Calculate based on first Thursday in September
            year = now.year if now.month >= 9 else now.year - 1
            
            # Find first Thursday in September
            sept_first = datetime(year, 9, 1)
            days_to_thursday = (3 - sept_first.weekday()) % 7
            season_start = sept_first + timedelta(days=days_to_thursday)
            
            if now < season_start:
                return 1
            
            weeks_elapsed = (now - season_start).days // 7
            return min(max(1, weeks_elapsed + 1), 18)
    
    def _get_fallback_games(self):
        """Create fallback sample games for testing"""
        current_week_start = self._get_current_week_start_date()
        
        # Sample games for testing
        sample_games = [
            {
                'home_team': 'KC',
                'away_team': 'BUF', 
                'game_date': current_week_start + timedelta(days=3, hours=20, minutes=20),  # Sunday 8:20 PM
                'spread': -3.5,
                'total': 47.5,
                'moneyline_home': -180,
                'moneyline_away': 150
            },
            {
                'home_team': 'DAL',
                'away_team': 'PHI',
                'game_date': current_week_start + timedelta(days=3, hours=13),  # Sunday 1 PM
                'spread': 2.5,
                'total': 44.0,
                'moneyline_home': 120,
                'moneyline_away': -140
            },
            {
                'home_team': 'SF',
                'away_team': 'SEA',
                'game_date': current_week_start + timedelta(days=3, hours=16, minutes=25),  # Sunday 4:25 PM
                'spread': -6.0,
                'total': 42.5,
                'moneyline_home': -260,
                'moneyline_away': 210
            },
            {
                'home_team': 'GB',
                'away_team': 'MIN',
                'game_date': current_week_start + timedelta(days=4, hours=20, minutes=15),  # Monday 8:15 PM
                'spread': -1.0,
                'total': 48.0,
                'moneyline_home': -110,
                'moneyline_away': -110
            }
        ]
        
        logging.info("Using fallback sample games for testing")
        return sample_games

def update_game_data():
    """Function to update games and betting lines"""
    try:
        import streamlit as st
        api_key = st.secrets.get("odds_api", {}).get("key")
    except:
        api_key = None
        
    fetcher = NFLDataFetcher(api_key)
    games = fetcher.get_nfl_games_and_odds()
    
    if games:
        count = fetcher.store_games_in_db(games)
        return f"Updated {count} games"
    else:
        return "No games found"