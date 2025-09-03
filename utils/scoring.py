"""
Scoring logic and powerups for the Fantasy Football Pick'em League.
"""
import pandas as pd
from utils.storage import load_picks, load_results, load_standings, update_standings


def calculate_pick_result(pick_type, pick_value, game_result):
    """Calculate if a specific pick was correct."""
    if pick_type == "favorite":
        # Extract team name and spread from pick_value (e.g., "Chiefs (-3.0)")
        team_name = pick_value.split(" (")[0]
        spread = float(pick_value.split("(")[1].replace(")", "").replace("+", ""))
        
        # Check if this team covered the spread
        home_team = game_result["home_team"]
        away_team = game_result["away_team"]
        home_score = game_result["home_score"]
        away_score = game_result["away_score"]
        
        if team_name == home_team:
            return (home_score + spread) > away_score
        else:
            return (away_score + spread) > home_score
            
    elif pick_type == "underdog":
        # Similar logic but for underdog
        team_name = pick_value.split(" (+")[0]
        spread = float(pick_value.split("(+")[1].replace(")", ""))
        
        home_team = game_result["home_team"]
        away_team = game_result["away_team"]
        home_score = game_result["home_score"]
        away_score = game_result["away_score"]
        
        if team_name == home_team:
            return (home_score + spread) > away_score
        else:
            return (away_score + spread) > home_score
            
    elif pick_type == "over":
        # Extract total from pick_value (e.g., "Chiefs vs Bills o51.5")
        total_line = float(pick_value.split(" o")[1])
        total_points = game_result["home_score"] + game_result["away_score"]
        return total_points > total_line
        
    elif pick_type == "under":
        # Extract total from pick_value (e.g., "Chiefs vs Bills u51.5")
        total_line = float(pick_value.split(" u")[1])
        total_points = game_result["home_score"] + game_result["away_score"]
        return total_points < total_line
    
    return False


def score_weekly_picks(username, week, year):
    """Score a user's picks for a specific week."""
    picks_df = load_picks()
    results_df = load_results()
    
    # Get user's picks for the week
    user_picks = picks_df[
        (picks_df['username'] == username) & 
        (picks_df['week'] == week) & 
        (picks_df['year'] == year)
    ]
    
    if len(user_picks) == 0:
        return 0, 0, False  # points, correct_picks, perfect_week
    
    pick_row = user_picks.iloc[0]
    week_results = results_df[(results_df['week'] == week) & (results_df['year'] == year)]
    
    if len(week_results) == 0:
        return 0, 0, False  # No results available yet
    
    correct_picks = 0
    total_picks = 4
    
    # Score each pick type
    pick_types = ['favorite', 'underdog', 'over', 'under']
    
    for pick_type in pick_types:
        pick_value = pick_row[pick_type]
        if pd.isna(pick_value) or pick_value == "":
            continue
            
        # Find matching game result
        # This is simplified - in a real app, you'd need better game matching logic
        for _, game_result in week_results.iterrows():
            try:
                if calculate_pick_result(pick_type, pick_value, game_result):
                    correct_picks += 1
                    break
            except Exception:
                continue  # Skip if can't parse pick
    
    # Calculate points
    points = correct_picks
    perfect_week = correct_picks == total_picks
    
    # Apply powerups
    if pick_row.get('perfect_powerup', False):
        if perfect_week:
            points = 8  # Perfect powerup: 8 points for perfect week
        else:
            points = 0  # Perfect powerup: 0 points if not perfect
    elif perfect_week:
        points = 5  # Regular perfect week bonus
    
    return points, correct_picks, perfect_week


def score_all_users_for_week(week, year):
    """Score all users for a specific week."""
    picks_df = load_picks()
    users = picks_df[
        (picks_df['week'] == week) & 
        (picks_df['year'] == year)
    ]['username'].unique()
    
    week_scores = []
    
    for username in users:
        points, correct_picks, perfect_week = score_weekly_picks(username, week, year)
        
        week_scores.append({
            'username': username,
            'week': week,
            'year': year,
            'points': points,
            'correct_picks': correct_picks,
            'perfect_week': perfect_week
        })
        
        # Update standings
        update_standings(username, year, points, perfect_week)
    
    return week_scores


def get_weekly_scoreboard(week, year):
    """Get formatted weekly scoreboard."""
    week_scores = score_all_users_for_week(week, year)
    
    if not week_scores:
        return pd.DataFrame()
    
    df = pd.DataFrame(week_scores)
    df = df.sort_values(['points', 'correct_picks'], ascending=[False, False])
    df['rank'] = range(1, len(df) + 1)
    
    return df[['rank', 'username', 'points', 'correct_picks', 'perfect_week']]


def get_season_standings(year):
    """Get season-long standings."""
    standings_df = load_standings()
    season_standings = standings_df[standings_df['year'] == year].copy()
    
    if len(season_standings) == 0:
        return pd.DataFrame()
    
    # Sort by total points, then by perfect weeks, then by correct picks
    season_standings = season_standings.sort_values(
        ['total_points', 'perfect_weeks', 'correct_picks'], 
        ascending=[False, False, False]
    )
    
    season_standings['rank'] = range(1, len(season_standings) + 1)
    
    return season_standings[['rank', 'username', 'total_points', 'perfect_weeks', 'correct_picks']]


def get_user_stats(username, year):
    """Get detailed stats for a specific user."""
    standings_df = load_standings()
    picks_df = load_picks()
    
    user_standings = standings_df[
        (standings_df['username'] == username) & 
        (standings_df['year'] == year)
    ]
    
    user_picks = picks_df[
        (picks_df['username'] == username) & 
        (picks_df['year'] == year)
    ]
    
    if len(user_standings) == 0:
        return {
            'total_points': 0,
            'perfect_weeks': 0,
            'weeks_played': 0,
            'powerups_used': 0,
            'average_points': 0.0
        }
    
    stats = user_standings.iloc[0].to_dict()
    stats['weeks_played'] = len(user_picks)
    stats['average_points'] = stats['total_points'] / max(stats['weeks_played'], 1)
    
    return stats


def has_used_powerup(username, year, powerup_type):
    """Check if user has already used a specific powerup this season."""
    picks_df = load_picks()
    user_picks = picks_df[
        (picks_df['username'] == username) & 
        (picks_df['year'] == year)
    ]
    
    if powerup_type == "perfect_powerup":
        return user_picks['perfect_powerup'].any()
    elif powerup_type == "line_helper":
        return user_picks['line_helper'].any()
    
    return False
