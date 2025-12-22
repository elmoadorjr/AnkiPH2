"""
Update checking service for AnkiPH addon
Checks for deck updates in the background and notifies users
Version: 2.1.0
"""

from aqt import mw
from aqt.utils import showInfo, tooltip
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback
import threading

from .api_client import api, AnkiPHAPIError, set_access_token
from .config import config


class UpdateChecker:
    """Handles checking for deck updates"""
    
    def __init__(self):
        self.checking = False
        self._checking_lock = threading.Lock()
    
    def should_check_updates(self) -> bool:
        """
        Determine if we should check for updates now
        
        Returns:
            True if enough time has passed since last check
        """
        if not config.is_logged_in():
            return False
        
        if not config.get_auto_check_updates():
            return False
        
        last_check = config.get_last_update_check()
        if not last_check:
            return True
        
        try:
            last_check_dt = datetime.fromisoformat(last_check)
            interval_hours = config.get_update_check_interval_hours()
            next_check = last_check_dt + timedelta(hours=interval_hours)
            
            return datetime.now() >= next_check
        except (ValueError, TypeError) as e:
            print(f"⚠ Error parsing last check timestamp: {e}")
            return True
    
    def check_for_updates(self, silent: bool = False) -> Optional[Dict]:
        """
        Check for updates on all purchased decks
        
        Args:
            silent: If True, only show notification if updates found
        
        Returns:
            Dict of updates or None if check failed
        """
        # Thread-safe check to prevent concurrent update checks
        if not self._checking_lock.acquire(blocking=False):
            print("Update check already in progress")
            return None
        
        self.checking = True
        
        try:
            # Ensure we're logged in
            if not config.is_logged_in():
                if not silent:
                    showInfo("Please login first to check for updates.")
                return None
            
            # Set access token
            token = config.get_access_token()
            set_access_token(token)
            
            if not silent:
                tooltip("Checking for deck updates...", period=2000)
            
            # Call API
            result = api.check_updates()
            
            # Update last check timestamp
            config.set_last_update_check()
            
            if not result.get('success'):
                error_msg = result.get('message', 'Failed to check updates')
                if not silent:
                    showInfo(f"Update check failed:\n{error_msg}")
                return None
            
            # Process results
            decks_with_updates = result.get('decks', [])
            
            # Build updates dict
            updates_dict = {}
            for deck_update in decks_with_updates:
                deck_id = deck_update.get('deck_id')
                has_update = deck_update.get('has_update', False)
                
                if has_update:
                    updates_dict[deck_id] = {
                        'deck_id': deck_id,
                        'current_version': deck_update.get('current_version'),
                        'latest_version': deck_update.get('latest_version'),
                        'has_update': True,
                        'update_type': deck_update.get('update_type', 'minor'),
                        'changelog_summary': deck_update.get('changelog_summary', 'Updates available'),
                        'checked_at': datetime.now().isoformat()
                    }
            
            # Save to config
            config.save_available_updates(updates_dict)
            
            # Show notification
            update_count = len(updates_dict)
            if update_count > 0:
                if update_count == 1:
                    msg = "1 deck update available!"
                else:
                    msg = f"{update_count} deck updates available!"
                
                tooltip(msg, period=3000)
                
                # Show detailed info if not silent
                if not silent:
                    self._show_update_summary(updates_dict)
            else:
                if not silent:
                    tooltip("All decks are up to date! ✓", period=2000)
            
            print(f"✓ Update check complete: {update_count} update(s) available")
            
            return updates_dict
        
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Session expired. Please login again."
                config.clear_tokens()
            
            print(f"✗ Update check failed: {error_msg}")
            
            if not silent:
                showInfo(f"Failed to check for updates:\n{error_msg}")
            
            return None
        
        except Exception as e:
            print(f"✗ Update check error: {e}")
            print(traceback.format_exc())
            
            if not silent:
                showInfo(f"Update check failed:\n{str(e)}")
            
            return None
        
        finally:
            self.checking = False
            self._checking_lock.release()
    
    def _show_update_summary(self, updates_dict: Dict):
        """
        Show a summary of available updates
        
        Args:
            updates_dict: Dict of deck updates
        """
        if not updates_dict:
            return
        
        # Build message
        lines = ["Available Updates:\n"]
        
        for deck_id, update_info in updates_dict.items():
            current = update_info.get('current_version', 'Unknown')
            latest = update_info.get('latest_version', 'Unknown')
            summary = update_info.get('changelog_summary', '')
            
            # Try to get deck name from downloaded decks
            downloaded = config.get_downloaded_decks()
            deck_name = "Unknown Deck"
            
            if deck_id in downloaded:
                # We don't have the name in config, just use ID
                deck_name = f"Deck {deck_id[:8]}"
            
            lines.append(f"• {deck_name}")
            lines.append(f"  {current} → {latest}")
            if summary:
                lines.append(f"  {summary}")
            lines.append("")
        
        lines.append("Open AnkiPH to update your decks.")
        
        showInfo("\n".join(lines))
    
    def get_update_info(self, deck_id: str) -> Optional[Dict]:
        """
        Get update info for a specific deck
        
        Args:
            deck_id: The deck ID
        
        Returns:
            Update info dict or None
        """
        updates = config.get_available_updates()
        return updates.get(str(deck_id))
    
    def has_updates_available(self) -> bool:
        """
        Check if any decks have updates available
        
        Returns:
            True if updates are available
        """
        updates = config.get_available_updates()
        return len(updates) > 0
    
    def get_update_count(self) -> int:
        """
        Get count of decks with updates available
        
        Returns:
            Number of decks with updates
        """
        updates = config.get_available_updates()
        return len(updates)
    
    def clear_update(self, deck_id: str):
        """
        Clear update notification for a deck (after updating)
        
        Args:
            deck_id: The deck ID
        """
        config.clear_update_for_deck(deck_id)
        print(f"✓ Cleared update notification for deck {deck_id}")
    
    def get_changelog(self, deck_id: str) -> Optional[List[Dict]]:
        """
        Get full changelog for a deck
        
        Args:
            deck_id: The deck ID
        
        Returns:
            List of version history entries or None
        """
        try:
            # Ensure we're logged in
            if not config.is_logged_in():
                return None
            
            # Set access token
            token = config.get_access_token()
            set_access_token(token)
            
            # Call API
            result = api.get_changelog(deck_id)
            
            if result.get('success'):
                return result.get('changelog', [])
            
            return None
        
        except Exception as e:
            print(f"✗ Failed to get changelog for {deck_id}: {e}")
            return None
    
    def auto_check_if_needed(self):
        """Automatically check for updates if needed (called on startup)"""
        if not self.should_check_updates():
            return
        
        print("Auto-checking for updates...")
        
        # Check silently in background
        try:
            self.check_for_updates(silent=True)
        except Exception as e:
            print(f"✗ Auto-update check failed (non-critical): {e}")
    
    def auto_apply_updates(self):
        """
        Automatically download and apply all available updates.
        Called on startup for hands-off sync experience.
        """
        updates = config.get_available_updates()
        
        if not updates:
            print("No updates to auto-apply")
            return
        
        print(f"Auto-applying {len(updates)} update(s)...")
        
        # Import here to avoid circular import
        from .deck_importer import import_deck
        
        success_count = 0
        fail_count = 0
        
        for deck_id, update_info in updates.items():
            try:
                # Get download URL
                result = api.download_deck(deck_id)
                
                if not result.get('success'):
                    print(f"✗ Failed to get download URL for {deck_id}")
                    fail_count += 1
                    continue
                
                download_url = result.get('download_url')
                if not download_url:
                    print(f"✗ No download URL for {deck_id}")
                    fail_count += 1
                    continue
                
                # Download the deck file
                deck_content = api.download_deck_file(download_url)
                
                if not deck_content:
                    print(f"✗ Failed to download deck file for {deck_id}")
                    fail_count += 1
                    continue
                
                # Import the deck (synchronous for background operation)
                anki_deck_id = import_deck(deck_content, f"Update_{deck_id[:8]}")
                
                # Update tracking
                new_version = update_info.get('latest_version', 'Unknown')
                config.save_downloaded_deck(deck_id, new_version, anki_deck_id)
                
                # Clear the update notification
                self.clear_update(deck_id)
                
                print(f"✓ Auto-updated deck {deck_id} to v{new_version}")
                success_count += 1
                
            except Exception as e:
                print(f"✗ Failed to auto-update deck {deck_id}: {e}")
                fail_count += 1
                continue
        
        # Show summary
        if success_count > 0:
            tooltip(f"\u2696\ufe0f AnkiPH: Updated {success_count} deck(s)", period=3000)
        
        if fail_count > 0:
            print(f"⚠ {fail_count} deck(s) failed to auto-update")


# Global update checker instance
update_checker = UpdateChecker()
