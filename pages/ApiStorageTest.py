"""
Test page for the new Raw API Storage system.
This page allows you to test different Odds API endpoints and view stored raw data.
"""
import streamlit as st
import json
from utils.odds import (
    fetch_sports_from_api,
    fetch_odds_from_api, 
    fetch_events_from_api,
    fetch_scores_from_api,
    get_raw_api_calls
)

st.set_page_config(page_title="API Storage Test", page_icon="🔧")

st.title("🔧 Raw API Storage Test")
st.write("Test the new raw API storage system that preserves all API calls to Firestore.")

# Create tabs for different functionalities
tab1, tab2, tab3, tab4 = st.tabs(["🔄 Test API Calls", "📊 View Stored Data", "🤖 GitHub Actions", "📈 API Usage Stats"])

with tab1:
    st.header("Test API Endpoints")
    st.write("Test different Odds API endpoints and see them stored in Firestore.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏈 Test NFL Odds API", type="primary"):
            with st.spinner("Calling NFL Odds API..."):
                try:
                    odds_data, doc_id = fetch_odds_from_api()
                    st.success(f"✅ API call successful! Stored with ID: `{doc_id}`")
                    
                    # Show a preview of the data
                    if isinstance(odds_data, list) and len(odds_data) > 0:
                        st.write(f"📊 Retrieved {len(odds_data)} games")
                        with st.expander("Preview first game data"):
                            st.json(odds_data[0])
                    elif isinstance(odds_data, dict) and odds_data.get("mock_data"):
                        st.info("🎭 Using mock data (no API key configured)")
                    else:
                        st.write("📊 Data retrieved")
                        with st.expander("Preview data"):
                            st.json(odds_data)
                            
                except Exception as e:
                    st.error(f"❌ API call failed: {str(e)}")
        
        if st.button("🏟️ Test Sports API"):
            with st.spinner("Calling Sports API..."):
                try:
                    sports_data, doc_id = fetch_sports_from_api()
                    st.success(f"✅ Sports API call successful! Stored with ID: `{doc_id}`")
                    
                    if isinstance(sports_data, dict) and sports_data.get("mock_data"):
                        st.info("🎭 Using mock data (no API key configured)")
                    else:
                        with st.expander("Preview sports data"):
                            st.json(sports_data)
                            
                except Exception as e:
                    st.error(f"❌ Sports API call failed: {str(e)}")
    
    with col2:
        if st.button("🎯 Test Events API"):
            with st.spinner("Calling Events API..."):
                try:
                    events_data, doc_id = fetch_events_from_api()
                    st.success(f"✅ Events API call successful! Stored with ID: `{doc_id}`")
                    
                    if isinstance(events_data, dict) and events_data.get("mock_data"):
                        st.info("🎭 Using mock data (no API key configured)")
                    else:
                        with st.expander("Preview events data"):
                            st.json(events_data)
                            
                except Exception as e:
                    st.error(f"❌ Events API call failed: {str(e)}")
        
        if st.button("📊 Test Scores API"):
            with st.spinner("Calling Scores API..."):
                try:
                    scores_data, doc_id = fetch_scores_from_api()
                    st.success(f"✅ Scores API call successful! Stored with ID: `{doc_id}`")
                    
                    if isinstance(scores_data, dict) and scores_data.get("mock_data"):
                        st.info("🎭 Using mock data (no API key configured)")
                    else:
                        with st.expander("Preview scores data"):
                            st.json(scores_data)
                            
                except Exception as e:
                    st.error(f"❌ Scores API call failed: {str(e)}")

