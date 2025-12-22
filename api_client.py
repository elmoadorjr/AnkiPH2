"""
Robust API client for AnkiPH Add-on
ENHANCED: Merged v4.0 improvements into stable v3.3 base

Key Improvements from v4.0:
- Thread-safe token refresh with locking
- Exponential backoff with jitter for retries
- Rate limiting support (429 handling)
- Better error handling with custom exceptions
- Request logging and validation
- Token expiry checking

Version: 3.3.1
"""

from __future__ import annotations
import json
import time
import random
import threading
import webbrowser
from typing import Any, Dict, Optional, List
from enum import Enum
from datetime import datetime

try:
    from .constants import PREMIUM_URL
except ImportError:
    PREMIUM_URL = "https://ankiph.lovable.app/subscription"

API_BASE = "https://ladvckxztcleljbiomcf.supabase.co/functions/v1"

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
    _HAS_REQUESTS = False


# === SUBSCRIPTION ACCESS SYSTEM (v3.3 - subscription-only) ===

class AccessTier(Enum):
    """User access tier for AnkiPH"""
    LIFETIME_SUBSCRIBER = "lifetime_subscriber"  # Full access, never expires
    SUBSCRIBER = "subscriber"                    # Full access via active subscription
    FREE_TIER = "free_tier"                      # Limited to is_free decks only


def check_access(user_data: dict, deck: dict) -> Optional[AccessTier]:
    """
    Determine user's access tier for a specific deck.
    
    Args:
        user_data: Dict with has_subscription, subscription_expires_at, is_lifetime
        deck: Dict with access_type field from API response
    
    Returns:
        AccessTier enum value, or None if no access
    """
    # Tier 1: Lifetime subscribers get everything
    if user_data.get("is_lifetime"):
        return AccessTier.LIFETIME_SUBSCRIBER
    
    # Tier 2: Active subscribers get everything
    if user_data.get("has_subscription"):
        expires = user_data.get("subscription_expires_at")
        if expires:
            try:
                expiry = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                if expiry > datetime.now(expiry.tzinfo):
                    return AccessTier.SUBSCRIBER
            except (ValueError, TypeError):
                # If can't parse, assume still valid
                return AccessTier.SUBSCRIBER
        else:
            # No expiry set, assume active
            return AccessTier.SUBSCRIBER
    
    # Tier 3: Free tier - only is_free decks
    access_type = deck.get("access_type", "")
    if access_type == "free_tier":
        return AccessTier.FREE_TIER
    
    return None  # No access


def can_sync_updates(tier: Optional[AccessTier]) -> bool:
    """
    Check if user's tier allows syncing updates.
    Free tier users cannot sync updates - they only get initial download.
    
    Args:
        tier: The user's AccessTier
    
    Returns:
        True if user can sync updates, False otherwise
    """
    if tier is None:
        return False
    return tier in [AccessTier.LIFETIME_SUBSCRIBER, AccessTier.SUBSCRIBER]


def show_upgrade_prompt():
    """
    Show upgrade dialog when user tries to access paid content.
    Opens browser to subscription page.
    """
    try:
        from aqt.qt import QMessageBox
        from aqt import mw
        
        dialog = QMessageBox(mw)
        dialog.setWindowTitle("Subscription Required")
        dialog.setText(
            "This deck requires an AnkiPH subscription.\n\n"
            "\u2022 Student: \u20b1100/month\n"
            "\u2022 Regular: \u20b1149/month\n\n"
            "Subscribe to sync all 33,709+ Philippine bar exam cards."
        )
        dialog.setIcon(QMessageBox.Icon.Information)
        
        subscribe_btn = dialog.addButton("Subscribe Now", QMessageBox.ButtonRole.ActionRole)
        dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        dialog.exec()
        
        clicked = dialog.clickedButton()
        if clicked == subscribe_btn:
            webbrowser.open(PREMIUM_URL)
    except Exception as e:
        print(f"\u2717 Failed to show upgrade prompt: {e}")


# === ENHANCED ERROR HANDLING (from v4.0) ===

