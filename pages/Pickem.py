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
from utils.storage import (get_current_week, is_thursday_or_later)
from utils.odds import (get_locked_lines_for_week, find_wednesday_9am_snapshot,
                       save_picks_to_firestore, get_user_picks_from_firestore,
                       create_picks_data_from_form, filter_games_by_week, is_week_complete,
                       get_scores_for_games)
from utils.scoring import has_used_powerup

# Page config
st.set_page_config(
    page_title="Weekly Picks - Fantasy Football Pick'em",
    page_icon="📝",
    layout="wide"
)

def get_available_weeks():
    """Get list of available weeks for tabs - only active week and completed weeks."""
    current_week, current_year = get_current_week()
    weeks_with_data = []
    
    # If current week is complete, add next week as first tab (if it exists)
    if is_week_complete(current_week, current_year):
        next_week = current_week + 1
        if next_week <= 18:  # NFL regular season is 18 weeks
            weeks_with_data.append((next_week, current_year))
        elif current_year == 2025:  # Handle year transition to 2026
            weeks_with_data.append((1, 2026))
    
    # Add current week (will be first if not complete, second if complete)
    weeks_with_data.append((current_week, current_year))
    
    # Add all previous completed weeks in reverse order (most recent first)
    for week_num in range(current_week - 1, 0, -1):
        weeks_with_data.append((week_num, current_year))
    
    return weeks_with_data


