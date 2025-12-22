# AnkiPH Anki Addon

**Version:** 3.3.0  
**Updated:** December 18, 2025  
**Compatible with:** Anki 24.x - 25.x (PyQt6)

---

## Overview

AnkiPH is an AnkiHub-style deck syncing addon for Philippine students. It provides:

- **Deck subscription & syncing** - Subscribe to decks and receive updates automatically
- **Automatic updates** - Checks for deck updates on startup
- **Progress tracking** - Syncs study progress to server
- **Notifications** - Receive announcements from deck publishers
- **Subscription-only access** - Student (₱100/mo), Regular (₱149/mo), Lifetime plans

---

## Quick Start

1. **Install** the addon in Anki
2. **Restart** Anki
3. **Open** → ⚖️ AnkiPH (in top menu bar)
4. **Login** with your account
5. **Subscribe** to access all 33,709+ cards
6. **Browse** and download decks
7. **Study** - Updates sync automatically on startup

---

## Features

### Core Features (Working)
- ✅ Authentication (login/logout with JWT)
- ✅ Deck browsing and download
- ✅ Batch download (up to 10 decks)
- ✅ Automatic update checking
- ✅ Manual update application
- ✅ Notifications system
- ✅ Progress syncing
- ✅ Subscription access tiers (Lifetime, Student, Regular, Free)

### Advanced Features (UI Ready, API Verification Needed)
- ⚠️ Push/Pull card changes
- ⚠️ Conflict resolution
- ⚠️ Protected fields
- ⚠️ Card suggestions
- ⚠️ Card history & rollback
- ⚠️ Tag sync
- ⚠️ Suspend state sync
- ⚠️ Media sync
- ⚠️ Note type sync

### Admin Features
- 🔒 Push changes to database
- 🔒 Import full decks

### Premium Features (v3.1 - Collaborative Decks)
- ✅ Create collaborative decks (5-10 max depending on tier)
- ✅ Push cards to your decks (max 500/batch, with change tracking)
- ✅ Manage deck metadata, visibility & tags
- ✅ Delete decks with cascade (cards, subscribers)
- ✅ View created decks with creation limits


---

## File Structure

```
AnkiPH_Addon/
├── __init__.py              # Entry point (v3.0.0)
├── api_client.py            # API client (20+ endpoints)
├── config.py                # Configuration management
├── deck_importer.py         # .apkg import
├── sync.py                  # Progress syncing
├── update_checker.py        # Update service
├── config.json              # Default config
├── manifest.json            # Addon metadata
└── ui/
    ├── __init__.py
    ├── main_dialog.py       # Simple unified dialog
    ├── tabbed_dialog.py     # Full UI (My Decks, Browse, Updates, Notifications)
    ├── settings_dialog.py   # Settings + Admin features
    ├── sync_dialog.py       # Push/Pull changes
    ├── history_dialog.py    # Card history viewer
    ├── suggestion_dialog.py # Card suggestions
    └── advanced_sync_dialog.py # Tags, suspend, media, note types
```

---

## Configuration

Access config via: **Tools → Add-ons → AnkiPH → Config**

```json
{
  "auto_check_updates": true,
  "update_check_interval_hours": 24,
  "auto_sync_enabled": true
}
```

---

## Troubleshooting

### "Update check failed"
1. Check internet connection
2. Verify you're logged in
3. Try: ⚖️ AnkiPH → Check for Updates

### "Session expired"
1. Open AnkiPH
2. Click Logout then Login again

---

## Version History

### v3.3.0 (December 18, 2025) - CURRENT
- 🔄 **Subscription-only model** - Removed legacy collection purchase references
- ✨ **Lifetime Subscriber tier** - Grandfathered users get permanent access
- ✨ **is_lifetime flag** - Server returns is_lifetime for lifetime subscribers
- 🔧 Removed `owns_collection`, `COLLECTION_OWNER`, `LEGACY` access tiers
- 🔧 Updated upgrade prompts to subscription-only messaging

### v3.2.0 (December 18, 2025)
- 🔧 Fixed deck download/sync with v3.0 pull-changes flow
- 🔧 Fixed Anki search syntax with special characters
- 🔧 Improved error handling and loading states

### v3.1.0 (December 18, 2025)
- ✨ **Collaborative Deck Management** - Create, update, delete your own decks
- ✨ **Push Deck Cards** - Upload up to 500 cards per batch with change tracking
- ✨ **Deck Creation Limits** - 10 decks for Subscribers
- 🔧 Fixed `push_deck_cards()` to use `delete_missing` parameter
- 📝 Updated API documentation with complete endpoint specs

### v3.0.0 (December 17, 2025)
- 🎨 Rebranded from Nottorney to AnkiPH
- ✨ Added tiered access support (Lifetime, Subscriber, Free Tier)
- ✨ Subscription status display in UI
- ✨ Upgrade prompts for free tier users

### v2.1.0 (December 17, 2025)
- 🔧 Synchronized version numbers across all files
- 🔧 Removed deprecated UI mode toggle (always tabbed now)
- 🔧 Cleaned up orphaned single_dialog references
- 📝 Updated documentation

### v2.0.0 (December 16, 2025)
- ✨ Admin features (push changes, import decks)
- ✨ Full sync mode for pull_changes
- ✨ Simplified UX (auto-sync on startup)

### v1.1.0 (December 15, 2025)
- ✨ Automatic update checking
- ✨ Modern tabbed interface
- ✨ Notifications system
- ✨ Batch download support

### v1.0.x (Initial)
- Basic deck download
- Progress sync
- Login/logout

---

## Support

- **Homepage:** https://nottorney.com
- **API Documentation:** See `ankiph_api_docs_Version3.md`

---

**Stay Updated. Study Smart! 📚⚖️**