"""
Scoring logic and powerups for the Fantasy Football Pick'em League.
"""
import pandas as pd
from datetime import datetime, timedelta
from utils.storage import load_picks, load_results, load_standings, update_standings


def calculate_pick_result(pick_type, pick_value, game_result, total_helper_adjustment=0):
    """Calculate pick result: 'win', 'push', or 'loss'."""
    try:
        if pick_type in ["favorite", "underdog"]:
            # Extract team name and spread from pick_value (e.g., "Chiefs (-3.0)" or "Bills (+7.0)")
            if " (" not in pick_value:
                return 'loss'
            
            team_name = pick_value.split(" (")[0]
            spread_str = pick_value.split("(")[1].replace(")", "")
            spread = float(spread_str.replace("+", ""))
            
            # Check if this team covered the spread
            home_team = game_result["home_team"]
            away_team = game_result["away_team"]
            home_score = game_result["home_score"]
            away_score = game_result["away_score"]
            
            if team_name == home_team:
                adjusted_home_score = home_score + spread
                if adjusted_home_score > away_score:
                    return 'win'
                elif adjusted_home_score == away_score:
                    return 'push'
                else:
                    return 'loss'
            else:  # Away team
                adjusted_away_score = away_score + spread
                if adjusted_away_score > home_score:
                    return 'win'
                elif adjusted_away_score == home_score:
                    return 'push'
                else:
                    return 'loss'
                
        elif pick_type == "over":
            # Extract total from pick_value (e.g., "Chiefs vs Bills o51.5")
            if " o" not in pick_value:
                return 'loss'
            total_line = float(pick_value.split(" o")[1])
            # Apply total helper adjustment if applicable
            adjusted_line = total_line + total_helper_adjustment
            total_points = game_result["home_score"] + game_result["away_score"]
            
            if total_points > adjusted_line:
                return 'win'
            elif total_points == adjusted_line:
                return 'push'
            else:
                return 'loss'
                
        elif pick_type == "under":
            # Extract total from pick_value (e.g., "Chiefs vs Bills u51.5")
            if " u" not in pick_value:
                return 'loss'
            total_line = float(pick_value.split(" u")[1])
            # Apply total helper adjustment if applicable
            adjusted_line = total_line + total_helper_adjustment
            total_points = game_result["home_score"] + game_result["away_score"]
            
            if total_points < adjusted_line:
                return 'win'
            elif total_points == adjusted_line:
                return 'push'
            else:
                return 'loss'
        
        return 'loss'
    except Exception:
        return 'loss'


def matches_game(pick_type, pick_value, game_result):
    """Check if a pick matches a specific game result."""
    try:
        home_team = game_result["home_team"]
        away_team = game_result["away_team"]
        
        if pick_type in ["favorite", "underdog"]:
            # Extract team name from spread pick
            team_name = pick_value.split(" (")[0]
            return team_name == home_team or team_name == away_team
        
        elif pick_type in ["over", "under"]:
            # Check if the teams in the total pick match the game
            if " vs " in pick_value:
                teams_part = pick_value.split(" o")[0].split(" u")[0]
                teams = teams_part.split(" vs ")
                if len(teams) == 2:
                    team1, team2 = teams[0].strip(), teams[1].strip()
                    return ((team1 == home_team and team2 == away_team) or 
                           (team1 == away_team and team2 == home_team))
        
        return False
    except Exception:
        return False


def covered_double_spread(favorite_pick, week_results):
    """Check if a favorite covered double the original spread."""
    try:
        if not favorite_pick or " (" not in favorite_pick:
            return False
        
        team_name = favorite_pick.split(" (")[0]
        spread_str = favorite_pick.split("(")[1].replace(")", "")
        original_spread = float(spread_str.replace("+", ""))
        double_spread = original_spread * 2  # e.g., -5 becomes -10
        
        # Find the matching game
        for _, game_result in week_results.iterrows():
            home_team = game_result["home_team"]
            away_team = game_result["away_team"]
            home_score = game_result["home_score"]
            away_score = game_result["away_score"]
            
            if team_name in [home_team, away_team]:
                if team_name == home_team:
                    margin = home_score - away_score
                else:
                    margin = away_score - home_score
                
                # Check if they covered the double spread
                return margin >= abs(double_spread)
        
        return False
    except Exception:
        return False


def is_late_submission(pick_row, week, year):
    """Check if a submission was made after the Thursday deadline."""
    try:
        if 'submission_time' not in pick_row or pd.isna(pick_row['submission_time']):
            return False
        
        submission_time = datetime.fromisoformat(pick_row['submission_time'])
        
        # Find Thursday of that week - this is simplified, in production you'd want
        # to get the actual TNF kickoff time for that specific week
        # For now, assume Thursday 8:15 PM ET is the deadline
        
        # Get the first day of the week based on week number
        # This is a simplification - you'd want more precise date calculation
        base_date = datetime(year, 9, 5)  # Rough start of NFL season
        week_start = base_date + timedelta(weeks=week-1)
        
        # Find Thursday of that week
        days_to_thursday = (3 - week_start.weekday()) % 7
        thursday = week_start + timedelta(days=days_to_thursday)
        deadline = thursday.replace(hour=20, minute=15)  # 8:15 PM TNF
        
        return submission_time > deadline
    except Exception:
        return False


