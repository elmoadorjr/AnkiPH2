"""
Progress syncing for the AnkiPH addon
Syncs study progress to the server
Updated for v3.0 API with improved field names and single-deck support
Version: 3.0.0
"""

from aqt import mw
from datetime import datetime, timedelta
from .api_client import api, AnkiPHAPIError, set_access_token
from .config import config
from .deck_importer import get_deck_stats, deck_exists


def get_progress_data() -> list:
    """
    Get progress data for all downloaded AnkiPH decks
    
    Returns:
        List of progress data dictionaries
    """
    downloaded_decks = config.get_downloaded_decks()
    progress_data = []
    decks_to_remove = []
    
    print(f"Checking progress for {len(downloaded_decks)} tracked deck(s)...")
    
    for deck_id, deck_info in downloaded_decks.items():
        anki_deck_id = deck_info.get('anki_deck_id')
        
        if not anki_deck_id:
            print(f"⚠ Deck {deck_id} has no Anki ID, skipping...")
            continue
        
        # Check if deck still exists in Anki
        if not deck_exists(anki_deck_id):
            print(f"⚠ Deck {deck_id} (Anki ID: {anki_deck_id}) no longer exists, marking for removal...")
            decks_to_remove.append(deck_id)
            continue
        
        try:
            # Get deck statistics
            stats = get_deck_stats(anki_deck_id)
            
            if not stats:
                print(f"⚠ No stats for deck {deck_id}, using defaults...")
                stats = {
                    'total_cards': 0,
                    'new_cards': 0,
                    'learning_cards': 0,
                    'review_cards': 0
                }
            
            # Get review statistics from the last 30 days
            review_stats = get_review_stats_for_deck(anki_deck_id, days=30)
            
            # Calculate retention rate
            retention_rate = calculate_retention_rate(anki_deck_id)
            
            # Calculate current streak
            current_streak = calculate_current_streak(anki_deck_id)
            
            # Build progress data (v3.0 format)
            progress = {
                'deck_id': deck_id,
                'progress': {
                    'total_cards_studied': review_stats.get('total_reviews', 0),
                    'cards_due_today': stats.get('new_cards', 0) + stats.get('learning_cards', 0),
                    'retention_rate': retention_rate,
                    'study_time_minutes': review_stats.get('study_time_minutes', 0),
                    'mature_cards': stats.get('review_cards', 0),
                    'young_cards': stats.get('learning_cards', 0),
                    'learning_cards': stats.get('learning_cards', 0),
                    'avg_ease_factor': review_stats.get('average_ease', 0) / 1000 if review_stats.get('average_ease', 0) > 10 else review_stats.get('average_ease', 0),
                    'current_streak_days': current_streak,
                    'total_reviews_today': review_stats.get('total_reviews_today', 0)
                }
            }
            
            progress_data.append(progress)
            print(f"OK Prepared progress data for deck {deck_id}")
            
        except Exception as e:
            print(f"X Error processing deck {deck_id}: {e}")
            continue
    
    # Clean up decks that no longer exist
    for deck_id in decks_to_remove:
        config.remove_downloaded_deck(deck_id)
        print(f"OK Removed non-existent deck {deck_id} from tracking")
    
    return progress_data


def calculate_retention_rate(deck_id: int) -> float:
    """
    Calculate retention rate for a deck based on review performance
    
    Args:
        deck_id: Anki deck ID
    
    Returns:
        Retention rate as percentage (0-100)
    """
    try:
        if not mw.col or not deck_exists(deck_id):
            return 0.0
        
        # Look at reviews from last 30 days
        cutoff_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        
        # Get card IDs for this deck
        card_ids = mw.col.decks.cids(deck_id, children=True)
        
        if not card_ids:
            return 0.0
        
        # Ensure all IDs are valid integers
        valid_card_ids = [int(cid) for cid in card_ids if cid]
        if not valid_card_ids:
            return 0.0
        
        # Use parameterized query with placeholders (prevent SQL injection)
        placeholders = ",".join("?" * len(valid_card_ids))
        
        # Query review log with parameterized values
        query = f"""
            SELECT 
                COUNT(*) as total_reviews,
                SUM(CASE WHEN ease >= 2 THEN 1 ELSE 0 END) as correct_reviews
            FROM revlog
            WHERE cid IN ({placeholders})
            AND id >= ?
        """
        
        result = mw.col.db.first(query, *valid_card_ids, cutoff_time)
        
        if not result or result[0] == 0:
            return 0.0
        
        total_reviews = result[0]
        correct_reviews = result[1] or 0
        
        # Calculate percentage
        retention_rate = (correct_reviews / total_reviews) * 100
        
        return round(retention_rate, 2)
    
    except Exception as e:
        print(f"✗ Error calculating retention rate for deck {deck_id}: {e}")
        return 0.0