def show_week_content(week, year):
    """Display content for a specific week."""
    # Get the Wednesday 9AM snapshot for this week
    snapshot = find_wednesday_9am_snapshot(week, year)
    
    # Display this week's games
    st.header("🏈 Games")
    
    if snapshot and snapshot.get('GAMES'):
        # Filter games to only show games from this specific week
        all_games = snapshot['GAMES']
        week_games = filter_games_by_week(all_games, week, year)
        
        # Get scores for games in this week
        game_ids = [game.get('GAME_ID') for game in week_games if game.get('GAME_ID')]
        game_scores = get_scores_for_games(game_ids)
        
        # Filter games with DraftKings odds and format for display
        display_games = []
        for game in week_games:
            if game.get('BOOKMAKER') == 'DraftKings':
                home_team = game.get('HOME_TEAM', '')
                away_team = game.get('AWAY_TEAM', '')
                spread_home = game.get('SPREAD_POINTS_HOME', 0)
                over_points = game.get('OVER_POINTS', 0)
                game_id = game.get('GAME_ID', '')
                
                # Check if game has scores (is completed)
                game_score = game_scores.get(game_id, {})
                is_completed = game_score.get('completed', False)
                
                if spread_home < 0:
                    formatted_text = f"{away_team} @ {home_team} ({spread_home})"
                else:
                    formatted_text = f"{away_team} @ {home_team} (+{spread_home})"
                
                display_games.append({
                    'formatted_text': formatted_text,
                    'total_line': over_points,
                    'home_team': home_team,
                    'away_team': away_team,
                    'game_id': game_id,
                    'is_completed': is_completed,
                    'home_score': game_score.get('home_score', 0) if is_completed else None,
                    'away_score': game_score.get('away_score', 0) if is_completed else None,
                    'total_points': game_score.get('total_points', 0) if is_completed else None
                })
        
        if display_games:
            # Create a nice display with columns for better layout
            cols_per_row = 2
            for i in range(0, len(display_games), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(display_games):
                        game = display_games[i + j]
                        with col:
                            # Use a card-like container
                            with st.container():
                                # Different styling for completed vs active games
                                if game.get('is_completed', False):
                                    # Completed game with scores
                                    bg_color = "#e8f5e8"  # Light green
                                    border_color = "#4caf50"  # Green
                                    text_color = "#2e7d32"  # Dark green
                                    
                                    score_text = f"{game['away_team']} {game['away_score']} - {game['home_score']} {game['home_team']}"
                                    total_text = f"Final Total: {game['total_points']}"
                                    
                                    st.markdown(f"""
                                    <div style="border: 2px solid {border_color}; border-radius: 8px; padding: 15px; margin: 5px 0; background-color: {bg_color};">
                                        <h4 style="margin: 0; text-align: center; color: {text_color};">🏁 FINAL</h4>
                                        <h3 style="margin: 5px 0; text-align: center; color: {text_color}; font-weight: bold;">{score_text}</h3>
                                        <p style="margin: 2px 0; text-align: center; font-size: 1.1em; color: {text_color};">
                                            {total_text}
                                        </p>
                                        <p style="margin: 2px 0; text-align: center; font-size: 0.9em; color: #666;">
                                            Line was: {game['formatted_text']} o/u{game['total_line']}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    # Active game (can still be picked)
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
            st.warning("No DraftKings games found in snapshot.")
    else:
        st.warning(f"No locked lines available for Week {week}, {year}. Snapshots are generated from Wednesday 9AM PST data.")


def show_picks_form():
    """Display the weekly picks form with tabs for different weeks."""
    current_week, current_year = get_current_week()
    
    # Header
    st.title("📝 Weekly Picks")
    
    # Get available weeks for tabs
    available_weeks = get_available_weeks()
    
    # Create tab labels with year when different from current year
    current_year = get_current_week()[1]
    tab_labels = []
    for week, year in available_weeks:
        if year == current_year:
            tab_labels.append(f"Week {week}")
        else:
            tab_labels.append(f"Week {week} ({year})")
    
    
    # Create tabs
    tabs = st.tabs(tab_labels)
    
    # Display content for each tab
    for i, (week, year) in enumerate(available_weeks):
        with tabs[i]:
            
            # Show week content
            show_week_content(week, year)
            
            # Only show picks form for current week
            if week == current_week and year == current_year:
                # Check if picks are locked
                picks_locked = is_thursday_or_later()
                if picks_locked:
                    st.warning("⚠️ Picks deadline has passed! Thursday Night Football has started.")
                    st.info("Late submissions are automatically deducted 1 point and forfeit scoring specials eligibility.")
                    st.info("You can still submit picks below, but no changes can be made once submitted.")
                
                # Get existing picks from Firestore
                existing_picks = get_user_picks_from_firestore(st.session_state.username, current_week, current_year)
                
                # Get locked lines for this week
                picks_options = get_locked_lines_for_week(current_week, current_year)
                
                if picks_options["favorites"][0] in ["No locked lines available", "Error loading lines"]:
                    st.error("No locked lines available for picks this week. Lines are locked based on Wednesday 9AM PST snapshots.")
                    st.info(picks_options.get("snapshot_info", "Snapshot information not available"))
                    return
                
                # Snapshot info available but not displayed to keep UI clean
                
                # Get snapshot games for parsing picks
                snapshot = find_wednesday_9am_snapshot(current_week, current_year)
                snapshot_games = snapshot.get('GAMES', []) if snapshot else []
                
                # Show current picks if they exist
                if existing_picks:
                    st.success("✅ You have already submitted picks for this week!")
                    
                    with st.expander("View Your Current Picks", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Spread Picks:**")
                            st.write(f"Favorite: {existing_picks.get('FAVORITE_TEAM', 'None')} ({existing_picks.get('FAVORITE_SPREAD', 'N/A')})")
                            st.write(f"Underdog: {existing_picks.get('UNDERDOG_TEAM', 'None')} ({existing_picks.get('UNDERDOG_SPREAD', 'N/A')})")
                        
                        with col2:
                            st.write("**Total Picks:**")
                            st.write(f"Over: {existing_picks.get('OVER_POINTS', 'None')} points")
                            st.write(f"Under: {existing_picks.get('UNDER_POINTS', 'None')} points")
                        
                        # Display active scoring specials
                        specials = []
                        if existing_picks.get('SUPER_SPREAD', False):
                            specials.append("🎯 **Super Spread ACTIVE**")
                        
                        if existing_picks.get('TOTAL_HELPER'):
                            helper_type = existing_picks.get('TOTAL_HELPER', '')
                            adj = existing_picks.get('TOTAL_HELPER_ADJUSTMENT', 0)
                            specials.append(f"📐 **Total Helper Used** - {helper_type} with {adj:+} points adjustment")
                        
                        if existing_picks.get('PERFECT_PREDICTION', False):
                            specials.append("🔮 **Perfect Prediction ACTIVE** - Perfect week = 8 points")
                        
                        if specials:
                            st.write("**Active Scoring Specials:**")
                            for special in specials:
                                st.write(special)
                        
                        # Show submission timestamp
                        if existing_picks.get('SUBMISSION_TIMESTAMP'):
                            st.write(f"**Submitted:** {existing_picks['SUBMISSION_TIMESTAMP'][:19]}")
                
                # Picks form
                with st.form("picks_form"):
                    st.header("Make Your Picks")
                    st.write("Select exactly **4 picks from 4 different games**: 1 Favorite, 1 Underdog, 1 Over, 1 Under")

                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Spread Picks")
                        
                        # Find existing favorite pick for default selection
                        fav_default_index = 0
                        if existing_picks and existing_picks.get('FAVORITE_TEAM'):
                            fav_team = existing_picks.get('FAVORITE_TEAM')
                            fav_spread = existing_picks.get('FAVORITE_SPREAD', 0)
                            fav_pick_str = f"{fav_team} ({fav_spread})"
                            try:
                                fav_default_index = picks_options["favorites"].index(fav_pick_str) + 1
                            except ValueError:
                                fav_default_index = 0
                        
                        favorite_pick = st.selectbox(
                            "Select a Favorite",
                            [""] + picks_options["favorites"],
                            index=fav_default_index,
                            disabled=picks_locked,
                            help="Pick a team you think will cover the spread as the favorite"
                        )
                        
                        # Find existing underdog pick for default selection
                        und_default_index = 0
                        if existing_picks and existing_picks.get('UNDERDOG_TEAM'):
                            und_team = existing_picks.get('UNDERDOG_TEAM')
                            und_spread = existing_picks.get('UNDERDOG_SPREAD', 0)
                            und_pick_str = f"{und_team} (+{abs(und_spread)})"
                            try:
                                und_default_index = picks_options["underdogs"].index(und_pick_str) + 1
                            except ValueError:
                                und_default_index = 0
                        
                        underdog_pick = st.selectbox(
                            "Select an Underdog",
                            [""] + picks_options["underdogs"],
                            index=und_default_index,
                            disabled=picks_locked,
                            help="Pick a team you think will cover the spread as the underdog"
                        )
                    
                    with col2:
                        st.subheader("Total Points Picks")
                        
                        # Find existing over pick for default selection
                        over_default_index = 0
                        if existing_picks and existing_picks.get('OVER_POINTS'):
                            over_points = existing_picks.get('OVER_POINTS', 0)
                            # Need to find the matching over pick string
                            for i, over_option in enumerate(picks_options["overs"]):
                                if f"o{over_points}" in over_option:
                                    over_default_index = i + 1
                                    break
                        
                        over_pick = st.selectbox(
                            "Select an Over",
                            [""] + picks_options["overs"],
                            index=over_default_index,
                            disabled=picks_locked,
                            help="Pick a game you think will go OVER the total points line"
                        )
                        
                        # Find existing under pick for default selection
                        under_default_index = 0
                        if existing_picks and existing_picks.get('UNDER_POINTS'):
                            under_points = existing_picks.get('UNDER_POINTS', 0)
                            # Need to find the matching under pick string
                            for i, under_option in enumerate(picks_options["unders"]):
                                if f"u{under_points}" in under_option:
                                    under_default_index = i + 1
                                    break
                        
                        under_pick = st.selectbox(
                            "Select an Under",
                            [""] + picks_options["unders"],
                            index=under_default_index,
                            disabled=picks_locked,
                            help="Pick a game you think will go UNDER the total points line"
                        )
                    
                    # Scoring Specials section
                    st.header("🚀 Scoring Specials (One-time per season)")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        super_spread_used = has_used_powerup(st.session_state.username, current_year, "super_spread")
                        
                        # Check if favorite pick is eligible for super spread (≤-5)
                        super_spread_eligible = True  # Default to eligible
                        if favorite_pick and " (" in favorite_pick:
                            try:
                                spread_str = favorite_pick.split("(")[1].replace(")", "")
                                spread_value = float(spread_str)
                                super_spread_eligible = spread_value <= -5.0
                            except:
                                super_spread_eligible = False
                        elif favorite_pick:
                            super_spread_eligible = False  # No spread info found
                        
                        # Get existing super spread choice
                        existing_super_spread = existing_picks.get('SUPER_SPREAD', False) if existing_picks else False
                        super_spread_options = ["No", "Yes"]
                        default_index = 1 if existing_super_spread else 0
                        
                        super_spread_choice = st.selectbox(
                            "Super Spread",
                            super_spread_options,
                            index=default_index,
                            disabled=super_spread_used or not super_spread_eligible or (picks_locked and not existing_picks),
                            help="Available if your favorite is at least -5. Team needs to cover double (e.g., -10 for -5 line) to earn 2.5 points. Push = 1 point. Miss = 0 points. NOT available for late submissions."
                        )
                        
                        super_spread = super_spread_choice == "Yes"
                        
                        if super_spread_used:
                            st.caption("✅ Already used this season")
                        elif not super_spread_eligible and favorite_pick:
                            st.caption("⚠️ Favorite must be -5.0 or bigger to use")
                        elif favorite_pick and super_spread_eligible:
                            spread_str = favorite_pick.split("(")[1].replace(")", "")
                            st.caption(f"✅ Eligible: {spread_str} qualifies")
                    
                    with col2:
                        total_helper_used = has_used_powerup(st.session_state.username, current_year, "total_helper")
                        
                        # Get existing total helper choice
                        existing_helper_choice = existing_picks.get('TOTAL_HELPER', '') if existing_picks else ''
                        helper_options = ["None", "Over", "Under"]
                        default_index = 0
                        if existing_helper_choice == 'OVER':
                            default_index = 1
                        elif existing_helper_choice == 'UNDER':
                            default_index = 2
                        
                        total_helper_choice = st.selectbox(
                            "Total Helper",
                            helper_options,
                            index=default_index,
                            disabled=total_helper_used or (picks_locked and not existing_picks),
                            help="Apply 5-point advantage to your Over or Under pick. No extra points allotted. NOT available for late submissions."
                        )
                        
                        if total_helper_used:
                            st.caption("✅ Already used this season")
                    
                    with col3:
                        perfect_prediction_used = has_used_powerup(st.session_state.username, current_year, "perfect_prediction")
                        
                        # Get existing perfect prediction choice
                        existing_perfect_prediction = existing_picks.get('PERFECT_PREDICTION', False) if existing_picks else False
                        perfect_prediction_options = ["No", "Yes"]
                        default_index = 1 if existing_perfect_prediction else 0
                        
                        perfect_prediction_choice = st.selectbox(
                            "Perfect Prediction",
                            perfect_prediction_options,
                            index=default_index,
                            disabled=perfect_prediction_used or (picks_locked and not existing_picks),
                            help="A 4/4 week will result in 8 points (instead of normal 5). NOT available for late submissions."
                        )
                        
                        perfect_prediction = perfect_prediction_choice == "Yes"
                        
                        if perfect_prediction_used:
                            st.caption("✅ Already used this season")
                    
                    # Calculate total helper adjustment based on selection
                    total_helper_adjustment = 0
                    if total_helper_choice == "Over":
                        total_helper_adjustment = -5  # Over line goes DOWN (easier to hit)
                    elif total_helper_choice == "Under":
                        total_helper_adjustment = 5   # Under line goes UP (easier to hit)
                    
                    # Submit button
                    if picks_locked:
                        st.warning("⚠️ **Late Submission Warning**: This submission will be penalized -1 point and scoring specials will be forfeited.")
                    
                    submitted = st.form_submit_button(
                        "Submit Late Picks (-1 point penalty)" if picks_locked and not existing_picks else "Submit Picks" if not existing_picks else "Update Picks",
                        type="secondary" if picks_locked else "primary",
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
                        
                        # Validate Super Spread eligibility
                        if super_spread:
                            if not favorite_pick:
                                errors.append("Must select a Favorite to use Super Spread")
                            elif " (" in favorite_pick:
                                try:
                                    spread_str = favorite_pick.split("(")[1].replace(")", "")
                                    spread_value = float(spread_str)
                                    if spread_value > -5.0:
                                        errors.append(f"Super Spread requires favorite spread of -5.0 or bigger. Your pick ({spread_str}) is not eligible.")
                                except:
                                    errors.append("Invalid favorite pick format for Super Spread validation")
                            else:
                                errors.append("Cannot determine favorite spread for Super Spread validation")
                        
                        # Validate Total Helper selection
                        if total_helper_choice in ["Over", "Under"]:
                            if total_helper_choice == "Over" and not over_pick:
                                errors.append("Must select an Over pick to use Total Helper on Over")
                            elif total_helper_choice == "Under" and not under_pick:
                                errors.append("Must select an Under pick to use Total Helper on Under")
                        
                        # Check for conflicts (same game picked multiple times)
                        # Extract game identifiers from each pick
                        def extract_game_teams(pick):
                            """Extract the two teams from a pick string to identify the game."""
                            if not pick:
                                return None
                            
                            # For spread picks: "Team Name (-X.X)" or "Team Name (+X.X)"
                            if " (" in pick and pick.endswith(")"):
                                team = pick.split(" (")[0]
                                # Need to get the other team from the available options
                                return team
                            
                            # For total picks: "Team A vs Team B oX.X" or "Team A vs Team B uX.X"
                            if " vs " in pick and (" o" in pick or " u" in pick):
                                teams_part = pick.split(" o")[0].split(" u")[0]  # Remove total info
                                teams = teams_part.split(" vs ")
                                if len(teams) == 2:
                                    return tuple(sorted([teams[0].strip(), teams[1].strip()]))
                            
                            return None
                        
                        # Get all available games to help identify matchups
                        picks_data = [favorite_pick, underdog_pick, over_pick, under_pick]
                        game_matchups = set()
                        
                        # For spread picks, we need to find their opposing team
                        for pick in picks_data:
                            if pick and " vs " in pick:
                                teams_part = pick.split(" o")[0].split(" u")[0]
                                teams = teams_part.split(" vs ")
                                if len(teams) == 2:
                                    game_matchups.add(tuple(sorted([teams[0].strip(), teams[1].strip()])))
                        
                        # Now check each pick's game
                        used_games = set()
                        for pick_type, pick in [("favorite", favorite_pick), ("underdog", underdog_pick), 
                                               ("over", over_pick), ("under", under_pick)]:
                            if pick:
                                # For spread picks, find which game this team belongs to
                                if " (" in pick and pick.endswith(")"):
                                    team = pick.split(" (")[0]
                                    # Find the game this team is in
                                    found_game = None
                                    for game in game_matchups:
                                        if team in game:
                                            found_game = game
                                            break
                                    if found_game:
                                        if found_game in used_games:
                                            errors.append(f"Cannot pick multiple selections from the same game: {' vs '.join(found_game)}")
                                        else:
                                            used_games.add(found_game)
                                
                                # For total picks
                                elif " vs " in pick:
                                    game = extract_game_teams(pick)
                                    if game:
                                        if game in used_games:
                                            errors.append(f"Cannot pick multiple selections from the same game: {' vs '.join(game)}")
                                        else:
                                            used_games.add(game)
                        
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            try:
                                # Create picks data using the new system
                                picks_data = create_picks_data_from_form(
                                    favorite_pick, underdog_pick, over_pick, under_pick,
                                    super_spread, total_helper_choice, total_helper_adjustment,
                                    perfect_prediction, snapshot_games
                                )
                                
                                # Save to Firestore
                                doc_id = save_picks_to_firestore(
                                    username=st.session_state.username,
                                    week=current_week,
                                    year=current_year,
                                    picks_data=picks_data
                                )
                                
                                if doc_id:
                                    st.rerun()
                                else:
                                    st.error("Failed to save picks. Please try again.")
                                    
                            except Exception as e:
                                st.error(f"Error saving picks: {e}")
    


def main():
    """Main page entry point."""
    # Check authentication
    if not check_login():
        return
    
    # Show picks form
    show_picks_form()


if __name__ == "__main__":
    main()