def score_weekly_picks(username, week, year):
    """Score a user's picks for a specific week with new rules."""
    picks_df = load_picks()
    results_df = load_results()
    
    # Get user's picks for the week
    user_picks = picks_df[
        (picks_df['username'] == username) & 
        (picks_df['week'] == week) & 
        (picks_df['year'] == year)
    ]
    
    if len(user_picks) == 0:
        return 0, 0, False, {}  # points, wins, perfect_week, details
    
    pick_row = user_picks.iloc[0]
    week_results = results_df[(results_df['week'] == week) & (results_df['year'] == year)]
    
    if len(week_results) == 0:
        return 0, 0, False, {}  # No results available yet
    
    # Score each pick type
    pick_types = ['favorite', 'underdog', 'over', 'under']
    pick_results = {}
    points = 0
    wins = 0
    
    # Get total helper adjustment if applicable
    total_helper_adjustment = 0
    if pick_row.get('total_helper', False):
        total_helper_adjustment = pick_row.get('total_helper_adjustment', 0)
    
    # Score regular picks first
    for pick_type in pick_types:
        pick_value = pick_row.get(pick_type)
        if pd.isna(pick_value) or pick_value == "":
            continue
            
        # Find matching game result
        result = 'loss'  # Default
        for _, game_result in week_results.iterrows():
            # Simple game matching - in production, you'd want more robust matching
            try:
                # Check if this pick matches this game
                if matches_game(pick_type, pick_value, game_result):
                    adjustment = total_helper_adjustment if pick_type in ['over', 'under'] else 0
                    result = calculate_pick_result(pick_type, pick_value, game_result, adjustment)
                    break
            except Exception:
                continue
        
        pick_results[pick_type] = result
        
        # Add points based on result
        if result == 'win':
            points += 1
            wins += 1
        elif result == 'push':
            points += 0.5
    
    # Check for perfect week (4 wins)
    perfect_week = wins == 4
    
    # Apply perfect week bonus (unless using scoring specials)
    if perfect_week and not any([
        pick_row.get('super_spread', False),
        pick_row.get('perfect_prediction', False)
    ]):
        points += 1  # Perfect week bonus: 5 total points
    
    # Check if this is a late submission (forfeits scoring specials)
    is_late = is_late_submission(pick_row, week, year)
    
    # Handle Super Spread special (not available for late submissions)
    if pick_row.get('super_spread', False) and not is_late:
        favorite_result = pick_results.get('favorite', 'loss')
        if favorite_result == 'win':
            # Check if it covered double the spread
            if covered_double_spread(pick_row.get('favorite'), week_results):
                points = points - 1 + 2.5  # Replace the 1 point with 2.5
        elif favorite_result == 'push':
            points = points - 0.5 + 1  # Replace 0.5 with 1 point
        elif favorite_result == 'loss':
            points = points - 1 + 0  # Replace 1 point with 0
    
    # Handle Perfect Prediction special (not available for late submissions)
    if pick_row.get('perfect_prediction', False) and not is_late:
        if perfect_week:
            points = 8  # Perfect prediction: 8 points for perfect week
        else:
            # Keep normal scoring
            pass
    
    # Check for late submission penalty
    if is_late_submission(pick_row, week, year):
        points = max(0, points - 1)  # Deduct 1 point, minimum 0
    
    return points, wins, perfect_week, pick_results


def score_all_users_for_week(week, year):
    """Score all users for a specific week."""
    picks_df = load_picks()
    users = picks_df[
        (picks_df['week'] == week) & 
        (picks_df['year'] == year)
    ]['username'].unique()
    
    week_scores = []
    
    for username in users:
        points, wins, perfect_week, pick_results = score_weekly_picks(username, week, year)
        
        week_scores.append({
            'username': username,
            'week': week,
            'year': year,
            'points': points,
            'wins': wins,
            'perfect_week': perfect_week,
            'pick_results': pick_results
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
    df = df.sort_values(['points', 'wins'], ascending=[False, False])
    df['rank'] = range(1, len(df) + 1)
    
    return df[['rank', 'username', 'points', 'wins', 'perfect_week']]


def get_season_standings(year):
    """Get season-long standings."""
    standings_df = load_standings()
    season_standings = standings_df[standings_df['year'] == year].copy()
    
    if len(season_standings) == 0:
        return pd.DataFrame()
    
    # Sort by total points, then by perfect weeks, then by wins
    season_standings = season_standings.sort_values(
        ['total_points', 'perfect_weeks'], 
        ascending=[False, False]
    )
    
    season_standings['rank'] = range(1, len(season_standings) + 1)
    
    return season_standings[['rank', 'username', 'total_points', 'perfect_weeks']]


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
    
    if len(user_picks) == 0:
        return False
    
    if powerup_type == "super_spread":
        return user_picks['super_spread'].fillna(False).any()
    elif powerup_type == "total_helper":
        return user_picks['total_helper'].fillna(False).any()
    elif powerup_type == "perfect_prediction":
        return user_picks['perfect_prediction'].fillna(False).any()
    # Legacy powerups for backward compatibility
    elif powerup_type == "perfect_powerup":
        return user_picks.get('perfect_powerup', pd.Series([False])).fillna(False).any()
    elif powerup_type == "line_helper":
        return user_picks.get('line_helper', pd.Series([False])).fillna(False).any()
    
    return False
