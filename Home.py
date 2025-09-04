"""
Fantasy Football Pick'em League - Main Application
Home page with login and dashboard functionality.
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.auth import check_login, logout
from utils.storage import (get_current_week, get_all_users, load_results, save_results, 
                          load_picks, load_standings)
from utils.scoring import get_weekly_scoreboard, get_season_standings, get_user_stats, score_all_users_for_week, get_user_weekly_history
from utils.odds import get_picks_options, load_cached_odds, fetch_nfl_odds

# Page config
st.set_page_config(
    page_title="Fantasy Football Pick 4 League",
    page_icon="🏈",
    layout="wide"
)

@st.dialog("User Pick History")
def show_user_history_modal(username, current_year):
    """Display user's complete pick history in a modal dialog."""
    st.subheader(f"📊 {username}'s Season History")
    
    # Get user's weekly history
    weekly_history = get_user_weekly_history(username, current_year)
    
    if len(weekly_history) == 0:
        st.info(f"🎯 {username} hasn't made any picks yet this season!")
        if st.button("Close", type="primary"):
            st.rerun()
        return
    
    # Overall season stats
    total_points = sum([w['points'] for w in weekly_history])
    total_wins = sum([w['wins'] for w in weekly_history])
    perfect_weeks = sum([1 for w in weekly_history if w['perfect_week']])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Points", f"{total_points:.1f}")
    col2.metric("Total Wins", f"{total_wins}/{len(weekly_history) * 4}")
    col3.metric("Perfect Weeks", perfect_weeks)
    col4.metric("Win Rate", f"{(total_wins / (len(weekly_history) * 4) * 100):.0f}%")
    
    st.divider()
    
    # Display weekly picks
    for week_data in weekly_history:
        week = week_data['week']
        points = week_data['points']
        wins = week_data['wins']
        perfect_week = week_data['perfect_week']
        picks = week_data['picks']
        powerups = week_data['powerups']
        submission_time = week_data.get('submission_time', '')
        
        # Week header
        week_status = "🔥 PERFECT!" if perfect_week else f"{wins}/4 wins"
        powerup_indicators = ""
        if powerups['super_spread']:
            powerup_indicators += " ⚡"
        if powerups['total_helper']:
            powerup_indicators += " 🎯"
        if powerups['perfect_prediction']:
            powerup_indicators += " 💎"
        
        # Format submission time
        submit_text = ""
        if submission_time:
            try:
                from datetime import datetime
                submit_dt = datetime.fromisoformat(submission_time.replace('Z', '+00:00'))
                submit_text = f" • Submitted {submit_dt.strftime('%m/%d %I:%M %p')}"
            except:
                pass
        
        with st.expander(f"🏈 Week {week} • {points} points • {week_status}{powerup_indicators}{submit_text}"):
            # Display picks in columns
            if picks:
                pick_cols = st.columns(len(picks))
                
                for i, (pick_type, pick_data) in enumerate(picks.items()):
                    with pick_cols[i]:
                        pick_value = pick_data['pick']
                        result = pick_data['result']
                        
                        # Determine styling based on result
                        if result == 'win':
                            bg_color = "#d4e6b7"
                            border_color = "#4caf50"
                            result_emoji = "✅"
                        elif result == 'loss':
                            bg_color = "#ffd6d6"
                            border_color = "#f44336"
                            result_emoji = "❌"
                        elif result == 'push':
                            bg_color = "#fff3cd"
                            border_color = "#ff9800"
                            result_emoji = "🤝"
                        else:  # pending
                            bg_color = "#f0f0f0"
                            border_color = "#999"
                            result_emoji = "⏳"
                        
                        # Pick type label
                        pick_label = pick_type.upper()
                        
                        st.markdown(f"""
                        <div style="
                            background-color: {bg_color};
                            border: 2px solid {border_color};
                            border-radius: 6px;
                            padding: 8px;
                            margin: 4px 0;
                            text-align: center;
                            font-size: 12px;
                        ">
                            <div style="font-weight: bold; margin-bottom: 4px;">
                                {result_emoji} {pick_label}
                            </div>
                            <div style="color: #666; word-wrap: break-word;">
                                {pick_value}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.write("No picks recorded for this week")
            
            # Show powerups used
            if any(powerups.values()):
                st.markdown("**Powerups Used:**")
                powerup_list = []
                if powerups['super_spread']:
                    powerup_list.append("⚡ Super Spread")
                if powerups['total_helper']:
                    powerup_list.append("🎯 Total Helper")
                if powerups['perfect_prediction']:
                    powerup_list.append("💎 Perfect Prediction")
                st.write(" • ".join(powerup_list))


def show_nfl_style_leaderboard(standings_df, current_year):
    """Display NFL-style leaderboard with enhanced styling."""
    
    # Leaderboard header with NFL styling
    st.markdown("""
    <div style="
        background: linear-gradient(45deg, #1f4e79, #2d5aa0);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    ">
        <h2 style="margin: 0; font-family: 'Arial Black', sans-serif;">
            🏆 2025 Season Leaderboard
        </h2>
        <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">
            Updated Weekly
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create standings cards for each user
    for idx, row in standings_df.iterrows():
        rank = row['rank']
        username = row['username']
        total_points = row['total_points']
        perfect_weeks = row['perfect_weeks']
        weeks_played = row['weeks_played']
        avg_points = row['avg_points']
        
        # Determine rank styling
        if rank == 1:
            rank_color = "#FFD700"  # Gold
            rank_emoji = "🥇"
            border_color = "#FFD700"
        elif rank == 2:
            rank_color = "#C0C0C0"  # Silver
            rank_emoji = "🥈"
            border_color = "#C0C0C0"
        elif rank == 3:
            rank_color = "#CD7F32"  # Bronze
            rank_emoji = "🥉"
            border_color = "#CD7F32"
        else:
            rank_color = "#4a5568"  # Gray
            rank_emoji = f"#{rank}"
            border_color = "#e2e8f0"
        
        # Highlight current user
        is_current_user = username == st.session_state.username
        bg_color = "#e6f3ff" if is_current_user else "#f8f9fa"
        border_style = f"3px solid {border_color}" if is_current_user else f"1px solid {border_color}"
        
        # Create columns for card and button
        card_col, button_col = st.columns([4, 1])
        
        with card_col:
            # User card with stats
            st.markdown(f"""
            <div style="
                background-color: {bg_color};
                border: {border_style};
                border-radius: 12px;
                padding: 16px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
                height: 90px;
                display: flex;
                align-items: center;
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                    <div style="display: flex; align-items: center;">
                        <div style="
                            background-color: {rank_color};
                            color: white;
                            border-radius: 50%;
                            width: 50px;
                            height: 50px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-weight: bold;
                            font-size: 16px;
                            margin-right: 16px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        ">
                            {rank_emoji}
                        </div>
                        <div>
                            <h3 style="
                                margin: 0;
                                font-size: 20px;
                                font-weight: bold;
                                color: #2d3748;
                            ">
                                {username} {'👑' if is_current_user else ''}
                            </h3>
                            <p style="
                                margin: 2px 0 0 0;
                                color: #718096;
                                font-size: 14px;
                            ">
                                {weeks_played} weeks played
                            </p>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="display: flex; gap: 20px; align-items: center;">
                            <div style="text-align: center;">
                                <div style="
                                    font-size: 24px;
                                    font-weight: bold;
                                    color: #2d5aa0;
                                    line-height: 1;
                                ">
                                    {total_points}
                                </div>
                                <div style="
                                    font-size: 12px;
                                    color: #718096;
                                    text-transform: uppercase;
                                    letter-spacing: 0.5px;
                                ">
                                    POINTS
                                </div>
                            </div>
                            <div style="text-align: center;">
                                <div style="
                                    font-size: 20px;
                                    font-weight: bold;
                                    color: #38a169;
                                    line-height: 1;
                                ">
                                    {perfect_weeks}
                                </div>
                                <div style="
                                    font-size: 12px;
                                    color: #718096;
                                    text-transform: uppercase;
                                    letter-spacing: 0.5px;
                                ">
                                    PERFECT
                                </div>
                            </div>
                            <div style="text-align: center;">
                                <div style="
                                    font-size: 18px;
                                    font-weight: bold;
                                    color: #805ad5;
                                    line-height: 1;
                                ">
                                    {avg_points:.1f}
                                </div>
                                <div style="
                                    font-size: 12px;
                                    color: #718096;
                                    text-transform: uppercase;
                                    letter-spacing: 0.5px;
                                ">
                                    AVG
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with button_col:
            # Add some spacing to align with card
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Pick History ", key=f"details_{username}", use_container_width=True, help=f"View {username}'s pick history"):
                show_user_history_modal(username, current_year)
        
        # Add spacing between cards
        st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
    
    # Add league summary footer
    st.markdown(f"""
    <div style="
        margin-top: 20px;
        padding: 16px;
        background: linear-gradient(90deg, #f7fafc, #edf2f7);
        border-radius: 8px;
        border-left: 4px solid #2d5aa0;
        text-align: center;
    ">
        <p style="
            margin: 0;
            color: #4a5568;
            font-size: 14px;
            font-weight: 500;
        ">
            🏈 <strong>{len(standings_df)}</strong> active competitors • Season {current_year}
        </p>
    </div>
    <br>
    <br>
    """, unsafe_allow_html=True)

    st.divider()

def show_dashboard():
    """Display the main dashboard after login."""
    current_week, current_year = get_current_week()
    
    # Header

    st.title("🏈 Fantasy Football Pick 4 League")
    st.subheader(f"Currently Week {current_week}, {current_year}")
    
    with st.sidebar:
        st.metric("Current User", st.session_state.username)
        if st.button("Logout", type="secondary"):
            logout()
    
    st.divider()

    # User Stats Section
    st.subheader("Your Stats")
    user_stats = get_user_stats(st.session_state.username, current_year)
    
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Total Points", user_stats['total_points'], border=True)   
    metric2.metric("Perfect Weeks", user_stats['perfect_weeks'], border=True)
    metric3.metric("Weeks Played", user_stats['weeks_played'], border=True)
    metric4.metric("Avg Points/Week", f"{user_stats['average_points']:.1f}", border=True)
    
    st.divider()

    # Season Scoreboard
    season_standings = get_season_standings(current_year)
    
    if len(season_standings) > 0:
        show_nfl_style_leaderboard(season_standings, current_year)
    else:
        st.info("No season standings available yet.")
    
    
    if st.button("📝 Make This Week's Picks", type="primary", use_container_width=True):
        st.switch_page("pages/Pickem.py")
    













def main():
    """Main application entry point."""
    # Check authentication
    if not check_login():
        return
    
    # Show dashboard if authenticated
    show_dashboard()


if __name__ == "__main__":
    main()