def calculate_current_streak(deck_id: int) -> int:
    """
    Calculate the current study streak for a deck
    
    Args:
        deck_id: Anki deck ID
    
    Returns:
        Number of consecutive days studied
    """
    try:
        if not mw.col or not deck_exists(deck_id):
            return 0
        
        # Get card IDs for this deck
        card_ids = mw.col.decks.cids(deck_id, children=True)
        
        if not card_ids:
            return 0
        
        # Ensure all IDs are valid integers
        valid_card_ids = [int(cid) for cid in card_ids if cid]
        if not valid_card_ids:
            return 0
        
        # Use parameterized query with placeholders (prevent SQL injection)
        placeholders = ",".join("?" * len(valid_card_ids))
        
        # Get distinct review dates
        query = f"""
            SELECT DISTINCT DATE(id / 1000, 'unixepoch', 'localtime') as review_date
            FROM revlog
            WHERE cid IN ({placeholders})
            ORDER BY review_date DESC
        """
        
        review_dates = mw.col.db.list(query, *valid_card_ids)
        
        if not review_dates:
            return 0
        
        # Parse dates
        parsed_dates = []
        for date_str in review_dates:
            try:
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                parsed_dates.append(parsed_date)
            except ValueError as e:
                print(f"⚠ Error parsing date '{date_str}': {e}")
                continue
        
        if not parsed_dates:
            return 0
        
        # Check if streak is current
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Streak must include today or yesterday
        if parsed_dates[0] != today and parsed_dates[0] != yesterday:
            return 0
        
        # Count consecutive days
        streak_days = 0
        expected_date = today
        
        for review_date in parsed_dates:
            if review_date == expected_date or review_date == expected_date - timedelta(days=1):
                streak_days += 1
                expected_date = review_date - timedelta(days=1)
            else:
                break
        
        return streak_days
    
    except Exception as e:
        print(f"✗ Error calculating streak for deck {deck_id}: {e}")
        return 0


def get_review_stats_for_deck(deck_id: int, days: int = 30) -> dict:
    """
    Get review statistics for a deck from the review history
    
    Args:
        deck_id: Anki deck ID
        days: Number of days to look back
    
    Returns:
        Dictionary with review statistics including total_reviews_today
    """
    try:
        if not mw.col or not deck_exists(deck_id):
            return {}
        
        # Calculate cutoff timestamp
        cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        # Calculate today's cutoff (start of today)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_cutoff = int(today_start.timestamp() * 1000)
        
        # Get card IDs for this deck
        card_ids = mw.col.decks.cids(deck_id, children=True)
        
        if not card_ids:
            return {}
        
        # Ensure all IDs are valid integers
        valid_card_ids = [int(cid) for cid in card_ids if cid]
        if not valid_card_ids:
            return {}
        
        # Use parameterized query with placeholders (prevent SQL injection)
        placeholders = ",".join("?" * len(valid_card_ids))
        
        # Query review log with parameterized values
        query = f"""
            SELECT 
                COUNT(*) as total_reviews,
                SUM(CASE WHEN type = 0 THEN 1 ELSE 0 END) as new_cards,
                AVG(ease) as average_ease,
                SUM(time) / 60000 as study_time_minutes,
                MAX(id) as last_review_id
            FROM revlog
            WHERE cid IN ({placeholders})
            AND id >= ?
        """
        
        result = mw.col.db.first(query, *valid_card_ids, cutoff_time)
        
        # Query for today's reviews
        today_query = f"""
            SELECT COUNT(*) as today_reviews
            FROM revlog
            WHERE cid IN ({placeholders})
            AND id >= ?
        """
        today_result = mw.col.db.first(today_query, *valid_card_ids, today_cutoff)
        
        if not result:
            return {}
        
        # Parse last study date
        last_study_date = None
        if result[4]:
            try:
                last_study_date = datetime.fromtimestamp(result[4] / 1000).isoformat()
            except (ValueError, OSError) as e:
                print(f"Warning: Error converting timestamp {result[4]}: {e}")
        
        return {
            'total_reviews': result[0] or 0,
            'new_cards': result[1] or 0,
            'average_ease': round(result[2] or 0, 2),
            'study_time_minutes': round(result[3] or 0, 2),
            'last_study_date': last_study_date,
            'total_reviews_today': today_result[0] if today_result else 0
        }
        
    except Exception as e:
        print(f"X Error getting review stats for deck {deck_id}: {e}")
        return {}


