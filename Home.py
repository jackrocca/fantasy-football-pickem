"""
Fantasy Football Pick'em League - Main Application
Home page with login and dashboard functionality.
"""
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.auth import check_login, logout, require_admin
from utils.storage import (get_current_week, get_all_users, load_results, save_results, 
                          load_picks, load_standings)
from utils.scoring import get_weekly_scoreboard, get_season_standings, get_user_stats, score_all_users_for_week
from utils.odds import get_picks_options, load_cached_odds, fetch_nfl_odds

# Page config
st.set_page_config(
    page_title="Fantasy Football Pick'em League",
    page_icon="🏈",
    layout="wide"
)

def show_dashboard():
    """Display the main dashboard after login."""
    current_week, current_year = get_current_week()
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("🏈 Fantasy Football Pick'em League")
        st.subheader(f"Week {current_week}, {current_year}")
    
    with col2:
        st.metric("Current User", st.session_state.username)
        if st.session_state.is_admin:
            st.markdown("🔧 **Admin**")
    
    with col3:
        if st.button("Logout", type="secondary"):
            logout()
    
    # User Stats Section
    st.header("Your Stats")
    user_stats = get_user_stats(st.session_state.username, current_year)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Points", user_stats['total_points'])
    with col2:
        st.metric("Perfect Weeks", user_stats['perfect_weeks'])
    with col3:
        st.metric("Weeks Played", user_stats['weeks_played'])
    with col4:
        st.metric("Avg Points/Week", f"{user_stats['average_points']:.1f}")
    
    # Current Week Scoreboard
    st.header(f"Week {current_week} Scoreboard")
    weekly_scores = get_weekly_scoreboard(current_week, current_year)
    
    if len(weekly_scores) > 0:
        # Highlight current user's row
        def highlight_user(row):
            if row['username'] == st.session_state.username:
                return ['background-color: #e6f3ff'] * len(row)
            return [''] * len(row)
        
        styled_df = weekly_scores.style.apply(highlight_user, axis=1)
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No picks have been scored for this week yet.")
    
    # Season Standings
    st.header(f"{current_year} Season Standings")
    season_standings = get_season_standings(current_year)
    
    if len(season_standings) > 0:
        # Highlight current user's row
        def highlight_user_season(row):
            if row['username'] == st.session_state.username:
                return ['background-color: #e6f3ff'] * len(row)
            return [''] * len(row)
        
        styled_season_df = season_standings.style.apply(highlight_user_season, axis=1)
        st.dataframe(styled_season_df, use_container_width=True)
    else:
        st.info("No season standings available yet.")
    
    # Quick Actions
    st.header("Quick Actions")
    
    if st.button("📝 Make This Week's Picks", type="primary", use_container_width=True):
        st.switch_page("pages/Pickem.py")
    
    # Recent Activity
    with st.expander("📊 Recent Activity", expanded=False):
        st.subheader("League Activity")
        
        all_users = get_all_users()
        st.write(f"**Total League Members:** {len(all_users)}")
        
        if len(weekly_scores) > 0:
            perfect_weeks_this_week = len(weekly_scores[weekly_scores['perfect_week'] == True])
            st.write(f"**Perfect Weeks This Week:** {perfect_weeks_this_week}")
            
            if perfect_weeks_this_week > 0:
                perfect_users = weekly_scores[weekly_scores['perfect_week'] == True]['username'].tolist()
                st.write(f"**Perfect Week Winners:** {', '.join(perfect_users)}")
        
        if len(season_standings) > 0:
            leader = season_standings.iloc[0]
            st.write(f"**Current Season Leader:** {leader['username']} ({leader['total_points']} points)")
    
    # Admin Panel for admin users
    if st.session_state.is_admin:
        st.divider()
        show_admin_panel()