class AnkiPHAPIError(Exception):
    """Custom exception for API errors with enhanced functionality"""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details
    
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error"""
        return self.status_code in (401, 403)
    
    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx)"""
        return self.status_code and 500 <= self.status_code < 600


class AnkiPHRateLimitError(AnkiPHAPIError):
    """Exception for API rate limiting (429)"""
    def __init__(self, message: str, retry_after: int = 60, details: Optional[Any] = None):
        super().__init__(message, status_code=429, details=details)
        self.retry_after = retry_after


# === HELPER FUNCTIONS ===

def exponential_backoff_with_jitter(attempt: int, base_delay: float = 1.0, max_delay: float = 32.0) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
    
    Returns:
        Delay in seconds with jitter applied
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter: random value between 0 and delay
    return delay * (0.5 + random.random() * 0.5)


def check_token_expiry(expires_at_str: Optional[str]) -> bool:
    """
    Check if a token has expired.
    
    Args:
        expires_at_str: ISO format timestamp string
    
    Returns:
        True if token is expired, False if still valid
    """
    if not expires_at_str:
        return False  # No expiry = assume valid
    
    try:
        expiry = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        now = datetime.now(expiry.tzinfo)
        return now >= expiry
    except (ValueError, TypeError, AttributeError):
        print(f"⚠ Could not parse token expiry: {expires_at_str}")
        return False  # Assume valid if can't parse