def clean_deleted_decks():
    """
    Remove tracking for decks that no longer exist in Anki
    
    Returns:
        Number of decks removed
    """
    downloaded_decks = config.get_downloaded_decks()
    decks_to_remove = []
    
    for deck_id, deck_info in downloaded_decks.items():
        anki_deck_id = deck_info.get('anki_deck_id')
        
        if not anki_deck_id:
            decks_to_remove.append(deck_id)
            continue
        
        if not deck_exists(anki_deck_id):
            decks_to_remove.append(deck_id)
            print(f"⚠ Deck {deck_id} (Anki ID: {anki_deck_id}) marked for cleanup")
    
    # Remove tracked decks
    for deck_id in decks_to_remove:
        config.remove_downloaded_deck(deck_id)
        print(f"✓ Removed deck {deck_id} from tracking")
    
    return len(decks_to_remove)


def clean_deleted_backend_decks():
    """
    Verify all tracked decks still exist on the server.
    Removes tracking for decks that have been deleted from the backend.
    
    Returns:
        Number of decks removed
    """
    if not config.is_logged_in():
        return 0
    
    downloaded_decks = config.get_downloaded_decks()
    if not downloaded_decks:
        return 0
    
    # Set access token
    token = config.get_access_token()
    if not token:
        return 0
    
    set_access_token(token)
    
    try:
        # Get user's subscriptions from server
        result = api.browse_decks(category="subscribed")
        
        if not result.get('success') and 'decks' not in result:
            print("⚠ Could not verify decks with server")
            return 0
        
        server_decks = result.get('decks', [])
        server_deck_ids = {deck.get('id') for deck in server_decks}
        
        # Find decks in local config that no longer exist on server
        decks_to_remove = []
        for deck_id in downloaded_decks.keys():
            if deck_id not in server_deck_ids:
                print(f"⚠ Deck {deck_id} not found on server, marking for cleanup")
                decks_to_remove.append(deck_id)
        
        # Remove stale entries
        for deck_id in decks_to_remove:
            config.remove_downloaded_deck(deck_id)
            print(f"✓ Removed server-deleted deck {deck_id} from local config")
        
        return len(decks_to_remove)
    
    except Exception as e:
        print(f"⚠ Backend deck cleanup check failed (non-critical): {e}")
        return 0


def sync_progress():
    """
    Sync progress for all downloaded decks to the server
    
    Raises:
        Exception: If sync fails
    """
    if not mw.col:
        raise Exception("Anki collection not available. Please try again.")
    
    if not config.is_logged_in():
        raise Exception("Not logged in. Please login first.")
    
    # FIXED: Set access token BEFORE making API calls
    token = config.get_access_token()
    if not token:
        raise Exception("No access token found. Please login again.")
    
    set_access_token(token)
    print(f"✓ Access token set for sync")
    
    try:
        # Clean up deleted decks first (local Anki check)
        cleaned = clean_deleted_decks()
        if cleaned > 0:
            print(f"✓ Cleaned up {cleaned} deleted deck(s) from tracking")
        
        # Also clean up decks deleted from backend
        backend_cleaned = clean_deleted_backend_decks()
        if backend_cleaned > 0:
            print(f"✓ Cleaned up {backend_cleaned} server-deleted deck(s) from tracking")
        
        # Get progress data
        progress_data = get_progress_data()
        
        if not progress_data:
            print("ℹ No decks to sync")
            return {
                'success': True,
                'message': 'No decks to sync',
                'synced_count': 0
            }
        
        print(f"Syncing progress for {len(progress_data)} deck(s)...")
        
        # Sync each deck individually using v3.0 format
        success_count = 0
        fail_count = 0
        last_result = None
        
        for deck_progress in progress_data:
            try:
                result = api.sync_progress(
                    deck_id=deck_progress['deck_id'],
                    progress=deck_progress['progress']
                )
                if result and result.get('success'):
                    success_count += 1
                    last_result = result
                else:
                    fail_count += 1
                    print(f"⚠ Sync returned: {result}")
            except Exception as e:
                fail_count += 1
                print(f"✗ Failed to sync deck {deck_progress.get('deck_id', 'unknown')}: {e}")
        
        print(f"✓ Progress synced: {success_count} succeeded, {fail_count} failed")
        
        return last_result or {'success': success_count > 0, 'synced_count': success_count}
    
    except AnkiPHAPIError as e:
        if e.status_code == 401:
            print(f"✗ Sync failed: Session expired")
            config.clear_tokens()  # Clear expired tokens
            raise Exception("Session expired. Please login again.")
        else:
            print(f"✗ Sync failed: {e}")
            raise Exception(f"Sync failed: {str(e)}")
    
    except Exception as e:
        print(f"✗ Sync progress error: {e}")
        raise


