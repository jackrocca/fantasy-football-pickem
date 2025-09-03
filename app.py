import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import time
from data_fetcher import NFLDataFetcher

st.set_page_config(
    page_title="Fantasy Football Pick'em League",
    page_icon="🏈",
    layout="wide"
)

def init_database():
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create games table for NFL games and lines
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week INTEGER NOT NULL,
            season INTEGER NOT NULL,
            game_date TIMESTAMP NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            spread REAL,
            total REAL,
            moneyline_home INTEGER,
            moneyline_away INTEGER,
            final_score_home INTEGER,
            final_score_away INTEGER,
            is_final BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create picks table for user selections
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season INTEGER NOT NULL,
            pick_type TEXT NOT NULL, -- 'spread_favorite', 'spread_underdog', 'over', 'under'
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_correct BOOLEAN DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (game_id) REFERENCES games (id),
            UNIQUE(user_id, game_id, pick_type)
        )
    ''')
    
    # Create weekly_scores table for tracking points
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season INTEGER NOT NULL,
            correct_picks INTEGER DEFAULT 0,
            bonus_point BOOLEAN DEFAULT FALSE,
            total_points INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, week, season)
        )
    ''')
    
    conn.commit()
    conn.close()

def check_authentication():
    if not st.user.is_logged_in:
        st.error("Please log in to access the Pick'em League")
        st.login()
        st.stop()
    
    # Get or create user in database
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    user_email = st.user.get('email', 'unknown@email.com')
    username = st.user.get('name', user_email.split('@')[0])
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email)
        VALUES (?, ?)
    ''', (username, user_email))
    
    conn.commit()
    conn.close()
    
    return username

def get_user_id(email):
    """Get user ID from database"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_current_week_games():
    """Get games for the current week"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    # Get current week and season
    current_week = NFLDataFetcher()._get_current_nfl_week()
    current_season = datetime.now().year
    
    cursor.execute('''
        SELECT id, home_team, away_team, game_date, spread, total, moneyline_home, moneyline_away
        FROM games 
        WHERE week = ? AND season = ?
        ORDER BY game_date
    ''', (current_week, current_season))
    
    games = cursor.fetchall()
    conn.close()
    return games

def submit_picks(user_id, picks):
    """Submit user picks to database"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    current_week = NFLDataFetcher()._get_current_nfl_week()
    current_season = datetime.now().year
    
    for pick in picks:
        cursor.execute('''
            INSERT OR REPLACE INTO picks 
            (user_id, game_id, week, season, pick_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, pick['game_id'], current_week, current_season, pick['pick_type']))
    
    conn.commit()
    conn.close()

def get_user_picks(user_id, week, season):
    """Get user's picks for a specific week"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT game_id, pick_type FROM picks
        WHERE user_id = ? AND week = ? AND season = ?
    ''', (user_id, week, season))
    
    picks = cursor.fetchall()
    conn.close()
    return {f"{game_id}_{pick_type}": True for game_id, pick_type in picks}

def is_pick_submission_allowed():
    """Check if picks can still be submitted (before Thursday game time)"""
    # Find the earliest game time this week
    games = get_current_week_games()
    if not games:
        return True
    
    earliest_game = min(games, key=lambda x: x[3])  # game_date is index 3
    game_datetime = datetime.fromisoformat(earliest_game[3])
    
    return datetime.now() < game_datetime

def calculate_pick_results():
    """Calculate results for all picks based on final scores"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    # Get all games with final scores
    cursor.execute('''
        SELECT id, home_team, away_team, spread, total, final_score_home, final_score_away
        FROM games 
        WHERE is_final = TRUE AND final_score_home IS NOT NULL AND final_score_away IS NOT NULL
    ''')
    
    games = cursor.fetchall()
    
    for game in games:
        game_id, home_team, away_team, spread, total, score_home, score_away = game
        
        # Get all picks for this game
        cursor.execute('SELECT id, pick_type FROM picks WHERE game_id = ?', (game_id,))
        picks = cursor.fetchall()
        
        for pick_id, pick_type in picks:
            is_correct = False
            
            if pick_type == 'spread_favorite' and spread is not None:
                if spread < 0:  # Home team is favorite
                    is_correct = (score_home + spread) > score_away
                else:  # Away team is favorite
                    is_correct = (score_away - spread) > score_home
                    
            elif pick_type == 'spread_underdog' and spread is not None:
                if spread < 0:  # Away team is underdog
                    is_correct = (score_away - abs(spread)) > score_home
                else:  # Home team is underdog
                    is_correct = (score_home + spread) > score_away
                    
            elif pick_type == 'over' and total is not None:
                is_correct = (score_home + score_away) > total
                
            elif pick_type == 'under' and total is not None:
                is_correct = (score_home + score_away) < total
            
            # Update pick result
            cursor.execute('UPDATE picks SET is_correct = ? WHERE id = ?', (is_correct, pick_id))
    
    conn.commit()
    conn.close()