class ApiClient:
    """
    Thread-safe API client for AnkiPH backend.
    
    Enhanced features from v4.0:
    - Thread-safe token refresh
    - Automatic retry with exponential backoff
    - Rate limiting support (429 handling)
    - Better error handling
    """
    
    def __init__(self, access_token: Optional[str] = None, base_url: str = API_BASE):
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._refresh_lock = threading.Lock()  # Thread-safe token refresh
        self._last_request_time = 0  # Track last request for rate limiting

    def _headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Build request headers"""
        headers = {"Content-Type": "application/json"}
        if include_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _full_url(self, path: str) -> str:
        """Build full URL from path"""
        if path.startswith("/"):
            path = path[1:]
        return f"{self.base_url}/{path}"

    def _handle_rate_limit(self, retry_after: int = 60):
        """
        Handle rate limiting by waiting for specified duration.
        
        Args:
            retry_after: Seconds to wait before retrying
        """
        print(f"⏳ Rate limited - waiting {retry_after}s before retry")
        time.sleep(retry_after)

    def post(self, path: str, json_body: Optional[Dict[str, Any]] = None, 
             require_auth: bool = True, timeout: int = 30, max_retries: int = 3) -> Any:
        """
        Make POST request to API with automatic retry and backoff.
        
        Args:
            path: API endpoint path
            json_body: Request body
            require_auth: Whether authentication is required
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        
        Returns:
            Parsed JSON response
        
        Raises:
            AnkiPHAPIError: On API errors
            AnkiPHRateLimitError: On rate limiting (429)
        """
        url = self._full_url(path)
        headers = self._headers(include_auth=require_auth)

        for attempt in range(max_retries):
            try:
                if _HAS_REQUESTS:
                    result = self._post_with_requests(url, headers, json_body, timeout)
                else:
                    result = self._post_with_urllib(url, headers, json_body, timeout)
                
                # Success - return result
                return result
                
            except AnkiPHRateLimitError as e:
                # Handle rate limiting
                if attempt < max_retries - 1:
                    self._handle_rate_limit(e.retry_after)
                    continue
                else:
                    raise  # Last attempt - re-raise
            
            except AnkiPHAPIError as e:
                # Handle auth errors with token refresh
                if e.is_auth_error() and attempt == 0:
                    if self._try_refresh_token():
                        # Token refreshed - retry request
                        headers = self._headers(include_auth=require_auth)
                        continue
                
                # Handle server errors with backoff
                if e.is_server_error() and attempt < max_retries - 1:
                    delay = exponential_backoff_with_jitter(attempt)
                    print(f"⏳ Server error - retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                
                # Re-raise if can't handle
                raise
            
            except Exception as e:
                # Generic error - retry with backoff
                if attempt < max_retries - 1:
                    delay = exponential_backoff_with_jitter(attempt)
                    print(f"⏳ Request failed - retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt - wrap and raise
                    raise AnkiPHAPIError(f"Request failed after {max_retries} attempts: {e}") from e
        
        # Should not reach here
        raise AnkiPHAPIError("Maximum retries exceeded")

    def _try_refresh_token(self) -> bool:
        """
        Attempt to refresh access token.
        Thread-safe - only one thread can refresh at a time.
        
        Returns:
            True if token was successfully refreshed
        """
        # Use lock to prevent multiple simultaneous refresh attempts
        with self._refresh_lock:
            try:
                from .config import config
                
                refresh_token = config.get_refresh_token()
                if not refresh_token:
                    return False
                
                print("🔄 Attempting to refresh access token...")
                
                # Call refresh endpoint
                result = self.refresh_token(refresh_token)
                
                if result.get('success'):
                    new_access = result.get('access_token')
                    new_refresh = result.get('refresh_token', refresh_token)
                    new_expires = result.get('expires_at')
                    
                    if new_access:
                        # Save new tokens
                        config.save_tokens(new_access, new_refresh, new_expires)
                        self.access_token = new_access
                        print("✓ Token refreshed successfully")
                        return True
                
                print("✗ Token refresh failed: no access token in response")
                return False
                
            except Exception as e:
                print(f"✗ Token refresh failed: {e}")
                return False

    def _post_with_requests(self, url: str, headers: Dict[str, str], 
                           json_body: Optional[Dict[str, Any]], timeout: int) -> Any:
        """POST using requests library"""
        try:
            resp = requests.post(url, headers=headers, json=json_body or {}, timeout=timeout)
        except requests.Timeout:
            raise AnkiPHAPIError("Request timed out. Please check your internet connection.")
        except requests.ConnectionError:
            raise AnkiPHAPIError("Connection failed. Please check your internet connection.")
        except Exception as e:
            raise AnkiPHAPIError(f"Network error: {e}") from e

        # Parse response
        try:
            data = resp.json()
        except Exception: 
            text = resp.text if hasattr(resp, "text") else ""
            raise AnkiPHAPIError(
                f"Invalid response from server (HTTP {resp.status_code})", 
                status_code=resp.status_code, 
                details=text[:500]
            )

        # Check for rate limiting
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', 60))
            raise AnkiPHRateLimitError(
                "Rate limit exceeded. Please wait before retrying.",
                retry_after=retry_after,
                details=data
            )

        # Check for errors
        if not resp.ok:
            err_msg = None
            if isinstance(data, dict):
                err_msg = data.get("error") or data.get("message") or data.get("detail")
            
            if not err_msg:
                err_msg = f"HTTP {resp.status_code} error"
            
            raise AnkiPHAPIError(err_msg, status_code=resp.status_code, details=data)

        return data

    def _post_with_urllib(self, url: str, headers: Dict[str, str], 
                         json_body: Optional[Dict[str, Any]], timeout: int) -> Any:
        """POST using urllib (fallback)"""
        try:
            req_data = (json.dumps(json_body or {})).encode("utf-8")
            req = _urllib_request.Request(url, data=req_data, headers=headers, method="POST")
            
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                
                try:
                    data = json.loads(raw.decode("utf-8"))
                except Exception:
                    raise AnkiPHAPIError(
                        "Invalid JSON response from server", 
                        status_code=resp.getcode(), 
                        details=raw[:500]
                    )
                
                # Check for rate limiting
                if resp.getcode() == 429:
                    retry_after = int(resp.headers.get('Retry-After', 60))
                    raise AnkiPHRateLimitError(
                        "Rate limit exceeded. Please wait before retrying.",
                        retry_after=retry_after,
                        details=data
                    )
                
                if resp.getcode() >= 400:
                    err_msg = data.get("error") if isinstance(data, dict) else None
                    raise AnkiPHAPIError(
                        err_msg or f"HTTP {resp.getcode()}", 
                        status_code=resp.getcode(), 
                        details=data
                    )
                
                return data
                
        except _urllib_error.HTTPError as he:
            try:
                body = he.read()
                parsed = json.loads(body.decode("utf-8"))
                err_msg = parsed.get("error") if isinstance(parsed, dict) else None
            except Exception:
                parsed = None
                err_msg = None
            
            # Check for rate limiting
            if getattr(he, 'code', None) == 429:
                retry_after = 60
                try:
                    retry_after = int(he.headers.get('Retry-After', 60))
                except:
                    pass
                raise AnkiPHRateLimitError(
                    "Rate limit exceeded. Please wait before retrying.",
                    retry_after=retry_after,
                    details=parsed
                )
            
            raise AnkiPHAPIError(
                err_msg or f"HTTP {getattr(he, 'code', 'error')}", 
                status_code=getattr(he, "code", None), 
                details=parsed or str(he)
            ) from he
            
        except _urllib_error.URLError as ue:
            raise AnkiPHAPIError(f"Connection error: {ue}") from ue
            
        except Exception as e:
            raise AnkiPHAPIError(f"Network error: {e}") from e

    # === AUTHENTICATION ENDPOINTS ===
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login with email and password"""
        return self.post(
            "/addon-login", 
            json_body={"email": email, "password": password}, 
            require_auth=False
        )

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        return self.post(
            "/addon-refresh-token", 
            json_body={"refresh_token": refresh_token}, 
            require_auth=False
        )

    # === DECK ENDPOINTS ===
    
    def get_purchased_decks(self) -> Any:
        """Get user's purchased decks"""
        return self.post("/addon-get-purchases")

    def browse_decks(self, category: str = "all", search: Optional[str] = None,
                     page: int = 1, limit: int = 20) -> Any:
        """Browse available decks"""
        json_body = {
            "category": category,
            "page": page,
            "limit": min(limit, 100)
        }
        
        if search:
            json_body["search"] = search
        
        return self.post("/addon-browse-decks", json_body=json_body)

    def download_deck(self, deck_id: str, include_media: bool = True) -> Any:
        """Download full deck content"""
        return self.post("/addon-download-deck", json_body={
            "deck_id": deck_id,
            "include_media": include_media
        })

    def batch_download_decks(self, deck_ids: List[str]) -> Any:
        """Download multiple decks at once (max 10)"""
        if len(deck_ids) > 10:
            raise ValueError("Maximum 10 decks per batch download")
        
        return self.post("/addon-batch-download", json_body={"deck_ids": deck_ids})

    def download_deck_file(self, download_url: str) -> bytes:
        """Download deck file from signed URL"""
        if not download_url:
            raise AnkiPHAPIError("Download URL is required")
        
        # Validate URL format
        if not isinstance(download_url, str):
            raise AnkiPHAPIError(f"Download URL must be a string, got {type(download_url).__name__}")
        
        download_url = download_url.strip()
        
        if not download_url.startswith(('http://', 'https://')):
            preview = download_url[:100] if len(download_url) > 100 else download_url
            print(f"✗ Invalid download_url received: {preview}")
            raise AnkiPHAPIError(f"Invalid download URL format. Expected http/https URL, got: {preview[:50]}...")
        
        print(f"✓ Downloading from: {download_url[:80]}...")

        if not _HAS_REQUESTS: 
            try:
                req = _urllib_request.Request(download_url, method="GET")
                with _urllib_request.urlopen(req, timeout=120) as resp:
                    content = resp.read()
                    if len(content) == 0:
                        raise AnkiPHAPIError("Downloaded file is empty")
                    return content
            except Exception as e:
                raise AnkiPHAPIError(f"Network error while downloading deck: {e}") from e

        # Use requests library
        try:
            response = requests.get(download_url, timeout=120, stream=True, allow_redirects=True)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            
            if "text/html" in content_type or "application/json" in content_type:
                try:
                    text = response.text[:1000]
                    if "error" in text.lower() or "expired" in text.lower():
                        raise AnkiPHAPIError(
                            "Download URL may be expired or invalid. Please try again."
                        )
                except Exception:
                    pass
                raise AnkiPHAPIError(
                    f"Received {content_type} instead of a deck file. URL may be expired."
                )

            # Download content
            content = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: 
                    content.extend(chunk)

            if len(content) == 0:
                raise AnkiPHAPIError("Downloaded file is empty")

            # Quick ZIP signature check
            if len(content) >= 4:
                if content[:2] != b"PK":
                    print("⚠ Warning: downloaded file does not appear to be a ZIP file")

            return bytes(content)
            
        except requests.HTTPError as he:
            raise AnkiPHAPIError(
                f"HTTP error while downloading deck: {he}", 
                status_code=getattr(he.response, "status_code", None)
            ) from he
            
        except requests.RequestException as re:
            raise AnkiPHAPIError(f"Network error while downloading deck: {re}") from re
            
        except Exception as e:
            raise AnkiPHAPIError(f"Unexpected error downloading deck: {e}") from e

    # === UPDATE CHECKING ===
    
    def check_updates(self) -> Any:
        """Check for updates on all purchased decks"""
        return self.post("/addon-check-updates")

    def check_deck_updates(self, deck_id: str, current_version: str,
                          last_sync_timestamp: Optional[str] = None) -> Any:
        """Check if a specific deck has updates"""
        json_body = {
            "deck_id": deck_id,
            "current_version": current_version
        }
        if last_sync_timestamp:
            json_body["last_sync_timestamp"] = last_sync_timestamp
        
        return self.post("/addon-check-updates", json_body=json_body)

    # === SUBSCRIPTION MANAGEMENT ===
    
    def manage_subscription(self, action: str, deck_id: str,
                           sync_enabled: bool = True,
                           notify_updates: bool = True) -> Any:
        """Manage deck subscriptions"""
        json_body = {
            "action": action,
            "deck_id": deck_id
        }
        
        if action in ("subscribe", "update"):
            json_body["sync_enabled"] = sync_enabled
            json_body["notify_updates"] = notify_updates
        
        return self.post("/addon-manage-subscription", json_body=json_body)

    def get_changelog(self, deck_id: str, from_version: Optional[str] = None) -> Any:
        """Get changelog/version history for a deck"""
        json_body = {"deck_id": deck_id}
        if from_version:
            json_body["from_version"] = from_version
        return self.post("/addon-get-changelog", json_body=json_body)

    def check_notifications(self, last_check: Optional[str] = None) -> Any:
        """Check for pending notifications"""
        json_body = {}
        if last_check:
            json_body["last_check"] = last_check
        return self.post("/addon-check-notifications", json_body=json_body)

    # === PROGRESS & SYNC ENDPOINTS ===
    
    def sync_progress(self, deck_id: str = None, progress: Dict = None,
                      progress_data: List[Dict] = None) -> Any:
        """Sync study progress to server"""
        if deck_id and progress:
            return self.post("/addon-sync-progress", json_body={
                "deck_id": deck_id,
                "progress": progress
            })
        else:
            return self.post("/addon-sync-progress", json_body={
                "progress_data": progress_data or []
            })

    # === COLLABORATIVE FEATURES ===
    
    def push_changes(self, deck_id: str, changes: List[Dict]) -> Any:
        """Push user's local changes as suggestions"""
        return self.post("/addon-push-changes", 
                        json_body={"deck_id": deck_id, "changes": changes})

    def pull_changes(self, deck_id: str, since: Optional[str] = None, 
                     last_change_id: Optional[str] = None,
                     full_sync: bool = False,
                     offset: int = 0,
                     limit: int = 1000) -> Any:
        """Pull publisher changes since last sync"""
        body = {
            "deck_id": deck_id, 
            "full_sync": full_sync,
            "offset": offset,
            "limit": limit
        }
        if since:
            body["since"] = since
        if last_change_id:
            body["last_change_id"] = last_change_id
        
        return self.post("/addon-pull-changes", json_body=body)
    
    def pull_all_cards(self, deck_id: str, progress_callback=None) -> dict:
        """Pull ALL cards from a deck, handling pagination automatically"""
        all_cards = []
        note_types = []
        latest_change_id = None
        total_cards = 0
        offset = 0
        limit = 1000
        
        while True:
            result = self.pull_changes(
                deck_id=deck_id,
                full_sync=True,
                offset=offset,
                limit=limit
            )
            
            if not result.get('success'):
                return result
            
            cards = result.get('cards', [])
            all_cards.extend(cards)
            
            if offset == 0:
                note_types = result.get('note_types', [])
                total_cards = result.get('total_cards', len(cards))
                latest_change_id = result.get('latest_change_id')
            
            if progress_callback:
                progress_callback(len(all_cards), total_cards)
            
            print(f"✓ Fetched batch: offset={offset}, got {len(cards)} cards (total: {len(all_cards)}/{total_cards})")
            
            has_more = result.get('has_more', False)
            if not has_more and len(cards) == limit:
                has_more = True
            
            if not has_more or len(cards) == 0:
                break
            
            offset = result.get('next_offset', offset + limit)
        
        return {
            "success": True,
            "cards": all_cards,
            "note_types": note_types,
            "total_cards": len(all_cards),
            "latest_change_id": latest_change_id
        }

    def submit_suggestion(self, deck_id: str, card_guid: str, field_name: str,
                         current_value: str, suggested_value: str, 
                         reason: Optional[str] = None) -> Any:
        """Submit a card improvement suggestion"""
        return self.post("/addon-submit-suggestion", json_body={
            "deck_id": deck_id,
            "card_guid": card_guid,
            "field_name": field_name,
            "current_value": current_value,
            "suggested_value": suggested_value,
            "reason": reason
        })

    def get_protected_fields(self, deck_id: str) -> Any:
        """Get user's protected fields"""
        return self.post("/addon-get-protected-fields", json_body={"deck_id": deck_id})

    def get_card_history(self, deck_id: str, card_guid: str, limit: int = 50) -> Any:
        """Get change history for a specific card"""
        return self.post("/addon-get-card-history", 
                        json_body={"deck_id": deck_id, "card_guid": card_guid, "limit": limit})

    def rollback_card(self, deck_id: str, card_guid: str, target_version: str) -> Any:
        """Rollback a card to a previous version"""
        return self.post("/addon-rollback-card", 
                        json_body={
                            "deck_id": deck_id,
                            "card_guid": card_guid,
                            "target_version": target_version
                        })

    # === DATA SYNC ===
    
    def sync_tags(self, deck_id: str, tags: List[Dict]) -> Any:
        """Sync card tags"""
        return self.post("/addon-sync-tags", json_body={
            "deck_id": deck_id,
            "tags": tags
        })

    def sync_suspend_state(self, deck_id: str, states: List[Dict]) -> Any:
        """Sync card suspend/bury states"""
        return self.post("/addon-sync-suspend-state", json_body={
            "deck_id": deck_id,
            "states": states
        })

    def sync_media(self, deck_id: str, action: str, 
                   file_hashes: List[str] = None,
                   files: List[Dict] = None) -> Any:
        """Sync media files"""
        json_body = {"deck_id": deck_id, "action": action}
        if file_hashes:
            json_body["file_hashes"] = file_hashes
        if files:
            json_body["files"] = files
        return self.post("/addon-sync-media", json_body=json_body)

    def sync_note_types(self, deck_id: str, action: str = "get", 
                        note_types: Optional[List] = None) -> Any:
        """Sync note type templates and CSS"""
        body = {"deck_id": deck_id, "action": action}
        if note_types:
            body["note_types"] = note_types
        
        return self.post("/addon-sync-note-types", json_body=body)

    # === ADMIN ENDPOINTS ===
    
    def admin_push_changes(self, deck_id: str, changes: List[Dict], version: str,
                           version_notes: Optional[str] = None,
                           timeout: int = 60) -> Any:
        """Admin: Push card changes from Anki to database"""
        body = {"deck_id": deck_id, "changes": changes, "version": version}
        if version_notes:
            body["version_notes"] = version_notes
        return self.post("/addon-admin-push-changes", json_body=body, timeout=timeout)

    def admin_import_deck(self, deck_id: Optional[str], cards: List[Dict], version: str,
                          version_notes: Optional[str] = None,
                          clear_existing: bool = False,
                          deck_title: Optional[str] = None,
                          timeout: int = 60) -> Any:
        """Admin: Import full deck to database"""
        body = {
            "cards": cards,
            "version": version,
            "clear_existing": clear_existing
        }
        if deck_id:
            body["deck_id"] = deck_id
        if deck_title:
            body["deck_title"] = deck_title
        if version_notes:
            body["version_notes"] = version_notes
        return self.post("/addon-admin-import-deck", json_body=body, timeout=timeout)

    # === COLLABORATIVE DECK MANAGEMENT ===
    
    def create_deck(self, title: str, description: str = "", 
                    bar_subject: Optional[str] = None, 
                    is_public: bool = True,
                    tags: Optional[List[str]] = None) -> Any:
        """Create a new collaborative deck (premium users only)"""
        body = {
            "title": title,
            "description": description,
            "is_public": is_public
        }
        if bar_subject:
            body["bar_subject"] = bar_subject
        if tags:
            body["tags"] = tags
        
        return self.post("/addon-create-deck", json_body=body)

    def update_deck(self, deck_id: str, 
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    bar_subject: Optional[str] = None,
                    is_public: Optional[bool] = None,
                    tags: Optional[List[str]] = None) -> Any:
        """Update metadata for a collaborative deck you created"""
        body = {"deck_id": deck_id}
        if title is not None:
            body["title"] = title
        if description is not None:
            body["description"] = description
        if bar_subject is not None:
            body["bar_subject"] = bar_subject
        if is_public is not None:
            body["is_public"] = is_public
        if tags is not None:
            body["tags"] = tags
        
        return self.post("/addon-update-deck", json_body=body)

    def delete_user_deck(self, deck_id: str, confirm: bool = False) -> Any:
        """Delete a collaborative deck you created"""
        return self.post("/addon-delete-user-deck", 
                        json_body={"deck_id": deck_id, "confirm": confirm})

    def push_deck_cards(self, deck_id: str, cards: List[Dict],
                        delete_missing: bool = False,
                        version: Optional[str] = None,
                        timeout: int = 60) -> Any:
        """Push cards from Anki Desktop to your collaborative deck"""
        if len(cards) > 500:
            raise ValueError("Maximum 500 cards per request (per API spec)")
        
        body = {"deck_id": deck_id, "cards": cards}
        if delete_missing:
            body["delete_missing"] = True
        if version:
            body["version"] = version
        
        return self.post("/addon-push-deck-cards", json_body=body, timeout=timeout)

    def get_my_decks(self) -> Any:
        """List all collaborative decks created by the authenticated user"""
        return self.post("/addon-get-my-decks", json_body={})