def should_auto_sync() -> bool:
    """
    Check if we should automatically sync progress
    
    Returns:
        True if auto-sync should happen
    """
    if not config.is_logged_in():
        return False
    
    if not mw.col:
        return False
    
    # Check if auto-sync is enabled
    if not config.get_auto_sync_enabled():
        return False
    
    return True


def auto_sync_if_needed():
    """Automatically sync progress if needed"""
    if not should_auto_sync():
        return
    
    try:
        sync_progress()
        print("OK Auto-sync completed")
    except Exception as e:
        print(f"X Auto-sync failed (non-critical): {e}")


def sync_deck_progress(deck_id: str) -> dict:
    """
    Sync progress for a single deck (v3.0 API format)
    
    Args:
        deck_id: The deck UUID (from AnkiPH server)
    
    Returns:
        API response dict
    
    Raises:
        Exception: If sync fails
    """
    if not mw.col:
        raise Exception("Anki collection not available. Please try again.")
    
    if not config.is_logged_in():
        raise Exception("Not logged in. Please login first.")
    
    # Set access token
    token = config.get_access_token()
    if not token:
        raise Exception("No access token found. Please login again.")
    
    set_access_token(token)
    
    # Get deck info
    downloaded_decks = config.get_downloaded_decks()
    deck_info = downloaded_decks.get(deck_id)
    
    if not deck_info:
        raise Exception(f"Deck {deck_id} not found in downloaded decks")
    
    anki_deck_id = deck_info.get('anki_deck_id')
    if not anki_deck_id or not deck_exists(anki_deck_id):
        raise Exception(f"Anki deck not found for {deck_id}")
    
    # Get statistics
    stats = get_deck_stats(anki_deck_id)
    review_stats = get_review_stats_for_deck(anki_deck_id, days=30)
    retention_rate = calculate_retention_rate(anki_deck_id)
    current_streak = calculate_current_streak(anki_deck_id)
    
    # Build v3.0 format progress data
    progress_data = {
        'total_cards_studied': review_stats.get('total_reviews', 0),
        'cards_due_today': stats.get('new_cards', 0) + stats.get('learning_cards', 0),
        'retention_rate': retention_rate,
        'study_time_minutes': review_stats.get('study_time_minutes', 0),
        'mature_cards': stats.get('review_cards', 0),
        'young_cards': stats.get('learning_cards', 0),
        'learning_cards': stats.get('learning_cards', 0),
        'avg_ease_factor': review_stats.get('average_ease', 0) / 1000 if review_stats.get('average_ease', 0) > 10 else review_stats.get('average_ease', 0),
        'current_streak_days': current_streak,
        'total_reviews_today': review_stats.get('total_reviews_today', 0)
    }
    
    try:
        # Use v3.0 single-deck format
        result = api.post("/addon-sync-progress", json_body={
            "deck_id": deck_id,
            "progress": progress_data
        })
        
        if result and result.get('success'):
            print(f"OK Synced progress for deck {deck_id}")
        
        return result
        
    except AnkiPHAPIError as e:
        if e.status_code == 401:
            config.clear_tokens()
            raise Exception("Session expired. Please login again.")
        raise Exception(f"Sync failed: {str(e)}")

