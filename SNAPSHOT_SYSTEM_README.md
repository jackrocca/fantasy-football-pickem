# 📊 Game Snapshot System

The Game Snapshot System processes raw API data into structured, human-readable game records with extracted DraftKings odds data.

## 🏗️ Architecture

```
Raw API Calls → Snapshot Processor → Game Snapshots Collection
```

- **Raw API Calls**: Unprocessed JSON responses from The Odds API
- **Snapshot Processor**: Extracts and structures relevant game data
- **Game Snapshots**: Human-readable game records with DraftKings odds

## 📋 Data Structure

### Firestore Collections

#### 1. `raw_api_calls` Collection
Contains unprocessed API responses (existing system).

#### 2. `game_snapshots` Collection  
Contains processed game data with this structure:

```json
{
  "SNAPSHOT_ID": "SeHTiQmHNdwMBde0FTtJ",
  "SNAPSHOT_CREATION_DATE": "2025-09-04T15:02:37Z",
  "TOTAL_GAMES": 272,
  "GAMES": [
    {
      "SNAPSHOT_ID": "SeHTiQmHNdwMBde0FTtJ",
      "SNAPSHOT_CREATION_DATE": "2025-09-04T15:02:37Z",
      "GAME_ID": "f1bc532dff946d15cb85654b5c4b246e",
      "GAMETIME": "2025-09-05T00:20:00Z",
      "HOME_TEAM": "Philadelphia Eagles",
      "AWAY_TEAM": "Dallas Cowboys",
      "BOOKMAKER": "DraftKings",
      "H2H_HOME": -395,
      "H2H_AWAY": 310,
      "SPREAD_POINTS_HOME": -7.5,
      "SPREAD_LINE_HOME": -120,
      "SPREAD_POINTS_AWAY": 7.5,
      "SPREAD_LINE_AWAY": 100,
      "OVER_POINTS": 48.5,
      "OVER_LINE": -112,
      "UNDER_POINTS": 48.5,
      "UNDER_LINE": -108
    }
  ]
}
```

## 📊 Field Definitions

### Basic Game Information
- **SNAPSHOT_ID**: Links back to the raw API call document
- **SNAPSHOT_CREATION_DATE**: When the snapshot was created
- **GAME_ID**: Unique identifier from The Odds API
- **GAMETIME**: Game start time (ISO format)
- **HOME_TEAM**: Home team name
- **AWAY_TEAM**: Away team name

### DraftKings Odds Data
- **BOOKMAKER**: Always "DraftKings"
- **H2H_HOME**: Home team moneyline odds (American format)
- **H2H_AWAY**: Away team moneyline odds (American format)
- **SPREAD_POINTS_HOME**: Home team point spread
- **SPREAD_LINE_HOME**: Home team spread odds
- **SPREAD_POINTS_AWAY**: Away team point spread  
- **SPREAD_LINE_AWAY**: Away team spread odds
- **OVER_POINTS**: Over/under total points
- **OVER_LINE**: Over bet odds
- **UNDER_POINTS**: Under total points (same as over)
- **UNDER_LINE**: Under bet odds

## ⚙️ Core Functions

### `extract_draftkings_odds(game_data: dict) -> dict`
Extracts DraftKings odds from a single game's API response.

### `create_game_snapshot(raw_api_doc_id: str, api_results: list) -> str`
Creates a complete game snapshot from raw API results.

### `process_raw_api_call_to_snapshot(raw_api_doc_id: str) -> str`
Processes an existing raw API call into a snapshot.

### `get_game_snapshots(limit: int = 10) -> list`
Retrieves game snapshots from Firestore.

## 🤖 Automated Processing

The system automatically creates snapshots when:

1. **GitHub Actions runs** (twice daily)
2. **Local automated collector runs**
3. **Manual API calls are made** (via the existing system)

### Automation Flow:
1. Raw API call is made and stored
2. Snapshot processor extracts DraftKings odds
3. Structured game data is stored in `game_snapshots` collection
4. Both raw and processed data are preserved

## 📈 Example Usage

### Manual Snapshot Creation
```python
from utils.odds import process_raw_api_call_to_snapshot

# Process existing raw API call
snapshot_id = process_raw_api_call_to_snapshot("raw_api_doc_id_here")
print(f"Created snapshot: {snapshot_id}")
```

### Retrieve Snapshots
```python
from utils.odds import get_game_snapshots

# Get recent snapshots
snapshots = get_game_snapshots(limit=5)
for snapshot in snapshots:
    print(f"Snapshot: {snapshot['document_id']}")
    print(f"Games: {snapshot['TOTAL_GAMES']}")
```

### Access Game Data
```python
# Get first game from snapshot
if snapshots and snapshots[0]['GAMES']:
    game = snapshots[0]['GAMES'][0]
    print(f"{game['AWAY_TEAM']} @ {game['HOME_TEAM']}")
    print(f"Spread: {game['SPREAD_POINTS_HOME']}")
    print(f"Total: {game['OVER_POINTS']}")
```

## 🎯 Benefits

✅ **Human-Readable**: Structured data vs raw JSON
✅ **DraftKings Focus**: Specifically extracts DraftKings odds
✅ **Automated**: Runs with every API collection
✅ **Queryable**: Easy to filter and analyze
✅ **Linked**: Maintains connection to raw data
✅ **Consistent**: Standardized field names and formats

## 🔍 Data Analysis Examples

### Find Games by Team
```python
snapshots = get_game_snapshots(limit=50)
cowboys_games = []

for snapshot in snapshots:
    for game in snapshot.get('GAMES', []):
        if 'Cowboys' in game.get('HOME_TEAM', '') or 'Cowboys' in game.get('AWAY_TEAM', ''):
            cowboys_games.append(game)
```

### Analyze Spread Trends
```python
# Get all games with spreads > 7 points
big_spreads = []

for snapshot in snapshots:
    for game in snapshot.get('GAMES', []):
        home_spread = abs(game.get('SPREAD_POINTS_HOME', 0))
        if home_spread > 7:
            big_spreads.append({
                'matchup': f"{game['AWAY_TEAM']} @ {game['HOME_TEAM']}",
                'spread': home_spread,
                'gametime': game['GAMETIME']
            })
```

### Compare Odds Over Time
```python
# Track how odds change for the same game
def track_game_odds(game_id):
    all_snapshots = get_game_snapshots(limit=100)
    game_history = []
    
    for snapshot in all_snapshots:
        for game in snapshot.get('GAMES', []):
            if game.get('GAME_ID') == game_id:
                game_history.append({
                    'timestamp': snapshot['SNAPSHOT_CREATION_DATE'],
                    'spread_home': game.get('SPREAD_POINTS_HOME'),
                    'total': game.get('OVER_POINTS')
                })
    
    return sorted(game_history, key=lambda x: x['timestamp'])
```

## 🚀 Future Enhancements

Potential extensions to the snapshot system:

1. **Multiple Bookmakers**: Extract odds from FanDuel, BetMGM, etc.
2. **Historical Tracking**: Track odds changes over time
3. **Alert System**: Notify when odds move significantly
4. **Analytics Dashboard**: Visualize trends and patterns
5. **Export Features**: CSV/Excel export for analysis

## 📊 Storage Considerations

- **Volume**: ~272 games per snapshot, 2 snapshots per day = ~544 games/day
- **Size**: Each game record is ~500 bytes, total ~272KB per snapshot
- **Cost**: Minimal Firestore costs for this volume
- **Retention**: Keep indefinitely for historical analysis

---

**🎯 Result**: Raw API data is now automatically processed into structured, queryable game records with DraftKings odds, ready for analysis and integration into your pick'em system!