def update_weekly_scores():
    """Update weekly scores for all users"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    # Get all user-week combinations with picks
    cursor.execute('''
        SELECT DISTINCT user_id, week, season 
        FROM picks 
        WHERE is_correct IS NOT NULL
    ''')
    
    user_weeks = cursor.fetchall()
    
    for user_id, week, season in user_weeks:
        # Count correct picks for this user-week
        cursor.execute('''
            SELECT COUNT(*) FROM picks 
            WHERE user_id = ? AND week = ? AND season = ? AND is_correct = TRUE
        ''', (user_id, week, season))
        
        correct_picks = cursor.fetchone()[0]
        
        # Check for bonus point (4 correct picks)
        bonus_point = correct_picks == 4
        total_points = correct_picks + (1 if bonus_point else 0)
        
        # Update weekly scores
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_scores 
            (user_id, week, season, correct_picks, bonus_point, total_points)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, week, season, correct_picks, bonus_point, total_points))
    
    conn.commit()
    conn.close()

def get_season_standings():
    """Get season standings for all users"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.username,
            SUM(ws.total_points) as total_points,
            COUNT(ws.week) as weeks_played,
            SUM(CASE WHEN ws.bonus_point THEN 1 ELSE 0 END) as perfect_weeks
        FROM users u
        LEFT JOIN weekly_scores ws ON u.id = ws.user_id
        GROUP BY u.id, u.username
        ORDER BY total_points DESC
    ''')
    
    standings = cursor.fetchall()
    conn.close()
    
    # Add rank
    return [(i+1, username, total_points or 0, weeks_played or 0, perfect_weeks or 0) 
            for i, (username, total_points, weeks_played, perfect_weeks) in enumerate(standings)]

def get_weekly_results(week, season):
    """Get weekly results for all users"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.username,
            ws.correct_picks,
            ws.bonus_point,
            ws.total_points
        FROM users u
        JOIN weekly_scores ws ON u.id = ws.user_id
        WHERE ws.week = ? AND ws.season = ?
        ORDER BY ws.total_points DESC
    ''', (week, season))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_user_picks_for_week(week, season):
    """Get all user picks for a specific week (visible after games start)"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.username,
            g.away_team || ' @ ' || g.home_team as matchup,
            p.pick_type,
            CASE WHEN p.is_correct IS NULL THEN 'Pending'
                 WHEN p.is_correct THEN 'WIN'
                 ELSE 'LOSS' END as result
        FROM picks p
        JOIN users u ON p.user_id = u.id
        JOIN games g ON p.game_id = g.id
        WHERE p.week = ? AND p.season = ?
        ORDER BY u.username, g.game_date
    ''', (week, season))
    
    picks = cursor.fetchall()
    conn.close()
    
    if picks:
        return [{'Player': username, 'Game': matchup, 'Pick': pick_type.replace('_', ' ').title(), 'Result': result} 
                for username, matchup, pick_type, result in picks]
    return []

def get_user_picks_detailed(user_id, week, season):
    """Get detailed user picks for a specific week"""
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            g.away_team || ' @ ' || g.home_team as matchup,
            p.pick_type,
            g.spread,
            g.total,
            CASE WHEN p.is_correct IS NULL THEN 'Pending'
                 WHEN p.is_correct THEN 'WIN'
                 ELSE 'LOSS' END as result
        FROM picks p
        JOIN games g ON p.game_id = g.id
        WHERE p.user_id = ? AND p.week = ? AND p.season = ?
        ORDER BY g.game_date
    ''', (user_id, week, season))
    
    picks = cursor.fetchall()
    conn.close()
    
    if picks:
        return [{'Game': matchup, 'Pick': pick_type.replace('_', ' ').title(), 'Line': spread or total, 'Result': result} 
                for matchup, pick_type, spread, total, result in picks]
    return []

def main():
    init_database()
    
    st.title("🏈 Fantasy Football Pick'em League")
    
    # Authentication check
    username = check_authentication()
    user_email = st.user.get('email', 'unknown@email.com')
    user_id = get_user_id(user_email)
    
    st.sidebar.write(f"Welcome, {username}!")
    if st.sidebar.button("Logout"):
        st.logout()
    
    # Navigation
    tab1, tab2, tab3, tab4 = st.tabs(["Make Picks", "Scoreboard", "My Picks", "Admin"])
    
    with tab1:
        st.header("Weekly Picks")
        
        # Check if picks are still allowed
        if not is_pick_submission_allowed():
            st.error("Pick submission is closed. Games have started!")
            st.stop()
        
        games = get_current_week_games()
        
        if not games:
            st.warning("No games available for this week. Check the Admin tab to update game data.")
            st.stop()
        
        st.info("Select exactly 4 picks: 1 spread favorite, 1 spread underdog, 1 over, 1 under")
        
        # Get existing picks
        current_week = NFLDataFetcher()._get_current_nfl_week()
        current_season = datetime.now().year
        existing_picks = get_user_picks(user_id, current_week, current_season)
        
        with st.form("weekly_picks"):
            picks = []
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Spread Picks")
                for game in games:
                    if game[4] is not None:  # Has spread
                        game_id, home_team, away_team, game_date, spread = game[0], game[1], game[2], game[3], game[4]
                        
                        # Determine favorite and underdog
                        if spread < 0:
                            favorite = home_team
                            underdog = away_team
                            spread_text = f"{home_team} {spread}"
                        else:
                            favorite = away_team
                            underdog = home_team
                            spread_text = f"{away_team} -{spread}"
                        
                        st.write(f"**{away_team} @ {home_team}**")
                        st.write(f"Spread: {spread_text}")
                        
                        # Spread favorite checkbox
                        fav_key = f"{game_id}_spread_favorite"
                        fav_checked = st.checkbox(
                            f"Pick {favorite} (Favorite)", 
                            key=fav_key,
                            value=existing_picks.get(fav_key, False)
                        )
                        if fav_checked:
                            picks.append({'game_id': game_id, 'pick_type': 'spread_favorite'})
                        
                        # Spread underdog checkbox
                        dog_key = f"{game_id}_spread_underdog"
                        dog_checked = st.checkbox(
                            f"Pick {underdog} (Underdog)", 
                            key=dog_key,
                            value=existing_picks.get(dog_key, False)
                        )
                        if dog_checked:
                            picks.append({'game_id': game_id, 'pick_type': 'spread_underdog'})
                        
                        st.divider()
            
            with col2:
                st.subheader("Total Picks")
                for game in games:
                    if game[5] is not None:  # Has total
                        game_id, home_team, away_team, game_date, total = game[0], game[1], game[2], game[3], game[5]
                        
                        st.write(f"**{away_team} @ {home_team}**")
                        st.write(f"Total: {total}")
                        
                        # Over checkbox
                        over_key = f"{game_id}_over"
                        over_checked = st.checkbox(
                            f"Over {total}", 
                            key=over_key,
                            value=existing_picks.get(over_key, False)
                        )
                        if over_checked:
                            picks.append({'game_id': game_id, 'pick_type': 'over'})
                        
                        # Under checkbox
                        under_key = f"{game_id}_under"
                        under_checked = st.checkbox(
                            f"Under {total}", 
                            key=under_key,
                            value=existing_picks.get(under_key, False)
                        )
                        if under_checked:
                            picks.append({'game_id': game_id, 'pick_type': 'under'})
                        
                        st.divider()
            
            submitted = st.form_submit_button("Submit Picks")
            
            if submitted:
                # Validate picks (exactly 4: 1 of each type)
                pick_types = [pick['pick_type'] for pick in picks]
                required_types = ['spread_favorite', 'spread_underdog', 'over', 'under']
                
                if len(picks) != 4:
                    st.error(f"You must make exactly 4 picks. You made {len(picks)}.")
                elif not all(pick_type in pick_types for pick_type in required_types):
                    st.error("You must pick exactly 1 spread favorite, 1 spread underdog, 1 over, and 1 under.")
                else:
                    submit_picks(user_id, picks)
                    st.success("Picks submitted successfully!")
                    st.rerun()
        
    with tab2:
        st.header("Scoreboard")
        
        # Season standings
        st.subheader("Season Standings")
        season_standings = get_season_standings()
        if season_standings:
            df = pd.DataFrame(season_standings, columns=['Rank', 'Player', 'Total Points', 'Weeks Played', 'Perfect Weeks'])
            st.dataframe(df, use_container_width=True)
        
        # Weekly results
        st.subheader("Weekly Results")
        current_week = NFLDataFetcher()._get_current_nfl_week()
        current_season = datetime.now().year
        
        week_selector = st.selectbox("Select Week", range(1, current_week + 1), index=current_week - 1)
        
        weekly_results = get_weekly_results(week_selector, current_season)
        if weekly_results:
            df_weekly = pd.DataFrame(weekly_results, columns=['Player', 'Correct Picks', 'Bonus Point', 'Total Points'])
            st.dataframe(df_weekly, use_container_width=True)
        
        # Show picks if games have started
        if not is_pick_submission_allowed():
            st.subheader("This Week's Picks")
            all_picks = get_all_user_picks_for_week(current_week, current_season)
            if all_picks:
                st.dataframe(pd.DataFrame(all_picks), use_container_width=True)
        
    with tab3:
        st.header("My Picks")
        
        # Show current week picks
        current_week = NFLDataFetcher()._get_current_nfl_week()
        current_season = datetime.now().year
        
        st.subheader(f"Week {current_week} Picks")
        current_picks = get_user_picks_detailed(user_id, current_week, current_season)
        if current_picks:
            df_current = pd.DataFrame(current_picks)
            st.dataframe(df_current, use_container_width=True)
        else:
            st.info("No picks submitted for this week yet.")
        
        # Pick history
        st.subheader("Pick History")
        week_history = st.selectbox("Select Week for History", range(1, current_week + 1), key="history_week")
        
        history_picks = get_user_picks_detailed(user_id, week_history, current_season)
        if history_picks:
            df_history = pd.DataFrame(history_picks)
            st.dataframe(df_history, use_container_width=True)
            
            # Show weekly summary
            correct_count = sum(1 for pick in history_picks if pick['Result'] == 'WIN')
            st.metric("Correct Picks", f"{correct_count}/4")
            if correct_count == 4:
                st.success("Perfect Week! Bonus point earned! 🎉")
        else:
            st.info(f"No picks found for week {week_history}.")
        
    with tab4:
        st.header("Admin")
        st.info("Administrative functions (games, scoring)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Game Management")
            
            if st.button("Update Game Data"):
                with st.spinner("Fetching latest game data..."):
                    from data_fetcher import update_game_data
                    result = update_game_data()
                    st.success(result)
            
            # Manual game result entry
            st.subheader("Enter Game Results")
            games = get_current_week_games()
            
            if games:
                game_options = [f"{game[2]} @ {game[1]} (ID: {game[0]})" for game in games]
                selected_game = st.selectbox("Select Game", game_options)
                
                if selected_game:
                    game_id = int(selected_game.split("ID: ")[1].split(")")[0])
                    
                    col_home, col_away = st.columns(2)
                    with col_home:
                        home_score = st.number_input("Home Team Score", min_value=0, max_value=100, value=0)
                    with col_away:
                        away_score = st.number_input("Away Team Score", min_value=0, max_value=100, value=0)
                    
                    if st.button("Submit Game Result"):
                        conn = sqlite3.connect('pickem_league.db')
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE games 
                            SET final_score_home = ?, final_score_away = ?, is_final = TRUE
                            WHERE id = ?
                        ''', (home_score, away_score, game_id))
                        conn.commit()
                        conn.close()
                        st.success("Game result submitted!")
        
        with col2:
            st.subheader("Scoring")
            
            if st.button("Calculate All Pick Results"):
                with st.spinner("Calculating pick results..."):
                    calculate_pick_results()
                    update_weekly_scores()
                    st.success("Pick results calculated and scores updated!")
            
            # Show game status
            st.subheader("Game Status")
            conn = sqlite3.connect('pickem_league.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM games WHERE is_final = TRUE')
            final_games = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM games')
            total_games = cursor.fetchone()[0]
            conn.close()
            
            st.metric("Games Completed", f"{final_games}/{total_games}")
            
            # API Key configuration
            st.subheader("API Configuration")
            st.info("To get live betting lines, configure The Odds API key in secrets.toml")
            
            with st.expander("Show API Setup Instructions"):
                st.code('''
# Add to .streamlit/secrets.toml:
[odds_api]
key = "your-api-key-here"

# Get free API key from: https://the-odds-api.com/
                ''', language='toml')

if __name__ == "__main__":
    main()