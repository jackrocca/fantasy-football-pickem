"""
Fantasy Football Pick'em League - Weekly Picks Page
Interface for submitting weekly picks with powerups.
"""
import streamlit as st
import sys
import os

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from utils.auth import check_login
from utils.storage import (get_current_week, is_thursday_or_later, 
                          save_picks, get_user_picks)
from utils.odds import get_picks_options, load_cached_odds, get_formatted_games_display
from utils.scoring import has_used_powerup

# Page config
st.set_page_config(
    page_title="Weekly Picks - Fantasy Football Pick'em",
    page_icon="📝",
    layout="wide"
)

def get_available_weeks():
    """Get list of available weeks for tabs."""
    import pandas as pd
    import os
    
    # Get current week as starting point
    current_week, current_year = get_current_week()
    
    # Check what weeks have cached data
    cache_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'odds_cache.csv')
    weeks_with_data = []
    
    if os.path.exists(cache_file):
        try:
            df = pd.read_csv(cache_file)
            if not df.empty:
                # Get unique week/year combinations
                unique_weeks = df[['week', 'year']].drop_duplicates()
                weeks_with_data = [(int(row['week']), int(row['year'])) for _, row in unique_weeks.iterrows()]
        except:
            pass
    
    # Always include current week
    if (current_week, current_year) not in weeks_with_data:
        weeks_with_data.append((current_week, current_year))
    
    # Sort by year and week (most recent first)
    weeks_with_data.sort(key=lambda x: (x[1], x[0]), reverse=True)
    
    return weeks_with_data


