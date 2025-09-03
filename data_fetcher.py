import requests
import sqlite3
import json
from datetime import datetime, timedelta
import time

class NFLDataFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        
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
            response = requests.get(url, params=params)
            response.raise_for_status()
            return self._parse_odds_api_response(response.json())
        except Exception as e:
            print(f"Error fetching from Odds API: {e}")
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
            response = requests.get(url, params={'limit': 100})
            response.raise_for_status()
            data = response.json()
            
            games = []
            for item in data.get('items', []):
                # Get game details
                game_response = requests.get(item['$ref'])
                game_data = game_response.json()
                
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
                        
                        game_date = datetime.fromisoformat(game_data['date'].replace('Z', '+00:00'))
                        
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
                
            return games
            
        except Exception as e:
            print(f"Error fetching from ESPN: {e}")
            return []
    
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
    
    def _get_current_nfl_week(self):
        """Calculate current NFL week based on date"""
        # NFL season typically starts first Thursday in September
        # This is a simplified calculation - you may want to make this more accurate
        now = datetime.now()
        if now.month < 9:
            return 1
        elif now.month > 12:
            return 18  # Playoffs
        else:
            # Rough calculation based on September start
            start_date = datetime(now.year, 9, 1)
            days_elapsed = (now - start_date).days
            return min(max(1, days_elapsed // 7), 18)

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