with tab2:
    st.header("View Stored Raw API Data")
    st.write("Browse the raw API calls stored in Firestore.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Filter options
        api_type_filter = st.selectbox(
            "Filter by API Type:",
            ["All", "GET_ODDS", "GITHUB_ACTIONS_GET_ODDS", "AUTOMATED_GET_ODDS", "GET_SPORTS", "GET_EVENTS", "GET_SCORES", "MOCK_ODDS", "ERROR_ODDS"],
            index=0
        )
        
        limit = st.number_input("Number of records:", min_value=1, max_value=50, value=10)
        
        if st.button("🔄 Refresh Data", type="primary"):
            st.rerun()
    
    with col2:
        # Fetch and display stored data
        filter_type = None if api_type_filter == "All" else api_type_filter
        
        with st.spinner("Loading stored API calls..."):
            try:
                raw_calls = get_raw_api_calls(api_type=filter_type, limit=limit)
                
                if raw_calls:
                    st.success(f"📊 Found {len(raw_calls)} stored API calls")
                    
                    for i, call in enumerate(raw_calls):
                        with st.expander(f"🔍 {call.get('API_TYPE', 'Unknown')} - {call.get('API_TIMESTAMP', 'No timestamp')[:19]}"):
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.write("**Document ID:**", call.get('document_id', 'N/A'))
                                st.write("**API Type:**", call.get('API_TYPE', 'N/A'))
                                st.write("**Timestamp:**", call.get('API_TIMESTAMP', 'N/A'))
                            
                            with col_b:
                                st.write("**Parameters:**")
                                st.json(call.get('API_PARAMETERS', {}))
                            
                            st.write("**Raw Results:**")
                            results = call.get('API_RESULTS', {})
                            if isinstance(results, list) and len(results) > 0:
                                st.write(f"Array with {len(results)} items")
                                with st.expander("View first item"):
                                    st.json(results[0])
                            else:
                                st.json(results)
                else:
                    st.info("📭 No stored API calls found")
                    
            except Exception as e:
                st.error(f"❌ Failed to load stored data: {str(e)}")

with tab3:
    st.header("🤖 GitHub Actions Automation")
    st.write("Monitor automated NFL odds collection running on GitHub Actions.")
    
    # Show GitHub Actions specific data
    try:
        github_actions_calls = get_raw_api_calls(api_type="GITHUB_ACTIONS_GET_ODDS", limit=20)
        
        if github_actions_calls:
            st.success(f"🤖 Found {len(github_actions_calls)} GitHub Actions collections")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Recent Collections")
                for call in github_actions_calls[:5]:
                    timestamp = call.get('API_TIMESTAMP', 'Unknown')[:19]
                    games_count = call.get('GAMES_COUNT', 'Unknown')
                    
                    with st.expander(f"🕐 {timestamp} - {games_count} games"):
                        st.write(f"**Document ID:** `{call.get('document_id', 'N/A')}`")
                        st.write(f"**Games Count:** {games_count}")
                        st.write(f"**Source:** {call.get('AUTOMATION_SOURCE', 'N/A')}")
                        
                        if st.button(f"View Raw Data", key=f"view_{call.get('document_id')}"):
                            st.json(call.get('API_RESULTS', {}))
            
            with col2:
                st.subheader("📅 Automation Status")
                
                if github_actions_calls:
                    latest = github_actions_calls[0]
                    latest_time = latest.get('API_TIMESTAMP', 'Unknown')
                    latest_count = latest.get('GAMES_COUNT', 0)
                    
                    st.metric("Last Collection", latest_time[:19])
                    st.metric("Games in Last Run", latest_count)
                    
                    # Show collection frequency
                    if len(github_actions_calls) >= 2:
                        from datetime import datetime
                        try:
                            latest_dt = datetime.fromisoformat(latest_time.replace('Z', '+00:00'))
                            previous_dt = datetime.fromisoformat(github_actions_calls[1].get('API_TIMESTAMP', '').replace('Z', '+00:00'))
                            hours_between = (latest_dt - previous_dt).total_seconds() / 3600
                            st.metric("Hours Since Previous", f"{hours_between:.1f}")
                        except:
                            st.metric("Hours Since Previous", "Unknown")
                
                st.subheader("🔗 GitHub Actions")
                st.write("**Repository:** Your GitHub repository")
                st.write("**Schedule:** 9AM & 9PM PST daily")
                st.write("**Workflow:** `collect-nfl-odds.yml`")
                
                st.info("💡 **Tip:** Check your GitHub repository's Actions tab to see workflow runs and logs.")
        
        else:
            st.info("🤖 No GitHub Actions collections found yet.")
            st.write("**Next Steps:**")
            st.write("1. Push your code to GitHub")
            st.write("2. Set up GitHub secrets (ODDS_API_KEY, GCP_SERVICE_ACCOUNT_KEY)")
            st.write("3. Enable GitHub Actions")
            st.write("4. Test with 'Run workflow' button")
            
            st.write("**Expected Schedule:**")
            st.write("- 9:00 AM PST (17:00 UTC)")
            st.write("- 9:00 PM PST (05:00 UTC)")
    
    except Exception as e:
        st.error(f"❌ Failed to load GitHub Actions data: {str(e)}")

with tab4:
    st.header("API Usage Statistics")
    st.write("Overview of your API usage and stored data.")
    
    try:
        # Get all raw calls for stats
        all_calls = get_raw_api_calls(limit=100)
        
        if all_calls:
            # Count by API type
            api_counts = {}
            for call in all_calls:
                api_type = call.get('API_TYPE', 'Unknown')
                api_counts[api_type] = api_counts.get(api_type, 0) + 1
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 API Calls by Type")
                for api_type, count in sorted(api_counts.items()):
                    st.metric(api_type, count)
            
            with col2:
                st.subheader("📈 Recent Activity")
                st.write(f"Total stored calls: **{len(all_calls)}**")
                
                if all_calls:
                    latest_call = all_calls[0]
                    st.write(f"Latest call: **{latest_call.get('API_TYPE', 'Unknown')}**")
                    st.write(f"Last activity: **{latest_call.get('API_TIMESTAMP', 'N/A')[:19]}**")
        else:
            st.info("📭 No API calls stored yet. Try making some API calls in the first tab!")
            
    except Exception as e:
        st.error(f"❌ Failed to load statistics: {str(e)}")

st.divider()
st.info("💡 **Tip:** Every API call made through this system is automatically stored in Firestore with full request parameters and raw responses, ensuring you never lose valuable API data!")