def show_odds_cache_management(current_week, current_year):
    """Show odds cache management interface."""
    st.header("📡 Odds Cache Management")
    
    st.write("Manage cached odds data to avoid excessive API calls and preserve your API credits.")
    
    # Current cache status
    st.subheader("Current Cache Status")
    
    cached_odds = load_cached_odds(current_week, current_year)
    
    if cached_odds:
        st.success(f"✅ Cached odds available for Week {current_week}, {current_year}")
        
        # Show cache details
        import os
        import pandas as pd
        cache_file = os.path.join("data", "odds_cache.csv")
        
        if os.path.exists(cache_file):
            cache_df = pd.read_csv(cache_file)
            current_cache = cache_df[(cache_df['week'] == current_week) & (cache_df['year'] == current_year)]
            
            if len(current_cache) > 0:
                cache_date = current_cache.iloc[0]['cache_date']
                st.info(f"📅 Cached on: {cache_date}")
                
                # Show number of games in cache
                num_games = len(cached_odds)
                st.metric("Games in Cache", num_games)
    else:
        st.warning(f"⚠️ No cached odds for Week {current_week}, {current_year}")
    
    # Refresh odds button
    st.subheader("Refresh Odds")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Current Week Odds", type="primary"):
            try:
                with st.spinner("Fetching fresh odds from API..."):
                    odds_data = fetch_nfl_odds(force_refresh=True)
                    if odds_data:
                        st.success("✅ Fresh odds cached successfully!")
                        st.rerun()
            except Exception as e:
                st.error(f"Error refreshing odds: {e}")
    
    with col2:
        if st.button("👀 Preview Current Odds"):
            if cached_odds:
                # Show formatted preview
                formatted_options = get_picks_options(force_refresh=False)
                
                st.write("**Available Picks:**")
                
                with st.expander("Favorites", expanded=True):
                    for fav in formatted_options["favorites"][:5]:  # Show first 5
                        st.write(f"• {fav}")
                
                with st.expander("Underdogs"):
                    for dog in formatted_options["underdogs"][:5]:  # Show first 5
                        st.write(f"• {dog}")
                
                with st.expander("Overs"):
                    for over in formatted_options["overs"][:5]:  # Show first 5
                        st.write(f"• {over}")
                
                with st.expander("Unders"):
                    for under in formatted_options["unders"][:5]:  # Show first 5
                        st.write(f"• {under}")
            else:
                st.warning("No cached odds to preview")
    
    # Cache history
    st.subheader("Cache History")
    
    import os
    cache_file = os.path.join("data", "odds_cache.csv")
    
    if os.path.exists(cache_file):
        cache_df = pd.read_csv(cache_file)
        
        if len(cache_df) > 0:
            # Format for display
            display_cache = cache_df.copy()
            display_cache['cache_date'] = pd.to_datetime(display_cache['cache_date']).dt.strftime('%Y-%m-%d %H:%M')
            display_cache = display_cache.drop('odds_data', axis=1)  # Don't show the JSON data
            display_cache = display_cache.sort_values(['year', 'week'], ascending=[False, False])
            
            st.dataframe(display_cache, use_container_width=True)
            
            # Clear cache options
            st.subheader("Cache Management")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Clear Current Week Cache"):
                    remaining_cache = cache_df[~((cache_df['week'] == current_week) & (cache_df['year'] == current_year))]
                    remaining_cache.to_csv(cache_file, index=False)
                    st.success("Current week cache cleared!")
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear Old Caches"):
                    # Keep only current year
                    recent_cache = cache_df[cache_df['year'] == current_year]
                    recent_cache.to_csv(cache_file, index=False)
                    st.success("Old caches cleared!")
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Clear All Cache", type="secondary"):
                    empty_cache = pd.DataFrame(columns=['week', 'year', 'cache_date', 'odds_data'])
                    empty_cache.to_csv(cache_file, index=False)
                    st.warning("All cache cleared!")
                    st.rerun()
        else:
            st.info("No cache history available")
    else:
        st.info("No cache file found")
    
    # API usage info
    st.subheader("💡 API Usage Tips")
    
    st.info("""
    **Best Practices for API Usage:**
    
    1. **Refresh once per week** - Ideally on Tuesday when lines are set
    2. **Monitor your credits** - Free tier includes 500 requests/month
    3. **Use cache** - Cached data is used automatically until it expires (24 hours)
    4. **Check remaining requests** - Shown when fetching fresh data
    
    **When to refresh:**
    - Beginning of each week (Tuesday/Wednesday)
    - If odds look outdated
    - If games are missing from the current week
    """)
    
    # Show API key status
    try:
        api_key = st.secrets["api_keys"]["the_odds_api"]
        if api_key and api_key != "YOUR_API_KEY":
            st.success("✅ API key configured")
        else:
            st.warning("⚠️ API key not configured - using mock data")
    except:
        st.error("❌ API key not found in secrets")


