# AnkiPH Anki Addon - Complete Documentation

**Version:** 3.3.0  
**Last Updated:** December 22, 2025  
**Compatible with:** Anki 24.x - 25.x (PyQt6)

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation & Setup](#installation--setup)
4. [User Guide](#user-guide)
5. [Architecture](#architecture)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Development Guide](#development-guide)
9. [Troubleshooting](#troubleshooting)
10. [Version History](#version-history)

---

## Overview

AnkiPH is an AnkiHub-style deck syncing addon designed specifically for Philippine law students preparing for the bar exam. It provides seamless deck subscription, automatic updates, progress tracking, and collaborative features.

### Key Capabilities

- **Subscription Management**: Subscribe to decks with automatic sync
- **Automatic Updates**: Background checking and updating of deck content
- **Progress Tracking**: Sync your study statistics to the server
- **Collaborative Editing**: Submit suggestions and view card history
- **Premium Features**: Create and manage your own collaborative decks
- **Advanced Sync**: Tags, suspend states, media, and note types

### Access Tiers

| Tier | Access | Price | Features |
|------|--------|-------|----------|
| **Lifetime Subscriber** | Full | Grandfathered | All features, never expires |
| **Student** | Full | ₱100/month | All decks, updates, sync |
| **Regular** | Full | ₱149/month | All decks, updates, sync |
| **Free Tier** | Limited | Free | `is_free` decks only, no updates |

---

## Features

### Core Features (Production Ready)

✅ **Authentication**
- JWT-based login/logout
- Automatic token refresh
- Session management

✅ **Deck Management**
- Browse 33,709+ cards across all decks
- Subscribe/unsubscribe to decks
- Batch download (up to 10 decks)
- Profile-specific tracking

✅ **Update System**
- Automatic update checking on startup
- Configurable check intervals (default: 24 hours)
- Manual update triggers
- Incremental and full sync support

✅ **Progress Syncing**
- Study statistics upload
- Retention rate calculation
- Streak tracking
- Leaderboard integration (server-side)

✅ **Notifications**
- Deck update announcements
- System notifications
- Unread count tracking

### Advanced Features (UI Ready)

⚠️ **Change Sync**
- Push/pull card changes
- Conflict resolution UI
- Protected fields support

⚠️ **Collaboration**
- Card improvement suggestions
- Card history viewer
- Version rollback

⚠️ **Advanced Sync**
- Tag synchronization
- Suspend/bury state sync
- Media file sync
- Note type sync

### Premium Features (v3.1+)

✅ **Deck Creation**
- Create collaborative decks (10 max for subscribers)
- Push up to 500 cards per batch
- Metadata management (title, description, tags)
- Visibility controls (public/private)

✅ **Deck Management**
- View created decks
- Update deck metadata
- Delete decks with cascade

### Admin Features

🔒 **Publisher Tools** (Admin/Deck Owner Only)
- Push changes to database
- Import full decks (batch processing)
- Version management
- Batch operations with retry logic

---

## Installation & Setup

### Requirements

- Anki 24.x or 25.x with PyQt6
- Internet connection
- AnkiPH account (register at https://nottorney.com)

### Installation Steps

1. **Download the Addon**
   - Download the latest `.ankiaddon` file from the repository
   - Or install via Anki's addon browser (code: TBD)

2. **Install in Anki**
   - Open Anki
   - Go to: Tools → Add-ons → Install from file...
   - Select the downloaded `.ankiaddon` file
   - Restart Anki

3. **Initial Setup**
   - After restart, you'll see "⚖️ AnkiPH" in the menu bar
   - Click to open the addon
   - Login with your AnkiPH credentials
   - Start browsing and subscribing to decks!

### First Time Configuration

```json
{
  "auto_check_updates": true,
  "update_check_interval_hours": 24,
  "auto_sync_enabled": true
}
```

Access via: **Tools → Add-ons → AnkiPH → Config**

---

## User Guide

### Basic Workflow

#### 1. Login

```
⚖️ AnkiPH → Sign In
```

- Enter your email and password
- System validates and stores JWT tokens
- Subscription tier is automatically detected

#### 2. Browse and Subscribe

- **Browse Decks** button shows all available decks
- Filter by name using the search box
- Subscribe to decks (requires active subscription)
- Free tier users see only `is_free` decks

#### 3. Sync and Update

**Automatic (Recommended)**:
- Updates check on Anki startup
- Downloads happen in background
- Notification shows when updates are available

**Manual**:
```
⚖️ AnkiPH → My Decks → Select deck → Sync
```

#### 4. Study

- Study cards normally in Anki
- Progress syncs automatically on addon close
- Stats contribute to leaderboard (if enabled)

### Advanced Usage

#### Protected Fields

Prevent specific fields from being overwritten during sync:

1. Open Settings → Protected Fields
2. Select your deck
3. Add field names to protect (e.g., "Personal Notes", "Extra")
4. Changes from server won't touch these fields

#### Card Suggestions

Submit improvements to deck maintainers:

1. My Decks → Select deck → 💡 Suggest
2. Choose a card
3. Select field to edit
4. Enter suggested value and reason
5. Submit for review

#### Card History & Rollback

View version history and restore previous versions:

1. My Decks → Select deck → 📜 Card History
2. Select a card
3. Browse version timeline
4. Click "Rollback" to restore an older version

---

## Architecture

### File Structure

```
AnkiPH_Addon/
├── __init__.py              # Entry point, menu setup
├── api_client.py            # API communication (20+ endpoints)
├── config.py                # Configuration management
├── constants.py             # Version, URLs, constants
├── deck_importer.py         # .apkg import with progress
├── sync.py                  # Progress syncing logic
├── update_checker.py        # Background update service
├── utils.py                 # Helper functions
├── config.json              # Default configuration
├── manifest.json            # Addon metadata
└── ui/
    ├── __init__.py
    ├── main_dialog.py       # Unified deck management UI
    ├── login_dialog.py      # AnkiHub-style login
    ├── settings_dialog.py   # Settings + Admin features
    ├── sync_dialog.py       # Push/Pull changes UI
    ├── history_dialog.py    # Card history viewer
    ├── suggestion_dialog.py # Suggestion submission
    └── advanced_sync_dialog.py # Advanced sync options
```

### Data Flow

```
┌─────────────────┐
│   Anki Addon    │
│   (Frontend)    │
└────────┬────────┘
         │
         │ JWT Auth
         │
┌────────▼────────────────────────┐
│   API Client (api_client.py)    │
│   - Request signing              │
│   - Token refresh                │
│   - Error handling               │
└────────┬────────────────────────┘
         │
         │ HTTPS
         │
┌────────▼────────────────────────┐
│  Supabase Edge Functions        │
│  (Backend API)                   │
│  - /addon-login                  │
│  - /addon-browse-decks           │
│  - /addon-download-deck          │
│  - /addon-pull-changes           │
│  - /addon-push-changes           │
│  - etc. (20+ endpoints)          │
└────────┬────────────────────────┘
         │
         │
┌────────▼────────────────────────┐
│   PostgreSQL Database            │
│   - Users & subscriptions        │
│   - Decks & cards                │
│   - Changes & history            │
└──────────────────────────────────┘
```

### Configuration System

#### Profile-Specific Data (Anki Collection)
Stored in `collection.anki2` metadata:
- `ankiph_downloaded_decks`: Deck tracking per profile
- Syncs automatically when switching profiles

#### Global Settings (Addon Config)
Stored in Anki's addon config:
- Authentication tokens
- User preferences
- Update settings
- Protected fields

### Update Mechanism

```python
# Startup flow
1. main_window_did_init hook triggered
2. update_checker.auto_check_if_needed()
3. API call: /addon-check-updates
4. Compare versions: local vs server
5. If updates available:
   - Show tooltip notification
   - Store in config.available_updates
   - Optionally auto-apply
```

### Sync Architecture

**Incremental Sync (v3.0+)**:
```python
# Pull changes since last sync
result = api.pull_changes(
    deck_id=deck_id,
    last_change_id="previous_change_uuid",
    full_sync=False
)

# Apply changes to local cards
for change in result['changes']:
    update_local_card(change)
```

**Full Sync (Large Decks)**:
```python
# Paginated fetch for 32k+ card decks
offset = 0
limit = 1000
all_cards = []

while True:
    result = api.pull_changes(
        deck_id=deck_id,
        full_sync=True,
        offset=offset,
        limit=limit
    )
    all_cards.extend(result['cards'])
    
    if not result['has_more']:
        break
    
    offset = result['next_offset']
```

---

## API Reference

### Base Configuration

```python
BASE_URL = "https://ladvckxztcleljbiomcf.supabase.co/functions/v1"

# All requests (except login) require:
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
```

### Core Endpoints

#### Authentication

**POST /addon-login**
```python
# Request
{
    "email": "user@example.com",
    "password": "userpassword"
}

# Response
{
    "success": true,
    "access_token": "jwt...",
    "refresh_token": "...",
    "expires_at": "2025-12-23T10:00:00Z",
    "user": {
        "id": "uuid",
        "email": "...",
        "is_admin": false,
        "has_subscription": true,
        "is_lifetime": false,
        "subscription_tier": "student",
        "subscription_expires_at": "2026-01-22T00:00:00Z",
        "can_create_decks": true,
        "created_decks_count": 2,
        "max_decks_allowed": 10
    }
}
```

**POST /addon-refresh-token**
```python
# Request
{
    "refresh_token": "refresh_token_here"
}

# Response
{
    "success": true,
    "access_token": "new_jwt...",
    "refresh_token": "new_refresh...",
    "expires_at": "..."
}
```

#### Deck Browsing

**POST /addon-browse-decks**
```python
# Request
{
    "category": "all",  # all|featured|community|subscribed
    "search": "constitutional",
    "page": 1,
    "limit": 20
}

# Response
{
    "success": true,
    "decks": [
        {
            "id": "uuid",
            "title": "Nottorney Collection",
            "description": "...",
            "card_count": 33709,
            "subscriber_count": 150,
            "is_featured": true,
            "is_verified": true,
            "bar_subject": "political_law",
            "version": "1.0.0",
            "image_url": "https://...",
            "is_subscribed": false,
            "updated_at": "2025-01-15T10:00:00Z"
        }
    ],
    "total": 45,
    "page": 1,
    "total_pages": 3
}
```

#### Deck Download

**POST /addon-download-deck**
```python
# Request
{
    "deck_id": "uuid",
    "include_media": true
}

# Response (v3.0 - uses pull_changes)
{
    "success": true,
    "use_pull_changes": true,
    "deck": {
        "id": "uuid",
        "title": "Nottorney Collection",
        "version": "1.0.0",
        "card_count": 33709
    }
}

# Then call:
# /addon-pull-changes with full_sync=true
```

#### Change Sync

**POST /addon-pull-changes**
```python
# Incremental sync
{
    "deck_id": "uuid",
    "last_change_id": "previous_uuid",
    "full_sync": false
}

# Full sync (pagination)
{
    "deck_id": "uuid",
    "full_sync": true,
    "offset": 0,
    "limit": 1000
}

# Response (incremental)
{
    "success": true,
    "changes": [
        {
            "change_id": "uuid",
            "card_guid": "anki_guid",
            "change_type": "modify",
            "field_name": "Back",
            "old_value": "...",
            "new_value": "...",
            "created_at": "..."
        }
    ],
    "latest_change_id": "uuid",
    "deck_version": "1.0.1"
}

# Response (full sync)
{
    "success": true,
    "cards": [
        {
            "card_guid": "abc123",
            "note_type": "Basic",
            "fields": {"Front": "...", "Back": "..."},
            "tags": ["tag1"],
            "subdeck_path": "DeckName::SubDeck"
        }
    ],
    "note_types": [...],
    "total_cards": 32435,
    "has_more": true,
    "next_offset": 1000,
    "latest_change_id": "uuid"
}
```

**POST /addon-push-changes**
```python
# Request (user suggestions)
{
    "deck_id": "uuid",
    "changes": [
        {
            "card_guid": "guid",
            "field_name": "Back",
            "old_value": "current",
            "new_value": "suggested",
            "reason": "Added citation"
        }
    ]
}

# Response
{
    "success": true,
    "changes_saved": 1,
    "message": "Changes submitted for review"
}
```

#### Premium Features

**POST /addon-create-deck**
```python
# Request
{
    "title": "My Criminal Law Deck",
    "description": "Personal notes",
    "bar_subject": "criminal_law",
    "is_public": true,
    "tags": ["criminal", "reviewer"]
}

# Response
{
    "success": true,
    "deck": {
        "id": "uuid",
        "title": "My Criminal Law Deck",
        "card_count": 0,
        "version": "1.0.0",
        "created_at": "2025-12-22T10:00:00Z"
    }
}
```

**POST /addon-push-deck-cards**
```python
# Request (max 500 cards per call)
{
    "deck_id": "uuid",
    "cards": [
        {
            "card_guid": "local-guid-123",
            "note_type": "Basic",
            "fields": {"Front": "Q", "Back": "A"},
            "tags": ["tag1"],
            "subdeck_path": "My Deck::Chapter 1"
        }
    ],
    "delete_missing": false,
    "version": "1.0.1"
}

# Response
{
    "success": true,
    "version": "1.0.1",
    "stats": {
        "cards_processed": 100,
        "cards_added": 10,
        "cards_modified": 5,
        "cards_deleted": 0,
        "total_cards": 157
    }
}
```

#### Admin Endpoints

**POST /addon-admin-push-changes**
```python
# Request (publisher/admin only)
{
    "deck_id": "uuid",
    "changes": [
        {
            "card_guid": "guid",
            "note_type": "Basic",
            "fields": {"Front": "...", "Back": "..."},
            "tags": ["updated"],
            "change_type": "modify",
            "deck_path": "DeckName::SubDeck"
        }
    ],
    "version": "2.2.0",
    "version_notes": "Updated 50 cards"
}

# Response
{
    "success": true,
    "cards_added": 0,
    "cards_modified": 50,
    "new_version": "2.2.0"
}
```

**POST /addon-admin-import-deck**
```python
# Request (batch import with retry logic)
{
    "deck_id": "uuid",  # or null for new deck
    "cards": [...],     # batch of 500 cards
    "version": "1.0.0",
    "version_notes": "Initial import",
    "clear_existing": false,
    "deck_title": "New Deck Name"  # if creating new
}

# Response
{
    "success": true,
    "deck_id": "uuid",
    "cards_imported": 500,
    "version": "1.0.0"
}
```

### Complete Endpoint List

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/addon-login` | POST | No | Authenticate user |
| `/addon-refresh-token` | POST | No | Refresh access token |
| `/addon-browse-decks` | POST | Yes | Browse available decks |
| `/addon-download-deck` | POST | Yes | Get deck download info |
| `/addon-check-updates` | POST | Yes | Check for updates |
| `/addon-pull-changes` | POST | Yes | Pull card changes |
| `/addon-push-changes` | POST | Yes | Submit suggestions |
| `/addon-manage-subscription` | POST | Yes | Subscribe/unsubscribe |
| `/addon-sync-progress` | POST | Yes | Upload study stats |
| `/addon-check-notifications` | POST | Yes | Get notifications |
| `/addon-get-changelog` | POST | Yes | Get version history |
| `/addon-get-protected-fields` | POST | Yes | Get protected fields |
| `/addon-submit-suggestion` | POST | Yes | Submit card suggestion |
| `/addon-get-card-history` | POST | Yes | Get card version history |
| `/addon-rollback-card` | POST | Yes | Rollback to previous version |
| `/addon-sync-tags` | POST | Yes | Sync card tags |
| `/addon-sync-suspend-state` | POST | Yes | Sync suspend/bury state |
| `/addon-sync-media` | POST | Yes | Sync media files |
| `/addon-sync-note-types` | POST | Yes | Sync note type templates |
| `/addon-create-deck` | POST | Yes | Create collaborative deck |
| `/addon-update-deck` | POST | Yes | Update deck metadata |
| `/addon-delete-user-deck` | POST | Yes | Delete user's deck |
| `/addon-push-deck-cards` | POST | Yes | Push cards to user deck |
| `/addon-get-my-decks` | POST | Yes | List user's created decks |
| `/addon-admin-push-changes` | POST | Admin | Push authoritative changes |
| `/addon-admin-import-deck` | POST | Admin | Import full deck |

---

## Configuration

### Addon Config

Located at: **Tools → Add-ons → AnkiPH → Config**

```json
{
  "api_url": "https://ladvckxztcleljbiomcf.supabase.co/functions/v1",
  "auto_sync_enabled": true,
  "auto_sync_interval_hours": 1,
  "auto_check_updates": true,
  "update_check_interval_hours": 24
}
```

### Storage Locations

#### Profile-Specific Data
Stored in Anki's collection metadata (`collection.anki2`):
- Downloaded decks mapping
- Deck versions
- Last sync timestamps

#### Global Settings
Stored in addon config:
- Access tokens
- User information
- Subscription status
- Protected fields
- Available updates cache

### Protected Fields Configuration

Configure per-deck in Settings → Protected Fields:

```python
# Example: Protect personal notes from sync overwrites
protected_fields = {
    "deck_uuid": ["Personal Notes", "Extra", "My Mnemonics"]
}
```

---

## Development Guide

### Setting Up Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/ankiph-addon.git
   cd ankiph-addon
   ```

2. **Install Anki**
   - Download Anki 24.x or 25.x
   - Ensure PyQt6 is available

3. **Symlink to Anki addons folder**
   ```bash
   # Linux/Mac
   ln -s $(pwd) ~/Anki2/addons21/ankiph_addon
   
   # Windows
   mklink /D "%APPDATA%\Anki2\addons21\ankiph_addon" "C:\path\to\repo"
   ```

4. **Restart Anki**
   - Changes to Python files require restart
   - Use Anki's debug console for live testing

### Code Style Guidelines

- **Python**: Follow PEP 8
- **Naming**: Snake_case for functions, CamelCase for classes
- **Docstrings**: Use Google-style docstrings
- **Type hints**: Add where helpful for clarity

### Adding New Features

#### 1. Add API Endpoint
```python
# In api_client.py
def new_feature(self, param: str) -> Dict[str, Any]:
    """
    Description of what this endpoint does.
    
    Args:
        param: Description of parameter
    
    Returns:
        Response data
    """
    return self.post("/addon-new-feature", json_body={"param": param})
```

#### 2. Add UI Component
```python
# In ui/new_dialog.py
class NewFeatureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Build your UI
        pass
```

#### 3. Wire it up
```python
# In ui/main_dialog.py
def open_new_feature(self):
    from .new_dialog import NewFeatureDialog
    dialog = NewFeatureDialog(self)
    dialog.exec()
```

### Testing

#### Manual Testing Checklist

- [ ] Login/logout flow
- [ ] Deck browsing and filtering
- [ ] Deck download and import
- [ ] Update checking
- [ ] Progress sync
- [ ] Protected fields preservation
- [ ] Conflict resolution
- [ ] Premium deck creation

#### API Testing

Use the test script:
```python
from api_client import api, set_access_token

# Login
result = api.login("test@example.com", "password")
set_access_token(result['access_token'])

# Test endpoint
result = api.browse_decks()
print(result)
```

### Common Development Tasks

#### Debugging Import Issues
```python
# Add at start of deck_importer.py
import traceback
try:
    # your code
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
```

#### Testing Without Server
```python
# Mock API responses in api_client.py
def download_deck(self, deck_id: str):
    # Return mock data for testing
    return {
        "success": True,
        "use_pull_changes": True,
        "deck": {"id": deck_id, "title": "Test Deck"}
    }
```

#### Simulating Large Deck Sync
```python
# Test pagination logic
def test_large_deck_sync():
    offset = 0
    limit = 1000
    all_cards = []
    
    while True:
        result = api.pull_changes(
            deck_id="test-uuid",
            full_sync=True,
            offset=offset,
            limit=limit
        )
        
        cards = result.get('cards', [])
        all_cards.extend(cards)
        
        print(f"Fetched {len(cards)} cards (total: {len(all_cards)})")
        
        if not result.get('has_more'):
            break
        
        offset = result.get('next_offset', offset + limit)
    
    print(f"Total cards: {len(all_cards)}")
```

---

## Troubleshooting

### Common Issues

#### "Session expired" Error
**Cause**: Access token has expired (1 hour validity)

**Solution**:
```
⚖️ AnkiPH → Logout → Login again
```

Or refresh token automatically:
```python
refresh_token = config.get_refresh_token()
result = api.refresh_token(refresh_token)
config.save_tokens(
    result['access_token'],
    result['refresh_token'],
    result['expires_at']
)
```

#### Update Check Fails
**Symptoms**: "Update check failed" message

**Causes**:
1. No internet connection
2. Token expired
3. Server maintenance

**Solution**:
1. Check internet connection
2. Verify login: ⚖️ AnkiPH → Settings
3. Try manual check: ⚖️ AnkiPH → Updates → Check Now

#### Deck Not Syncing
**Symptoms**: Cards don't update after sync

**Debugging**:
1. Check protected fields: Settings → Protected Fields
2. Review sync log: Check Anki console for errors
3. Verify deck tracking:
   ```python
   from config import config
   print(config.get_downloaded_decks())
   ```

#### Import Fails Silently
**Cause**: Orphaned operation (no parent widget)

**Solution**: Ensure parent widget is passed:
```python
# WRONG
import_deck_with_progress(content, name, on_success, on_failure)

# CORRECT
import_deck_with_progress(content, name, on_success, on_failure, parent=self)
```

#### Special Characters in Deck Names
**Cause**: Anki search syntax breaks on `()` and other special chars

**Solution**: Use the escape utility:
```python
from utils import escape_anki_search

deck_name = "Law (2024)"
escaped = escape_anki_search(deck_name)
# Result: "Law \(2024\)"

note_ids = mw.col.find_notes(f'deck:"{escaped}"')
```

#### Large Deck Timeout
**Symptoms**: Import or sync fails for 30k+ card decks

**Solution**: Pagination is built-in:
```python
# Backend automatically paginates
result = api.pull_all_cards(deck_id, progress_callback=update_ui)
# Returns all cards with automatic batching
```

### Error Codes

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| `UNAUTHORIZED` | 401 | Token invalid/expired | Re-login |
| `FORBIDDEN` | 403 | No permission | Check subscription |
| `NOT_FOUND` | 404 | Resource not found | Verify deck ID |
| `VALIDATION_ERROR` | 400 | Bad request | Check input format |
| `RATE_LIMITED` | 429 | Too many requests | Wait and retry |
| `SUBSCRIPTION_REQUIRED` | 403 | Subscription needed | Subscribe at nottorney.com |
| `DECK_LIMIT_REACHED` | 403 | Max decks created | Delete old decks or upgrade |

### Debug Mode

Enable verbose logging:
```python
# In __init__.py, add at top
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs:
- **Tools → Add-ons → AnkiPH → View Files**
- Check `stdout.txt` and `stderr.txt`

### Getting Help

1. **Documentation**: Read this guide thoroughly
2. **API Docs**: See `ankiph_api_docs_Version3.md`
3. **Community**: Visit https://nottorney.com/community
4. **Support**: Contact via https://nottorney.com/help
5. **Issues**: Report bugs with:
   - Anki version
   - Addon version
   - Error messages
   - Steps to reproduce

---

## Version History

### v3.3.0 (December 22, 2025) - CURRENT
🔄 **Subscription-only model**
- Removed legacy collection purchase references
- Added `is_lifetime` flag for grandfathered users
- Removed `owns_collection`, `COLLECTION_OWNER`, `LEGACY` tiers
- Updated all upgrade prompts to subscription-only

### v3.2.0 (December 18, 2025)
🔧 **Stability improvements**
- Fixed deck download/sync with v3.0 pull-changes flow
- Fixed Anki search syntax with special characters
- Improved error handling and loading states
- Better pagination for large decks (32k+ cards)

### v3.1.0 (December 18, 2025)
✨ **Collaborative Deck Management**
- Create up to 10 collaborative decks (subscribers)
- Push up to 500 cards per batch with change tracking
- Manage deck metadata, visibility, and tags
- Delete decks with cascade (cards, subscribers)
- View created decks with creation limits

### v3.0.0 (December 17, 2025)
🎨 **Rebranding and tiered access**
- Rebranded from Nottorney to AnkiPH
- Added tiered access: Lifetime, Subscriber, Free Tier
- Subscription status display in UI
- Upgrade prompts for free tier users
- Modern two-panel deck management UI

### v2.1.0 (December 17, 2025)
🔧 **Maintenance release**
- Synchronized version numbers across all files
- Removed deprecated UI mode toggle
- Cleaned up orphaned single_dialog references
- Updated documentation

### v2.0.0 (December 16, 2025)
✨ **Admin features and simplified UX**
- Admin push changes and import deck features
- Full sync mode for pull_changes API
- Simplified UX with auto-sync on startup
- Settings dialog with admin tab

### v1.1.0 (December 15, 2025)
✨ **Modern UI and notifications**
- Automatic update checking on startup
- Modern tabbed interface (My Decks, Browse, Updates, Notifications)
- Notifications system with unread counts
- Batch download support (up to 10 decks)

### v1.0.x (Initial Release)
🎉 **Core features**
- Basic deck download and import
- Progress sync to server
- Login/logout authentication
- Simple dialog UI

---

## Appendix

### Keyboard Shortcuts

No keyboard shortcuts currently implemented. Future enhancement.

### File Locations

**Addon Files**:
- Windows: `%APPDATA%\Anki2\addons21\AnkiPH_Addon`
- Mac: `~/Library/Application Support/Anki2/addons21/AnkiPH_Addon`
- Linux: `~/.local/share/Anki2/addons21/AnkiPH_Addon`

**Config**:
- Addon settings: `addons21/AnkiPH_Addon/config.json`
- User overrides: `addons21/AnkiPH_Addon/meta.json`

**Profile Data**:
- Collection metadata: `collection.anki2` (SQLite)
- Key: `ankiph_downloaded_decks`

### External Dependencies

All dependencies bundled with addon:
- `requests` (HTTP client) - fallback to `urllib` if unavailable
- PyQt6 (GUI) - provided by Anki
- No external packages required

### Migration Notes

#### From v2.x to v3.x
- **Breaking**: `owns_collection` field removed
- **Breaking**: `COLLECTION_OWNER` access tier removed
- **Migration**: Existing users auto-detected as `is_lifetime=true`
- **Action Required**: None - automatic migration on login

#### From v1.x to v2.x
- **UI Mode**: `minimal` mode removed, all users now use tabbed UI
- **Migration**: Automatic via `migrated_to_v1_1_0` flag
- **Action Required**: None - automatic on first run

### Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes following code style guidelines
4. Test thoroughly (see Testing section)
5. Submit a pull request with:
   - Clear description of changes
   - Screenshots if UI changes
   - Test results

### License

Copyright (c) 2025 AnkiPH Team. All rights reserved.

This addon is proprietary software for AnkiPH subscribers.

---

## Contact & Support

- **Homepage**: https://nottorney.com
- **Documentation**: https://nottorney.com/docs
- **Support**: https://nottorney.com/help
- **Community**: https://nottorney.com/community
- **Pricing**: https://nottorney.com/pricing

---

**Last Updated**: December 22, 2025  
**Document Version**: 1.0  
**Maintained By**: AnkiPH Development Team