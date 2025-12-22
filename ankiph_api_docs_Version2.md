# AnkiPH Anki Add-on API Documentation

**Version:** 3.1.0  
**Base URL:** `https://ladvckxztcleljbiomcf.supabase.co/functions/v1`  
**Last Updated:** December 18, 2025

---

## Authentication

Uses JWT Bearer authentication. Include in all requests:
```
Authorization: Bearer <access_token>
```

| Token | Validity | Usage |
|-------|----------|-------|
| `access_token` | 1 hour | API requests |
| `refresh_token` | 7 days | Get new access tokens |

---

## Error Response Format

All errors return:
```json
{
  "success": false,
  "message": "Human-readable error message"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| `401` | Invalid/expired token |
| `403` | No access (deck not owned) |
| `400` | Bad request |
| `500` | Server error |

---

## Endpoints

### 1. Login
**POST** `/addon-login`

Request:
```json
{ "email": "user@example.com", "password": "..." }
```

Response:
```json
{
  "success": true,
  "access_token": "jwt...",
  "refresh_token": "...",
  "expires_at": "ISO8601",
  "user": {
    "id": "uuid",
    "email": "...",
    "is_admin": false,
    "has_subscription": true,
    "subscription_expires_at": "ISO8601",
    "subscription_tier": "premium",
    "can_create_decks": true,
    "created_decks_count": 3,
    "max_decks_allowed": 10
  }
}
```

---

### 2. Refresh Token
**POST** `/addon-refresh-token`

Request:
```json
{ "refresh_token": "..." }
```

---

### 3. Get Purchases
**POST** `/addon-get-purchases`

Response:
```json
{
  "success": true,
  "decks": [
    { "id": "uuid", "name": "...", "version": "1.0.0" }
  ]
}
```

---

### 4. Download Deck
**POST** `/addon-download-deck`

Request:
```json
{ "deck_id": "uuid" }
```

---

### 5. Pull Changes
**POST** `/addon-pull-changes`

Request:
```json
{
  "deck_id": "uuid",
  "since": "ISO8601 (optional)",
  "last_change_id": "uuid (optional)",
  "full_sync": false
}
```

Response (incremental):
```json
{
  "success": true,
  "full_sync": false,
  "changes": [
    {
      "change_id": "uuid",
      "card_guid": "anki-note-guid",
      "field_name": "Front",
      "old_value": "...",
      "new_value": "...",
      "change_type": "modify",
      "is_protected": false
    }
  ],
  "conflicts": [
    {
      "card_guid": "guid",
      "field_name": "Back",
      "local_value": "User's version",
      "server_value": "Server's version",
      "is_protected": false
    }
  ],
  "protected_fields": ["Personal Notes"],
  "has_more": false
}
```

Response (full_sync=true):
```json
{
  "success": true,
  "full_sync": true,
  "cards": [...],
  "total_cards": 1000,
  "deck_version": "1.0.0"
}
```

---

### 6. Push Changes
**POST** `/addon-push-changes`

Request:
```json
{
  "deck_id": "uuid",
  "changes": [
    {
      "card_guid": "guid",
      "field_name": "Front",
      "old_value": "...",
      "new_value": "..."
    }
  ],
  "version": "1.0.1"
}
```

Response:
```json
{
  "success": true,
  "changes_pushed": 5,
  "last_change_id": "uuid"
}
```

---

### 7. Sync Tags
**POST** `/addon-sync-tags`

Request:
```json
{
  "deck_id": "uuid",
  "action": "pull" | "push",
  "changes": [{ "card_guid": "...", "tags": ["tag1"] }],
  "since": "ISO8601 (optional)"
}
```

Response:
```json
{
  "success": true,
  "tags_added": 5,
  "tags_removed": 2
}
```

---

### 8. Sync Suspend State
**POST** `/addon-sync-suspend-state`

Request:
```json
{
  "deck_id": "uuid",
  "action": "pull" | "push",
  "changes": [{ "card_guid": "...", "is_suspended": true, "is_buried": false }]
}
```

Response:
```json
{
  "success": true,
  "cards_updated": 10
}
```

---

### 9. Sync Media
**POST** `/addon-sync-media`

Request:
```json
{
  "deck_id": "uuid",
  "action": "list" | "download" | "upload" | "get_upload_url" | "confirm_upload",
  "file_name": "image.png",
  "file_hash": "sha256..."
}
```

Response (download):
```json
{
  "success": true,
  "files": [{ "file_name": "...", "url": "signed-url" }],
  "files_downloaded": 5,
  "files_uploaded": 0
}
```

---

### 10. Sync Note Types
**POST** `/addon-sync-note-types`

Request:
```json
{
  "deck_id": "uuid",
  "action": "get" | "push",
  "note_types": []
}
```

Response:
```json
{
  "success": true,
  "note_types": [...],
  "types_updated": 2
}
```

---

### 11. Submit Suggestion
**POST** `/addon-submit-suggestion`

Request:
```json
{
  "deck_id": "uuid",
  "card_guid": "guid",
  "field_name": "Front",
  "current_value": "...",
  "suggested_value": "...",
  "reason": "Typo fix"
}
```

---

### 12. Protected Fields
**GET/POST** `/addon-protected-fields`

Get:
```json
{ "deck_id": "uuid" }
```

Set:
```json
{
  "deck_id": "uuid",
  "fields": ["Personal Notes", "Extra"]
}
```

---

## Collaborative Deck Management (v3.1 - Premium)

Premium subscribers can create and manage their own collaborative decks.

**Deck Limits:**
| Tier | Max Decks |
|------|-----------|
| Collection Owner | 10 |
| Premium Subscriber | 5 |

### 13. Create Deck
**POST** `/addon-create-deck`

Request:
```json
{
  "title": "My Constitutional Law Notes",
  "description": "Personal notes for political law",
  "bar_subject": "political_law",
  "is_public": true,
  "tags": ["political", "law", "consti"]
}
```

Response:
```json
{
  "success": true,
  "deck": {
    "id": "uuid",
    "title": "My Constitutional Law Notes",
    "description": "...",
    "bar_subject": "political_law",
    "is_public": true,
    "is_verified": false,
    "card_count": 0,
    "subscriber_count": 0,
    "version": "1.0.0",
    "tags": ["political", "law", "consti"],
    "created_at": "2024-12-18T10:00:00Z",
    "updated_at": "2024-12-18T10:00:00Z"
  }
}
```

### 14. Update Deck
**POST** `/addon-update-deck`

Request:
```json
{
  "deck_id": "uuid",
  "title": "Updated Title",
  "description": "New description",
  "is_public": false,
  "tags": ["updated", "tags"]
}
```

### 15. Delete User Deck
**POST** `/addon-delete-user-deck`

Request:
```json
{ "deck_id": "uuid", "confirm": true }
```

Response:
```json
{
  "success": true,
  "message": "Deck deleted successfully",
  "deleted": {
    "deck_id": "uuid",
    "title": "Deleted Deck",
    "cards_deleted": 150,
    "subscribers_removed": 25
  }
}
```

### 16. Push Deck Cards
**POST** `/addon-push-deck-cards` (max 500 cards/request)

Request:
```json
{
  "deck_id": "uuid",
  "cards": [
    {
      "card_guid": "anki-note-guid-123",
      "note_type": "Basic",
      "fields": { "Front": "Question?", "Back": "Answer." },
      "tags": ["chapter1", "important"],
      "subdeck_path": "Chapter 1"
    }
  ],
  "delete_missing": false,
  "version": "1.0.1"
}
```

Response:
```json
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

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `deck_id` | uuid | Required. Your deck ID |
| `cards` | array | Required. Max 500 cards per batch |
| `delete_missing` | bool | If true, delete cards not in list |
| `version` | string | Optional. Auto-increments if not provided |

### 17. Get My Decks
**POST** `/addon-get-my-decks`

Response:
```json
{
  "success": true,
  "decks": [
    {
      "id": "uuid",
      "title": "My Constitutional Law Notes",
      "description": "...",
      "bar_subject": "political_law",
      "card_count": 157,
      "subscriber_count": 25,
      "is_public": true,
      "is_verified": false,
      "version": "1.0.1",
      "tags": ["political", "law"],
      "image_url": "...",
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-18T10:30:00Z"
    }
  ],
  "can_create_more": true,
  "created_decks_count": 3,
  "max_decks": 10
}
```

---

## Changelog

### v3.1.0 (December 2024)
- **ENHANCED:** Push Deck Cards uses `delete_missing` parameter
- **ENHANCED:** Login response includes deck creation fields
- **ENHANCED:** Get My Decks returns `created_decks_count`

### v3.0.0 (December 2024)
- **NEW:** Collaborative deck management endpoints
- **NEW:** `can_create_decks` in login response

### v2.1.0
- `addon-pull-changes`: Returns `change_id`, conflicts use `local_value`/`server_value`
- All sync endpoints: Use `action` parameter
- Response format standardized