#!/usr/bin/env python3
"""
Cron Job Setup Script
Sets up automated cron jobs for NFL odds collection at 9AM and 9PM PST daily.
"""
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

def get_project_path():
    """Get the absolute path to the project directory."""
    return os.path.dirname(os.path.abspath(__file__))

def get_python_path():
    """Get the Python executable path from the virtual environment."""
    project_path = get_project_path()
    venv_python = os.path.join(project_path, ".venv", "bin", "python")
    
    if os.path.exists(venv_python):
        return venv_python
    else:
        # Fallback to system python
        return sys.executable

def create_cron_entries():
    """Create cron job entries for 9AM and 9PM PST daily."""
    project_path = get_project_path()
    python_path = get_python_path()
    script_path = os.path.join(project_path, "automated_odds_collector.py")
    
    # PST is UTC-8, PDT is UTC-7
    # For simplicity, we'll use UTC times that work for PST
    # 9AM PST = 5PM UTC (17:00)
    # 9PM PST = 5AM UTC next day (05:00)
    
    cron_entries = [
        # 9AM PST daily (5PM UTC)
        f"0 17 * * * {python_path} {script_path} >> {project_path}/logs/cron.log 2>&1",
        # 9PM PST daily (5AM UTC next day)  
        f"0 5 * * * {python_path} {script_path} >> {project_path}/logs/cron.log 2>&1"
    ]
    
    return cron_entries

def get_current_crontab():
    """Get the current crontab entries."""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            return []  # No crontab exists yet
    except Exception as e:
        print(f"Error reading crontab: {e}")
        return []

def update_crontab(entries):
    """Update the crontab with new entries."""
    try:
        # Write entries to a temporary file
        temp_cron_file = "/tmp/fantasy_football_cron"
        with open(temp_cron_file, 'w') as f:
            for entry in entries:
                f.write(entry + '\n')
        
        # Install the new crontab
        result = subprocess.run(['crontab', temp_cron_file], capture_output=True, text=True)
        
        # Clean up temp file
        os.remove(temp_cron_file)
        
        if result.returncode == 0:
            return True
        else:
            print(f"Error installing crontab: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error updating crontab: {e}")
        return False

def setup_log_directory():
    """Create logs directory if it doesn't exist."""
    project_path = get_project_path()
    log_dir = os.path.join(project_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    print(f"✅ Log directory ready: {log_dir}")

def main():
    """Main setup function."""
    print("🔧 Fantasy Football Pickem - Cron Job Setup")
    print("=" * 50)
    
    project_path = get_project_path()
    python_path = get_python_path()
    
    print(f"📁 Project Path: {project_path}")
    print(f"🐍 Python Path: {python_path}")
    
    # Setup log directory
    setup_log_directory()
    
    # Get current crontab
    current_entries = get_current_crontab()
    print(f"📋 Current crontab has {len(current_entries)} entries")
    
    # Create new cron entries
    new_cron_entries = create_cron_entries()
    
    # Check if our entries already exist
    fantasy_entries = [entry for entry in current_entries if "automated_odds_collector.py" in entry]
    
    if fantasy_entries:
        print(f"⚠️  Found {len(fantasy_entries)} existing fantasy football cron entries:")
        for entry in fantasy_entries:
            print(f"   {entry}")
        
        response = input("\nDo you want to replace existing entries? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Setup cancelled")
            return
        
        # Remove existing fantasy entries
        current_entries = [entry for entry in current_entries if "automated_odds_collector.py" not in entry]
    
    # Add new entries
    all_entries = current_entries + new_cron_entries
    
    print("\n📝 New cron entries to be added:")
    for entry in new_cron_entries:
        print(f"   {entry}")
    
    print(f"\n🕘 Schedule:")
    print(f"   • 9:00 AM PST daily (17:00 UTC)")
    print(f"   • 9:00 PM PST daily (05:00 UTC next day)")
    
    response = input("\nProceed with cron job installation? (y/N): ").lower().strip()
    if response != 'y':
        print("❌ Setup cancelled")
        return
    
    # Update crontab
    if update_crontab(all_entries):
        print("✅ Cron jobs installed successfully!")
        print(f"📊 Total crontab entries: {len(all_entries)}")
        
        # Test the script
        print("\n🧪 Testing the automated script...")
        script_path = os.path.join(project_path, "automated_odds_collector.py")
        
        test_response = input("Run a test execution now? (y/N): ").lower().strip()
        if test_response == 'y':
            try:
                result = subprocess.run([python_path, script_path], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print("✅ Test execution successful!")
                    print("📄 Check the logs directory for detailed output")
                else:
                    print("❌ Test execution failed!")
                    print(f"Error: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("⏱️  Test execution timed out (this might be normal for API calls)")
            except Exception as e:
                print(f"❌ Test execution error: {e}")
        
        print("\n🎉 Setup complete!")
        print("📋 To view your cron jobs: crontab -l")
        print("📄 To view logs: tail -f logs/automated_odds_collector.log")
        print("🗑️  To remove cron jobs: crontab -e (then delete the lines)")
        
    else:
        print("❌ Failed to install cron jobs")

if __name__ == "__main__":
    main()
