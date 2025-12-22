"""
Configuration management for the AnkiPH addon
FIXED: Profile-specific deck tracking using collection metadata
ENHANCED: Added update checking, notification tracking, and sync state management
ENHANCED: Added subscription-only access support (subscriber, free tier)
Version: 3.2.0
"""

from aqt import mw
from datetime import datetime
import json


class Config:
    """Manages addon configuration and authentication state"""
    
    def __init__(self):
        self.addon_name = "AnkiPH_Addon"
        self._config_cache = None
        self._cache_timestamp = 0
        self._cache_timeout = 1.0  # 1 second cache
        
    def _get_config(self):
        """Get the addon config from Anki with caching"""
        try:
            # Use cache if less than timeout seconds old
            current_time = datetime.now().timestamp()
            if self._config_cache and (current_time - self._cache_timestamp) < self._cache_timeout:
                return self._config_cache
            
            # Get config from Anki
            config = mw.addonManager.getConfig(self.addon_name)
            
            if config is None:
                print(f"⚠ Config is None for {self.addon_name}, using defaults")
                config = self._get_default_config()
                # Save default config
                self._save_config(config)
            
            # Ensure all required keys exist
            default = self._get_default_config()
            for key, value in default.items():
                if key not in config:
                    config[key] = value
            
            # === v1.1.0 MIGRATION ===
            # Force tabbed UI for existing users (one-time migration)
            migration_needed = False
            if 'ui_mode' in config:
                if config.get('ui_mode') == 'minimal':
                    if not config.get('migrated_to_v1_1_0', False):
                        print("⚡ Migrating to v1.1.0: Switching to tabbed UI")
                        config['ui_mode'] = 'tabbed'
                        config['migrated_to_v1_1_0'] = True
                        migration_needed = True
            
            # Save if migration happened
            if migration_needed:
                self._save_config(config)
            # === END MIGRATION ===
            
            # Update cache
            self._config_cache = config
            self._cache_timestamp = current_time
            
            return config
            
        except Exception as e:
            print(f"✗ Error reading config for {self.addon_name}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Get the default configuration"""
        return {
            "api_url": "https://ladvckxztcleljbiomcf.supabase.co/functions/v1",
            "auto_sync_enabled": True,
            "auto_sync_interval_hours": 1,
            # NOTE: downloaded_decks removed from global config - now profile-specific
            "access_token": None,
            "refresh_token": None,
            "expires_at": None,
            "user": None,
            "is_admin": False,
            # Subscription access fields (v3.2 - subscription-only model)
            "has_subscription": False,
            "subscription_expires_at": None,
            "subscription_tier": "free",
            "is_lifetime": False,
            # Collaborative deck creation fields (v3.1)
            "can_create_decks": False,
            "created_decks_count": 0,
            "max_decks_allowed": 0,
            "ui_mode": "tabbed",
            "last_notification_check": None,
            "unread_notification_count": 0,
            "last_update_check": None,
            "auto_check_updates": True,
            "update_check_interval_hours": 24,
            "available_updates": {},
            "sync_state": {},
            "protected_fields": {},
            "migrated_to_v1_1_0": False
        }
    
    def _save_config(self, data):
        """Save the addon config to Anki"""
        try:
            # Make a deep copy to avoid reference issues
            data_to_save = json.loads(json.dumps(data, default=str))
            
            # Write to Anki
            mw.addonManager.writeConfig(self.addon_name, data_to_save)
            
            # Invalidate cache after save
            self._config_cache = None
            self._cache_timestamp = 0
            
            return True
            
        except Exception as e:
            print(f"✗ ERROR: Failed to save config: {e}")
            self._config_cache = None
            self._cache_timestamp = 0
            return False
    
    def _invalidate_cache(self):
        """Invalidate the config cache"""
        self._config_cache = None
        self._cache_timestamp = 0
    
    # === PROFILE-SPECIFIC METADATA STORAGE ===
    
    def _get_profile_meta(self, key: str, default=None):
        """Get profile-specific metadata from collection"""
        if not mw.col:
            return default
        
        try:
            meta_key = f"ankiph_{key}"
            value = mw.col.get_config(meta_key, default)
            return value
        except Exception as e:
            print(f"✗ Error reading profile meta '{key}': {e}")
            return default
    
    def _set_profile_meta(self, key: str, value):
        """Set profile-specific metadata in collection"""
        if not mw.col:
            print(f"✗ Cannot save profile meta '{key}': no collection")
            return False
        
        try:
            meta_key = f"ankiph_{key}"
            mw.col.set_config(meta_key, value)
            return True
        except Exception as e:
            print(f"✗ Error saving profile meta '{key}': {e}")
            return False
    
    # === AUTHENTICATION ===
    
    def save_tokens(self, access_token, refresh_token, expires_at):
        """Save authentication tokens"""
        cfg = self._get_config()
        cfg['access_token'] = access_token
        cfg['refresh_token'] = refresh_token
        cfg['expires_at'] = expires_at
        
        success = self._save_config(cfg)
        if success:
            print(f"✓ Tokens saved: expires_at={expires_at}")
        else:
            print(f"✗ Failed to save tokens")
        return success
    
    def get_access_token(self):
        """Get the current access token"""
        return self._get_config().get('access_token')
    
    def get_refresh_token(self):
        """Get the current refresh token"""
        return self._get_config().get('refresh_token')
    
    def set_access_token(self, token):
        """Set the access token"""
        cfg = self._get_config()
        cfg['access_token'] = token
        return self._save_config(cfg)
    
    def is_logged_in(self):
        """Check if user is logged in with a valid token"""
        token = self.get_access_token()
        return bool(token)
    
    def save_user_data(self, user_data: dict):
        """
        Save user data from login response
        
        Args:
            user_data: Dict containing user info (id, email, full_name, is_admin,
                       has_subscription, subscription_expires_at, subscription_tier, is_lifetime,
                       can_create_decks, created_decks_count, max_decks_allowed)
        """
        cfg = self._get_config()
        cfg['user'] = user_data
        cfg['is_admin'] = user_data.get('is_admin', False)
        
        # Save subscription access fields (v3.2 - subscription-only)
        cfg['has_subscription'] = user_data.get('has_subscription', False)
        cfg['subscription_expires_at'] = user_data.get('subscription_expires_at')
        cfg['subscription_tier'] = user_data.get('subscription_tier', 'free')
        cfg['is_lifetime'] = user_data.get('is_lifetime', False)
        
        # Save collaborative deck creation fields (v3.1)
        cfg['can_create_decks'] = user_data.get('can_create_decks', False)
        cfg['created_decks_count'] = user_data.get('created_decks_count', 0)
        cfg['max_decks_allowed'] = user_data.get('max_decks_allowed', 0)
        
        success = self._save_config(cfg)
        if success:
            admin_status = 'Admin' if cfg['is_admin'] else 'User'
            tier_info = self._get_tier_display()
            deck_info = f", can_create: {cfg['can_create_decks']}" if cfg['can_create_decks'] else ""
            print(f"✓ User data saved: {user_data.get('email')} ({admin_status}, {tier_info}{deck_info})")
        return success
    
    def _get_tier_display(self) -> str:
        """Get human-readable tier display for logging"""
        if self.is_lifetime_subscriber():
            return "Lifetime Subscriber"
        if self.has_active_subscription():
            tier = self.get_subscription_tier()
            return f"{tier.capitalize()} Subscriber" if tier != 'free' else "Subscriber"
        return "Free Tier"
    
    def is_admin(self) -> bool:
        """Check if current user has admin privileges"""
        return self._get_config().get('is_admin', False)
    
    def get_user(self) -> dict:
        """Get current user data"""
        return self._get_config().get('user', {})
    
    def clear_tokens(self):
        """Clear all authentication tokens and user data"""
        cfg = self._get_config()
        cfg['access_token'] = None
        cfg['refresh_token'] = None
        cfg['expires_at'] = None
        cfg['user'] = None
        cfg['is_admin'] = False
        # Clear subscription access fields (v3.2)
        cfg['has_subscription'] = False
        cfg['subscription_expires_at'] = None
        cfg['subscription_tier'] = 'free'
        cfg['is_lifetime'] = False
        # Clear collaborative deck creation fields (v3.1)
        cfg['can_create_decks'] = False
        cfg['created_decks_count'] = 0
        cfg['max_decks_allowed'] = 0
        
        success = self._save_config(cfg)
        if success:
            print("✓ Tokens cleared successfully")
        else:
            print("✗ Failed to clear tokens")
        return success
    
    # === SUBSCRIPTION ACCESS (v3.2 - subscription-only model) ===
    
    def has_subscription(self) -> bool:
        """Check if user has an AnkiPH subscription (may be expired)"""
        return self._get_config().get('has_subscription', False)
    
    def get_subscription_tier(self) -> str:
        """Get subscription tier: 'free', 'student', 'regular', or 'lifetime'"""
        return self._get_config().get('subscription_tier', 'free')
    
    def get_subscription_expires_at(self) -> str:
        """Get subscription expiry timestamp (ISO format) or None"""
        return self._get_config().get('subscription_expires_at')
    
    def is_lifetime_subscriber(self) -> bool:
        """Check if user has lifetime subscription (grandfathered or purchased)"""
        if self._get_config().get('is_lifetime', False):
            return True
        tier = self.get_subscription_tier()
        return tier == 'lifetime'
    
    def has_active_subscription(self) -> bool:
        """
        Check if user has an active (non-expired) AnkiPH subscription.
        
        Returns:
            True if user has subscription AND it hasn't expired (or is lifetime)
        """
        if not self.has_subscription():
            return False
        
        # Lifetime subscribers never expire
        if self.is_lifetime_subscriber():
            return True
        
        expires_at = self.get_subscription_expires_at()
        if not expires_at:
            return False
        
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            return expiry > datetime.now(expiry.tzinfo)
        except (ValueError, TypeError):
            # If we can't parse the date, assume still valid
            return True
    
    def has_full_access(self) -> bool:
        """
        Check if user has full access to all decks.
        
        Returns:
            True if user has an active subscription
        """
        return self.has_active_subscription()
    
    def get_access_status_text(self) -> str:
        """
        Get human-readable subscription status for UI display.
        
        Returns:
            Status string like "Lifetime Subscriber" or "Free Tier - Limited Access"
        """
        if self.is_lifetime_subscriber():
            return "Lifetime Subscriber - Full Access"
        
        if self.has_active_subscription():
            tier = self.get_subscription_tier()
            expires = self.get_subscription_expires_at()
            tier_label = tier.capitalize() if tier != 'free' else 'AnkiPH'
            
            if expires:
                try:
                    expiry_date = expires[:10]  # Get YYYY-MM-DD
                    return f"{tier_label} Subscriber - Expires: {expiry_date}"
                except:
                    pass
            return f"{tier_label} Subscriber - Active"
        
        return "Free Tier - Limited Access"
    
    # === COLLABORATIVE DECK CREATION (v3.1) ===
    
    def can_create_decks(self) -> bool:
        """Check if user can create collaborative decks (premium feature)"""
        return self._get_config().get('can_create_decks', False)
    
    def get_created_decks_count(self) -> int:
        """Get number of collaborative decks the user has created"""
        return self._get_config().get('created_decks_count', 0)
    
    def get_max_decks_allowed(self) -> int:
        """Get maximum number of collaborative decks user can create"""
        return self._get_config().get('max_decks_allowed', 0)
    
    def can_create_more_decks(self) -> bool:
        """Check if user can create more collaborative decks (under limit)"""
        return self.can_create_decks() and self.get_created_decks_count() < self.get_max_decks_allowed()
    
    def update_deck_creation_status(self, can_create: bool, created_count: int, max_allowed: int):
        """
        Update collaborative deck creation status.
        
        Args:
            can_create: Whether user can create decks (premium)
            created_count: Number of decks user has created
            max_allowed: Maximum decks allowed for user tier
        """
        cfg = self._get_config()
        cfg['can_create_decks'] = can_create
        cfg['created_decks_count'] = created_count
        cfg['max_decks_allowed'] = max_allowed
        return self._save_config(cfg)
    
    # === DOWNLOADED DECKS TRACKING (PROFILE-SPECIFIC) ===
    
    def save_downloaded_deck(self, deck_id, version, anki_deck_id=None, title=None, card_count=None):
        """
        Track a downloaded deck (PROFILE-SPECIFIC)
        
        Args:
            deck_id: AnkiPH deck ID
            version: Deck version
            anki_deck_id: Anki's internal deck ID (optional, None if not installed)
            title: Deck title from server (optional)
            card_count: Number of cards (optional)
        """
        if not deck_id:
            print("✗ Cannot save deck: no deck_id provided")
            return False
        
        # Ensure anki_deck_id is an integer if provided
        if anki_deck_id is not None:
            try:
                anki_deck_id = int(anki_deck_id)
            except (ValueError, TypeError) as e:
                print(f"✗ Cannot save deck: invalid anki_deck_id '{anki_deck_id}' ({e})")
                return False
        
        # Get current downloaded decks for this profile
        downloaded_decks = self._get_profile_meta('downloaded_decks', {})
        
        if not isinstance(downloaded_decks, dict):
            downloaded_decks = {}
        
        # Preserve existing data if updating
        existing = downloaded_decks.get(str(deck_id), {})
        
        # Save deck info (merge with existing)
        downloaded_decks[str(deck_id)] = {
            'version': str(version),
            'anki_deck_id': anki_deck_id if anki_deck_id is not None else existing.get('anki_deck_id'),
            'title': title or existing.get('title'),
            'card_count': card_count if card_count is not None else existing.get('card_count'),
            'downloaded_at': existing.get('downloaded_at') or datetime.now().isoformat(),
            'last_synced': None
        }
        
        # Save back to profile metadata
        success = self._set_profile_meta('downloaded_decks', downloaded_decks)
        
        if success:
            install_status = f"(Anki ID: {anki_deck_id})" if anki_deck_id else "(not installed)"
            print(f"✓ Saved deck to profile: {deck_id} v{version} {install_status}")
        else:
            print(f"✗ Failed to save deck to profile: {deck_id}")
        
        return success
    
    def get_downloaded_decks(self):
        """Get dictionary of downloaded decks (PROFILE-SPECIFIC)"""
        if not mw.col:
            print("⚠ No collection available")
            return {}
        
        decks = self._get_profile_meta('downloaded_decks', {})
        
        # Ensure it's a dictionary
        if not isinstance(decks, dict):
            print(f"⚠ downloaded_decks is not a dict, resetting")
            decks = {}
        
        print(f"Retrieved {len(decks)} tracked deck(s) for current profile")
        return decks
    
    def is_deck_downloaded(self, deck_id):
        """Check if a deck is downloaded (PROFILE-SPECIFIC)"""
        if not deck_id:
            return False
        
        downloaded_decks = self.get_downloaded_decks()
        return str(deck_id) in downloaded_decks
    
    def get_deck_anki_id(self, deck_id):
        """Get the Anki deck ID for a downloaded deck"""
        if not deck_id:
            return None
        
        decks = self.get_downloaded_decks()
        deck_info = decks.get(str(deck_id), {})
        anki_deck_id = deck_info.get('anki_deck_id')
        
        if anki_deck_id is not None:
            try:
                return int(anki_deck_id)
            except (ValueError, TypeError):
                print(f"✗ Invalid anki_deck_id: {anki_deck_id}")
                return None
        
        return None
    
    def get_deck_version(self, deck_id):
        """Get the version of a downloaded deck"""
        if not deck_id:
            return None
        
        decks = self.get_downloaded_decks()
        deck_info = decks.get(str(deck_id), {})
        return deck_info.get('version')
    
    def update_deck_version(self, deck_id, new_version):
        """Update the version of a downloaded deck"""
        if not deck_id:
            return False
        
        downloaded_decks = self.get_downloaded_decks()
        
        if str(deck_id) in downloaded_decks:
            downloaded_decks[str(deck_id)]['version'] = str(new_version)
            downloaded_decks[str(deck_id)]['updated_at'] = datetime.now().isoformat()
            return self._set_profile_meta('downloaded_decks', downloaded_decks)
        
        return False
    
    def remove_downloaded_deck(self, deck_id):
        """Remove a deck from tracking"""
        if not deck_id:
            print(f"✗ Cannot remove deck: no deck_id provided")
            return False
        
        print(f"Removing deck from tracking: {deck_id}")
        
        downloaded_decks = self.get_downloaded_decks()
        
        if not isinstance(downloaded_decks, dict):
            print(f"✓ Deck {deck_id} not tracked (no tracking data)")
            return True
        
        deck_id_str = str(deck_id)
        
        if deck_id_str not in downloaded_decks:
            print(f"✓ Deck {deck_id} not tracked (already removed)")
            return True
        
        # Remove from tracking
        del downloaded_decks[deck_id_str]
        
        success = self._set_profile_meta('downloaded_decks', downloaded_decks)
        
        if success:
            print(f"✓ Removed deck from profile tracking: {deck_id}")
        else:
            print(f"✗ Failed to remove deck: {deck_id}")
        
        return success
    
    # === UPDATE CHECKING (GLOBAL) ===
    
    def get_last_update_check(self):
        """Get timestamp of last update check"""
        return self._get_config().get('last_update_check')
    
    def set_last_update_check(self, timestamp=None):
        """Save last update check timestamp"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        cfg = self._get_config()
        cfg['last_update_check'] = timestamp
        return self._save_config(cfg)
    
    def get_auto_check_updates(self):
        """Check if auto-update checking is enabled"""
        return self._get_config().get('auto_check_updates', True)
    
    def set_auto_check_updates(self, enabled):
        """Set auto-update checking state"""
        cfg = self._get_config()
        cfg['auto_check_updates'] = bool(enabled)
        return self._save_config(cfg)
    
    def get_update_check_interval_hours(self):
        """Get update check interval in hours"""
        return self._get_config().get('update_check_interval_hours', 24)
    
    def set_update_check_interval_hours(self, hours):
        """Set update check interval in hours"""
        cfg = self._get_config()
        cfg['update_check_interval_hours'] = int(hours)
        return self._save_config(cfg)
    
    def get_available_updates(self):
        """Get dict of decks with available updates"""
        return self._get_config().get('available_updates', {})
    
    def save_available_updates(self, updates_dict):
        """
        Save available updates for decks
        
        Args:
            updates_dict: Dict mapping deck_id -> update info
        """
        cfg = self._get_config()
        cfg['available_updates'] = updates_dict
        return self._save_config(cfg)
    
    def has_update_available(self, deck_id):
        """Check if a specific deck has an update available"""
        updates = self.get_available_updates()
        return str(deck_id) in updates and updates[str(deck_id)].get('has_update', False)
    
    def clear_update_for_deck(self, deck_id):
        """Clear update notification for a specific deck"""
        cfg = self._get_config()
        updates = cfg.get('available_updates', {})
        
        if str(deck_id) in updates:
            del updates[str(deck_id)]
            cfg['available_updates'] = updates
            return self._save_config(cfg)
        
        return True
    
    # === NOTIFICATION TRACKING (GLOBAL) ===
    
    def get_last_notification_check(self):
        """Get timestamp of last notification check"""
        return self._get_config().get('last_notification_check')
    
    def set_last_notification_check(self, timestamp=None):
        """Save last notification check timestamp"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        cfg = self._get_config()
        cfg['last_notification_check'] = timestamp
        return self._save_config(cfg)
    
    def get_unread_notification_count(self):
        """Get count of unread notifications"""
        return self._get_config().get('unread_notification_count', 0)
    
    def set_unread_notification_count(self, count):
        """Set count of unread notifications"""
        cfg = self._get_config()
        cfg['unread_notification_count'] = int(count)
        return self._save_config(cfg)
    
    # === SYNC STATE (GLOBAL) ===
    
    def get_sync_state(self, deck_id):
        """Get sync state for a deck"""
        sync_states = self._get_config().get('sync_state', {})
        return sync_states.get(str(deck_id), {})
    
    def save_sync_state(self, deck_id, state_data):
        """
        Save sync state for a deck
        
        Args:
            deck_id: The deck ID
            state_data: Dict containing sync state info
        """
        cfg = self._get_config()
        
        if 'sync_state' not in cfg:
            cfg['sync_state'] = {}
        
        cfg['sync_state'][str(deck_id)] = {
            **state_data,
            'last_updated': datetime.now().isoformat()
        }
        
        return self._save_config(cfg)
    
    def clear_sync_state(self, deck_id):
        """Clear sync state for a deck"""
        cfg = self._get_config()
        sync_states = cfg.get('sync_state', {})
        
        if str(deck_id) in sync_states:
            del sync_states[str(deck_id)]
            cfg['sync_state'] = sync_states
            return self._save_config(cfg)
        
        return True
    
    # === PROTECTED FIELDS (GLOBAL) ===
    
    def get_protected_fields(self, deck_id):
        """Get list of protected field names for a deck"""
        protected = self._get_config().get('protected_fields', {})
        return protected.get(str(deck_id), [])
    
    def save_protected_fields(self, deck_id, field_names):
        """
        Save list of protected field names for a deck
        
        Args:
            deck_id: The deck ID
            field_names: List of field names to protect
        """
        cfg = self._get_config()
        
        if 'protected_fields' not in cfg:
            cfg['protected_fields'] = {}
        
        cfg['protected_fields'][str(deck_id)] = field_names
        
        return self._save_config(cfg)
    
    # === GENERAL SETTINGS ===
    
    def get_auto_sync_enabled(self):
        """Check if auto-sync is enabled"""
        return self._get_config().get('auto_sync_enabled', True)
    
    def set_auto_sync_enabled(self, enabled):
        """Set auto-sync enabled state"""
        cfg = self._get_config()
        cfg['auto_sync_enabled'] = bool(enabled)
        return self._save_config(cfg)



# Global config instance
config = Config()