def show_results_entry(current_week, current_year):
    """Show game results entry interface."""
    st.header("📊 Game Results Entry")
    
    # Load existing results
    results_df = load_results()
    week_results = results_df[(results_df['week'] == current_week) & (results_df['year'] == current_year)]
    
    # Show existing results
    if len(week_results) > 0:
        st.subheader("Current Week Results")
        st.dataframe(week_results, use_container_width=True)
        
        if st.button("Clear All Week Results", type="secondary"):
            # Remove this week's results
            remaining_results = results_df[~((results_df['week'] == current_week) & (results_df['year'] == current_year))]
            save_results(remaining_results.to_dict('records'))
            st.success("Week results cleared!")
            st.rerun()
    
    # Add new result form
    st.subheader("Add Game Result")
    
    with st.form("result_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            game_id = st.text_input("Game ID", placeholder="e.g., game1")
            home_team = st.text_input("Home Team", placeholder="e.g., Kansas City Chiefs")
            away_team = st.text_input("Away Team", placeholder="e.g., Buffalo Bills")
        
        with col2:
            home_score = st.number_input("Home Score", min_value=0, value=0)
            away_score = st.number_input("Away Score", min_value=0, value=0)
            total_points = home_score + away_score
            st.metric("Total Points", total_points)
        
        with col3:
            spread_favorite = st.selectbox("Spread Favorite", [home_team, away_team] if home_team and away_team else [""])
            spread_line = st.number_input("Spread Line", min_value=0.0, value=0.0, step=0.5)
            over_under_line = st.number_input("Over/Under Line", min_value=0.0, value=47.5, step=0.5)
        
        submitted = st.form_submit_button("Add Result", type="primary")
        
        if submitted:
            if not all([game_id, home_team, away_team]):
                st.error("Please fill in all required fields")
            else:
                # Add to results
                new_result = {
                    'week': current_week,
                    'year': current_year,
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'spread_favorite': spread_favorite,
                    'spread_line': spread_line,
                    'total_points': total_points,
                    'over_under_line': over_under_line
                }
                
                # Load existing results and add new one
                all_results = load_results().to_dict('records')
                all_results.append(new_result)
                save_results(all_results)
                
                st.success(f"Added result for {away_team} @ {home_team}")
                st.rerun()


def show_user_management():
    """Show user management interface."""
    st.header("👥 User Management")
    
    # Show all users
    all_users = get_all_users()
    
    if all_users:
        st.subheader("Current Users")
        user_df = pd.DataFrame({"Username": all_users})
        
        # Add admin status
        admin_status = []
        for user in all_users:
            try:
                is_admin = st.secrets.get("admins", {}).get(user, False)
                admin_status.append("✅ Admin" if is_admin else "Regular")
            except:
                admin_status.append("Regular")
        
        user_df["Status"] = admin_status
        st.dataframe(user_df, use_container_width=True)
    else:
        st.warning("No users found in secrets.toml")
    
    # Instructions for adding users
    st.subheader("Adding New Users")
    st.info("""
    To add new users:
    1. Edit `.streamlit/secrets.toml`
    2. Add new entries under `[users]` section
    3. Format: `username = "password"`
    4. For admin access, add `username = true` under `[admins]` section
    5. Restart the application
    """)
    
    # Show user picks summary
    st.subheader("User Activity Summary")
    picks_df = load_picks()
    standings_df = load_standings()
    
    if len(picks_df) > 0:
        current_week, current_year = get_current_week()
        
        # Picks this week
        week_picks = picks_df[(picks_df['week'] == current_week) & (picks_df['year'] == current_year)]
        st.write(f"**Picks submitted this week:** {len(week_picks)}")
        
        if len(week_picks) > 0:
            st.write("**Users who have picked:**")
            st.write(", ".join(week_picks['username'].tolist()))
        
        # Season stats
        if len(standings_df) > 0:
            season_stats = standings_df[standings_df['year'] == current_year]
            if len(season_stats) > 0:
                st.write(f"**Active users this season:** {len(season_stats)}")


def show_scoring_management(current_week, current_year):
    """Show scoring and results management."""
    st.header("🏆 Scoring Management")
    
    # Manual scoring trigger
    st.subheader("Score Current Week")
    
    # Check if we have results for this week
    results_df = load_results()
    week_results = results_df[(results_df['week'] == current_week) & (results_df['year'] == current_year)]
    
    if len(week_results) == 0:
        st.warning("No game results entered for this week. Please add results in the 'Results Entry' tab first.")
    else:
        st.success(f"Found {len(week_results)} game results for Week {current_week}")
        
        if st.button("🔄 Score All Users for This Week", type="primary"):
            try:
                week_scores = score_all_users_for_week(current_week, current_year)
                st.success(f"Scored {len(week_scores)} users for Week {current_week}")
                
                # Show results
                if week_scores:
                    scores_df = pd.DataFrame(week_scores)
                    scores_df = scores_df.sort_values('points', ascending=False)
                    st.dataframe(scores_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error scoring users: {e}")
    
    # Historical scoring
    st.subheader("Historical Scoring")
    
    # Week selector for re-scoring
    col1, col2 = st.columns(2)
    
    with col1:
        score_week = st.number_input("Week to Score", min_value=1, max_value=18, value=current_week)
    
    with col2:
        score_year = st.number_input("Year", min_value=2020, max_value=2030, value=current_year)
    
    if st.button(f"Score Week {score_week}, {score_year}"):
        try:
            week_scores = score_all_users_for_week(score_week, score_year)
            st.success(f"Re-scored {len(week_scores)} users for Week {score_week}, {score_year}")
        except Exception as e:
            st.error(f"Error scoring users: {e}")
    
    # View all picks for debugging
    st.subheader("Debug: View All Picks")
    picks_df = load_picks()
    
    if len(picks_df) > 0:
        # Filter options
        debug_week = st.selectbox("Week", sorted(picks_df['week'].unique()), 
                                 index=list(sorted(picks_df['week'].unique())).index(current_week) if current_week in picks_df['week'].unique() else 0)
        debug_year = st.selectbox("Year", sorted(picks_df['year'].unique()),
                                 index=list(sorted(picks_df['year'].unique())).index(current_year) if current_year in picks_df['year'].unique() else 0)
        
        filtered_picks = picks_df[(picks_df['week'] == debug_week) & (picks_df['year'] == debug_year)]
        
        if len(filtered_picks) > 0:
            st.dataframe(filtered_picks, use_container_width=True)
        else:
            st.info("No picks found for selected week/year")


def show_league_settings():
    """Show league settings and utilities."""
    st.header("⚙️ League Settings")
    
    # Current settings display
    current_week, current_year = get_current_week()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Settings")
        st.metric("Current Week", current_week)
        st.metric("Current Year", current_year)
        st.metric("Picks Locked", "Yes" if st.session_state.get('picks_locked', False) else "No")
    
    with col2:
        st.subheader("Quick Actions")
        
        # Manual lock/unlock (this would require additional state management)
        if st.button("🔒 Lock All Picks", help="Prevent any further pick changes"):
            st.session_state.picks_locked = True
            st.success("Picks locked!")
        
        if st.button("🔓 Unlock All Picks", help="Allow pick changes again"):
            st.session_state.picks_locked = False
            st.success("Picks unlocked!")
    
    # Data management
    st.subheader("Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Download data
        st.write("**Export Data**")
        
        picks_df = load_picks()
        if len(picks_df) > 0:
            csv = picks_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Picks CSV",
                data=csv,
                file_name=f"picks_{current_year}.csv",
                mime="text/csv"
            )
        
        results_df = load_results()
        if len(results_df) > 0:
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results CSV",
                data=csv,
                file_name=f"results_{current_year}.csv",
                mime="text/csv"
            )
        
        standings_df = load_standings()
        if len(standings_df) > 0:
            csv = standings_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Standings CSV",
                data=csv,
                file_name=f"standings_{current_year}.csv",
                mime="text/csv"
            )
    
    with col2:
        # Reset options
        st.write("**Reset Options**")
        
        if st.button("🗑️ Clear Current Week Picks", type="secondary"):
            picks_df = load_picks()
            remaining_picks = picks_df[~((picks_df['week'] == current_week) & (picks_df['year'] == current_year))]
            remaining_picks.to_csv("data/picks.csv", index=False)
            st.warning("Current week picks cleared!")
        
        if st.button("🗑️ Reset Season Standings", type="secondary"):
            standings_df = load_standings()
            remaining_standings = standings_df[standings_df['year'] != current_year]
            remaining_standings.to_csv("data/standings.csv", index=False)
            st.warning("Season standings reset!")
    
    with col3:
        # System info
        st.write("**System Info**")
        st.write(f"App started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.write(f"Total users: {len(get_all_users())}")
        
        picks_df = load_picks()
        st.write(f"Total picks: {len(picks_df)}")
        
        results_df = load_results()
        st.write(f"Total results: {len(results_df)}")


def show_admin_panel():
    """Display the admin panel for admin users."""
    current_week, current_year = get_current_week()
    
    # Admin section header
    st.header("⚙️ Admin Panel")
    st.subheader(f"League Management - Week {current_week}, {current_year}")
    
    # Admin tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Results Entry", "👥 User Management", "🏆 Scoring", "📡 Odds Cache", "⚙️ League Settings"])
    
    with tab1:
        show_results_entry(current_week, current_year)
    
    with tab2:
        show_user_management()
    
    with tab3:
        show_scoring_management(current_week, current_year)
    
    with tab4:
        show_odds_cache_management(current_week, current_year)
    
    with tab5:
        show_league_settings()


def main():
    """Main application entry point."""
    # Check authentication
    if not check_login():
        return
    
    # Show dashboard if authenticated
    show_dashboard()


if __name__ == "__main__":
    main()
