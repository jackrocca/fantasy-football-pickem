#!/usr/bin/env python3
"""
Setup script to initialize the Pick'em League database with sample data for testing
"""

import sqlite3
from datetime import datetime, timedelta
from data_fetcher import NFLDataFetcher

def setup_sample_data():
    """Initialize database with sample games and data"""
    
    # Initialize the database
    from app import init_database
    init_database()
    
    # Add sample games using the fallback data
    fetcher = NFLDataFetcher()
    sample_games = fetcher._get_fallback_games()
    
    if sample_games:
        count = fetcher.store_games_in_db(sample_games)
        print(f"✅ Added {count} sample games to database")
    else:
        print("❌ Failed to create sample games")
    
    # Add a few sample users for testing
    conn = sqlite3.connect('pickem_league.db')
    cursor = conn.cursor()
    
    sample_users = [
        ('testuser1', 'test1@example.com'),
        ('testuser2', 'test2@example.com'), 
        ('testuser3', 'test3@example.com')
    ]
    
    for username, email in sample_users:
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email)
            VALUES (?, ?)
        ''', (username, email))
    
    conn.commit()
    conn.close()
    
    print("✅ Database setup complete with sample data")
    print("\nNext steps:")
    print("1. Configure your OIDC provider in .streamlit/secrets.toml")
    print("2. Run: streamlit run app.py")
    print("3. Use Admin tab to update with real NFL data")

if __name__ == "__main__":
    setup_sample_data()