# === GLOBAL INSTANCE ===

# Single shared instance
api = ApiClient()


def set_access_token(token: Optional[str]) -> None:
    """Set the access token for API requests"""
    api.access_token = token
    if token:
        print("✓ Access token set")
    else:
        print("✓ Access token cleared")


def ensure_valid_token() -> bool:
    """
    Ensure we have a valid access token, refreshing if needed.
    
    Returns:
        True if we have a valid token
    """
    from .config import config
    
    token = config.get_access_token()
    if not token:
        return False
    
    # Check expiry
    expires_at = config.get("expires_at")
    if not check_token_expiry(expires_at):
        # Token still valid
        set_access_token(token)
        return True
    
    # Token expired - try refresh
    refresh_token = config.get_refresh_token()
    if not refresh_token:
        print("⚠ Token expired and no refresh token available")
        return False
    
    try:
        print("🔄 Access token expired, attempting refresh...")
        result = api.refresh_token(refresh_token)
        
        if result.get('success'):
            new_token = result.get('access_token')
            new_refresh = result.get('refresh_token', refresh_token)
            new_expires = result.get('expires_at')
            
            if new_token:
                config.save_tokens(new_token, new_refresh, new_expires)
                set_access_token(new_token)
                print("✓ Token refreshed successfully")
                return True
        
        print("✗ Token refresh failed: no access token in response")
        return False
        
    except Exception as e:
        print(f"✗ Token refresh failed: {e}")
        return False