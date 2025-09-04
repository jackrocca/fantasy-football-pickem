"""
Data storage utilities for CSV operations.
"""
import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit as st


def get_data_path(filename):
    """Get the full path to a data file."""
    return os.path.join("data", filename)


def ensure_csv_exists(filename, columns):
    """Ensure a CSV file exists with proper columns."""
    filepath = get_data_path(filename)
    if not os.path.exists(filepath):
        df = pd.DataFrame(columns=columns)
        df.to_csv(filepath, index=False)
    return filepath


def load_picks():
    """Load user picks from CSV."""
    filepath = ensure_csv_exists("picks.csv", [
        "username", "week", "year", "favorite", "underdog", "over", "under",
        "super_spread", "total_helper", "total_helper_adjustment", "perfect_prediction", 
        "submission_time", "timestamp"
    ])
    try:
        return pd.read_csv(filepath)
    except Exception as e:
        st.error(f"Error loading picks: {e}")
        return pd.DataFrame()


def save_picks(username, week, year, favorite, underdog, over, under, 
               super_spread=False, total_helper=False, total_helper_adjustment=0, perfect_prediction=False):
    """Save user picks to CSV."""
    filepath = get_data_path("picks.csv")
    df = load_picks()
    
    # Remove existing picks for this user/week/year
    df = df[~((df['username'] == username) & (df['week'] == week) & (df['year'] == year))]
    
    # Determine submission time for deadline checking
    current_time = datetime.now()
    submission_time = current_time.isoformat()
    
    # Add new pick
    new_pick = pd.DataFrame([{
        'username': username,
        'week': week,
        'year': year,
        'favorite': favorite,
        'underdog': underdog,
        'over': over,
        'under': under,
        'super_spread': super_spread,
        'total_helper': total_helper,
        'total_helper_adjustment': total_helper_adjustment,
        'perfect_prediction': perfect_prediction,
        'submission_time': submission_time,
        'timestamp': submission_time
    }])
    
    df = pd.concat([df, new_pick], ignore_index=True)
    df.to_csv(filepath, index=False)


def load_results():
    """Load game results from CSV."""
    filepath = ensure_csv_exists("results.csv", [
        "week", "year", "game_id", "home_team", "away_team", "home_score", 
        "away_score", "spread_favorite", "spread_line", "total_points", "over_under_line"
    ])
    try:
        return pd.read_csv(filepath)
    except Exception as e:
        st.error(f"Error loading results: {e}")
        return pd.DataFrame()


def save_results(results_data):
    """Save game results to CSV."""
    filepath = get_data_path("results.csv")
    df = pd.DataFrame(results_data)
    df.to_csv(filepath, index=False)


def load_standings():
    """Load season standings from CSV."""
    filepath = ensure_csv_exists("standings.csv", [
        "username", "year", "total_points", "correct_picks", "perfect_weeks", 
        "powerups_used", "current_streak", "best_streak"
    ])
    try:
        return pd.read_csv(filepath)
    except Exception as e:
        st.error(f"Error loading standings: {e}")
        return pd.DataFrame()


def update_standings(username, year, points_earned, perfect_week=False):
    """Update user standings."""
    filepath = get_data_path("standings.csv")
    df = load_standings()
    
    # Find or create user record
    user_mask = (df['username'] == username) & (df['year'] == year)
    
    if user_mask.any():
        # Update existing record
        df.loc[user_mask, 'total_points'] += points_earned
        df.loc[user_mask, 'correct_picks'] += points_earned  # Simplified for now
        if perfect_week:
            df.loc[user_mask, 'perfect_weeks'] += 1
    else:
        # Create new record
        new_record = pd.DataFrame([{
            'username': username,
            'year': year,
            'total_points': points_earned,
            'correct_picks': points_earned,  # Simplified for now
            'perfect_weeks': 1 if perfect_week else 0,
            'powerups_used': 0,
            'current_streak': 0,
            'best_streak': 0
        }])
        df = pd.concat([df, new_record], ignore_index=True)
    
    df.to_csv(filepath, index=False)


def get_current_week():
    """Get the current NFL week based on date."""
    # NFL season typically starts first Thursday after Labor Day
    # This is a simplified version - you might want to use a more accurate calculation
    today = datetime.now()
    
    # Assume week 1 starts on September 5th (adjust as needed)
    if today.month < 9:
        return 1, today.year
    elif today.month > 2:
        week = min(((today - datetime(today.year, 9, 5)).days // 7) + 1, 18)
        return max(week, 1), today.year
    else:
        # February/March - previous season
        week = min(((today - datetime(today.year - 1, 9, 5)).days // 7) + 1, 18)
        return max(week, 1), today.year - 1


def is_thursday_or_later():
    """Check if it's Thursday or later (picks should be locked)."""
    return datetime.now().weekday() >= 3  # Thursday = 3


def get_user_picks(username, week, year):
    """Get picks for a specific user, week, and year."""
    df = load_picks()
    user_picks = df[(df['username'] == username) & 
                   (df['week'] == week) & 
                   (df['year'] == year)]
    
    if len(user_picks) > 0:
        return user_picks.iloc[0].to_dict()
    return None


def get_all_users():
    """Get list of all users from secrets."""
    try:
        return list(st.secrets.get("users", {}).keys())
    except Exception:
        return []