def show_week_content(week, year):
    """Display content for a specific week."""
    # Show cache status
    cached_odds = load_cached_odds(week, year)
    
    # Display this week's games
    st.header("🏈 Games")
    
    try:
        # For current week, use the live function, for others use cached data
        current_week, current_year = get_current_week()
        if week == current_week and year == current_year:
            games_display = get_formatted_games_display()
        else:
            # For past weeks, we'd need to create a function to format cached data
            # For now, just show that data exists
            games_display = []
        
        if games_display:
            # Create a nice display with columns for better layout
            cols_per_row = 2
            for i in range(0, len(games_display), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(games_display):
                        game = games_display[i + j]
                        with col:
                            # Use a card-like container
                            with st.container():
                                st.markdown(f"""
                                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 5px 0; background-color: #f9f9f9;">
                                    <h4 style="margin: 0; text-align: center; color: #1f77b4;">{game['formatted_text']}</h4>
                                    <p style="margin: 2px 0; text-align: center; font-size: 1.1em; color: #666;">
                                        Over / Under {game['total_line']}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
            
            st.markdown("---")  # Add separator between games and picks
        else:
            if not cached_odds:
                st.warning("No games data available for this week.")
            else:
                st.info("Games data is cached but display formatting is only available for current week.")
            
    except Exception as e:
        st.error(f"Error loading games display: {e}")


def show_picks_form():
    """Display the weekly picks form with tabs for different weeks."""
    current_week, current_year = get_current_week()
    
    # Header
    st.title("📝 Weekly Picks")
    
    # Get available weeks for tabs
    available_weeks = get_available_weeks()
    
    # Create tab labels (most recent first)
    tab_labels = [f"Week {week}" for week, year in available_weeks]
    
    # Create tabs
    tabs = st.tabs(tab_labels)
    
    # Display content for each tab
    for i, (week, year) in enumerate(available_weeks):
        with tabs[i]:
            st.subheader(f"Week {week}, {year}")
            
            # Show week content
            show_week_content(week, year)
            
            # Only show picks form for current week
            if week == current_week and year == current_year:
                # Check if picks are locked
                picks_locked = is_thursday_or_later()
                if picks_locked:
                    st.warning("⚠️ Picks are locked! Thursday has passed.")
                    st.info("You can view your picks below, but no changes can be made.")
                
                # Get existing picks
                existing_picks = get_user_picks(st.session_state.username, current_week, current_year)
                
                # Get available options
                picks_options = get_picks_options()
                
                if picks_options["favorites"][0] == "No games available":
                    st.error("No games available for picks this week.")
                    return
                
                # Show current picks if they exist
                if existing_picks:
                    st.success("✅ You have already submitted picks for this week!")
                    
                    with st.expander("View Your Current Picks", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Spread Picks:**")
                            st.write(f"Favorite: {existing_picks.get('favorite', 'None')}")
                            st.write(f"Underdog: {existing_picks.get('underdog', 'None')}")
                        
                        with col2:
                            st.write("**Total Picks:**")
                            st.write(f"Over: {existing_picks.get('over', 'None')}")
                            st.write(f"Under: {existing_picks.get('under', 'None')}")
                        
                        if existing_picks.get('perfect_powerup', False):
                            st.write("🚀 **Perfect Powerup ACTIVE** - Perfect week = 8 points, else 0 points")
                        
                        if existing_picks.get('line_helper', False):
                            adj = existing_picks.get('line_helper_adjustment', 0)
                            st.write(f"🎯 **Line Helper Used** - Adjustment: {adj:+} points")
                
                # Picks form
                with st.form("picks_form"):
                    st.header("Make Your Picks")
                    st.write("Select exactly **4 picks**: 1 Favorite, 1 Underdog, 1 Over, 1 Under")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Spread Picks")
                        
                        favorite_pick = st.selectbox(
                            "Select a Favorite (team getting points)",
                            [""] + picks_options["favorites"],
                            index=0 if not existing_picks else picks_options["favorites"].index(existing_picks.get('favorite', '')) + 1,
                            disabled=picks_locked,
                            help="Pick a team you think will cover the spread as the favorite"
                        )
                        
                        underdog_pick = st.selectbox(
                            "Select an Underdog (team giving points)",
                            [""] + picks_options["underdogs"],
                            index=0 if not existing_picks else picks_options["underdogs"].index(existing_picks.get('underdog', '')) + 1,
                            disabled=picks_locked,
                            help="Pick a team you think will cover the spread as the underdog"
                        )
                    
                    with col2:
                        st.subheader("Total Points Picks")
                        
                        over_pick = st.selectbox(
                            "Select an Over",
                            [""] + picks_options["overs"],
                            index=0 if not existing_picks else picks_options["overs"].index(existing_picks.get('over', '')) + 1,
                            disabled=picks_locked,
                            help="Pick a game you think will go OVER the total points line"
                        )
                        
                        under_pick = st.selectbox(
                            "Select an Under",
                            [""] + picks_options["unders"],
                            index=0 if not existing_picks else picks_options["unders"].index(existing_picks.get('under', '')) + 1,
                            disabled=picks_locked,
                            help="Pick a game you think will go UNDER the total points line"
                        )
                    
                    # Powerups section
                    st.header("🚀 Powerups (One-time per season)")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        perfect_powerup_used = has_used_powerup(st.session_state.username, current_year, "perfect_powerup")
                        perfect_powerup = st.checkbox(
                            "Perfect Powerup",
                            value=existing_picks.get('perfect_powerup', False) if existing_picks else False,
                            disabled=picks_locked or perfect_powerup_used,
                            help="If you get all 4 picks correct = 8 points. If you miss any = 0 points."
                        )
                        
                        if perfect_powerup_used:
                            st.caption("✅ Already used this season")
                    
                    with col2:
                        line_helper_used = has_used_powerup(st.session_state.username, current_year, "line_helper")
                        line_helper = st.checkbox(
                            "Line Helper",
                            value=existing_picks.get('line_helper', False) if existing_picks else False,
                            disabled=picks_locked or line_helper_used,
                            help="Adjust any Over/Under line by ±5 points"
                        )
                        
                        if line_helper_used:
                            st.caption("✅ Already used this season")
                    
                    # Line helper adjustment
                    line_helper_adjustment = 0
                    if line_helper and not line_helper_used:
                        line_helper_adjustment = st.slider(
                            "Line Helper Adjustment",
                            min_value=-5,
                            max_value=5,
                            value=existing_picks.get('line_helper_adjustment', 0) if existing_picks else 0,
                            step=1,
                            disabled=picks_locked,
                            help="Adjust the Over/Under line by this amount"
                        )
                    
                    # Submit button
                    submitted = st.form_submit_button(
                        "Submit Picks" if not existing_picks else "Update Picks",
                        type="primary",
                        disabled=picks_locked,
                        use_container_width=True
                    )
                    
                    if submitted:
                        # Validate picks
                        errors = []
                        
                        if not favorite_pick:
                            errors.append("Must select a Favorite")
                        if not underdog_pick:
                            errors.append("Must select an Underdog")
                        if not over_pick:
                            errors.append("Must select an Over")
                        if not under_pick:
                            errors.append("Must select an Under")
                        
                        # Check for conflicts (same game picked multiple times)
                        picks = [favorite_pick, underdog_pick, over_pick, under_pick]
                        games = []
                        for pick in picks:
                            if pick:
                                if " vs " in pick:
                                    game = pick.split(" vs ")[0] + " vs " + pick.split(" vs ")[1].split(" ")[0]
                                elif " @ " in pick:
                                    game = pick.split(" @ ")[0] + " @ " + pick.split(" @ ")[1].split(" ")[0]
                                else:
                                    # Extract game from spread pick
                                    if "(" in pick:
                                        teams = pick.split(" (")[0]
                                        game = teams
                                    else:
                                        game = pick
                                games.append(game)
                        
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            try:
                                save_picks(
                                    username=st.session_state.username,
                                    week=current_week,
                                    year=current_year,
                                    favorite=favorite_pick,
                                    underdog=underdog_pick,
                                    over=over_pick,
                                    under=under_pick,
                                    perfect_powerup=perfect_powerup,
                                    line_helper=line_helper,
                                    line_helper_adjustment=line_helper_adjustment
                                )
                                st.success("✅ Picks saved successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving picks: {e}")
    
    # Navigation (outside tabs)
    st.markdown("---")
    st.header("Navigation")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏠 Back to Home", use_container_width=True):
            st.switch_page("Home.py")
    
    with col2:
        if st.session_state.is_admin:
            if st.button("⚙️ Admin Panel", use_container_width=True):
                st.switch_page("pages/Admin.py")


def main():
    """Main page entry point."""
    # Check authentication
    if not check_login():
        return
    
    # Show picks form
    show_picks_form()


if __name__ == "__main__":
    main()
