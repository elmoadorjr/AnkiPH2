Case 1: I attempted to Subscribe to an Anki Deck via Addon - Result: Subscribe Failed - No Download URL

Case 2: I deleted a previously installed Deck - Deck Management - still shows Installed and Up to date.

Case 3: I unsubscribed from a Deck - Result: Deck is still subscribed - And still gives option to Unsubscribe.

Case 4: I downloaded a 23 card deck - Result: it worked but there was a short freeze - and is bad for UX.

Case 5: I click the AnkiPH login_dialog's Forgot Password and Register Now links - No dedicated Forgot Password page or Forgot Password dialog in webapp not triggered AnD/or SignUp tab in /auth not opened.

case 6: I sign up - Deck rebuild - is slow - delayed at least 1 second.

case 7: Im on free tier limited access account - i click browse decks in deck management - and nottorney collection which is a paid deck is displayed - i click install - it sorta allows me but there is an error from case 1 - in which case IF case 1 was fixed - and downloading a paid deck did allow?? then it would be broken - because free tier accounts - cant download paid decks.

Case 8: Im not logged in- im aware of this - i click AnkiPH button in topnav - it shows me a blank Dialog that has a button Sign IN - I click it and leads me to Login_dialog - but i feel like this part is unnecessary - and interferes with user UX - because if im not logged in - why not just call Login_dialog first.



# AnkiPH Addon - Bug Fixes & Solutions

## Critical Issues Analysis

### Case 1: Subscribe Failed - No Download URL ❌

**Root Cause:**
The v3.0 API changed to use `pull_changes` flow instead of direct `.apkg` downloads. The code in `main_dialog.py` has logic for both flows, but there's a critical check missing.

**Location:** `ui/main_dialog.py`, line ~560 in `_do_install()`

**Issue:**
```python
# V3.0 flow: use pull-changes for card data
if result.get('use_pull_changes'):
    self.sync_btn.setText("Fetching cards...")
    QApplication.processEvents()
    self._install_from_pull_changes(deck_id, result)
    return

# Legacy flow: download .apkg file
if result.get('download_url'):
    # ... download code
    return

raise Exception("No download method available")  # ← This is triggered!
```

**Fix:**
The API response likely has `success: true` but no `use_pull_changes` or `download_url` field. Add better error handling:

```python
# After api.download_deck(deck_id)
if not result.get('success'):
    raise Exception(result.get('error', 'Download failed'))

# Check which flow to use
if result.get('use_pull_changes', False):
    # V3.0 flow
    self._install_from_pull_changes(deck_id, result)
    return
elif result.get('download_url'):
    # Legacy flow
    # ... download code
    return
else:
    # Log the response for debugging
    print(f"API Response: {result}")
    raise Exception(
        "Server returned neither pull_changes nor download_url. "
        f"Response keys: {list(result.keys())}"
    )
```

---

### Case 2: Deleted Deck Still Shows as Installed ❌

**Root Cause:**
The `deck_exists()` check is cached or not properly detecting deleted decks.

**Location:** `ui/main_dialog.py`, line ~200 in `load_decks()`

**Issue:**
```python
is_installed = False

if anki_deck_id and mw.col:
    # Use proper deck_exists check
    is_installed = deck_exists(anki_deck_id)  # ← This returns True even after deletion!
```

**Fix:**
The `deck_exists()` function in `deck_importer.py` needs to handle the case where `decks.get()` returns `None`:

```python
# In deck_importer.py
def deck_exists(deck_id: int) -> bool:
    """Check if a deck exists"""
    try:
        deck_id = int(deck_id)
        if not mw.col:
            return False
        
        deck = mw.col.decks.get(deck_id)
        
        # Check if deck is None or was deleted (mod == -1)
        if deck is None:
            return False
        
        # Check if deck is marked as deleted
        if deck.get('mod') == -1:
            return False
            
        return True
    except Exception as e:
        print(f"✗ Error checking deck existence for {deck_id}: {e}")
        return False
```

**Additional Fix in main_dialog.py:**
Add auto-cleanup after loading:

```python
def load_decks(self):
    """Load subscribed decks"""
    self.deck_list.clear()
    
    try:
        # Clean up deleted decks FIRST
        from ..deck_importer import deck_exists
        downloaded_decks = config.get_downloaded_decks()
        
        decks_to_remove = []
        for deck_id, deck_info in downloaded_decks.items():
            anki_deck_id = deck_info.get('anki_deck_id')
            if anki_deck_id and not deck_exists(anki_deck_id):
                decks_to_remove.append(deck_id)
        
        # Remove invalid entries
        for deck_id in decks_to_remove:
            config.remove_downloaded_deck(deck_id)
            print(f"✓ Auto-removed deleted deck: {deck_id}")
        
        # Now reload fresh data
        downloaded_decks = config.get_downloaded_decks()
        # ... rest of load logic
```

---

### Case 3: Unsubscribe Doesn't Remove Deck ❌

**Root Cause:**
The unsubscribe button calls `config.remove_downloaded_deck()` but doesn't call the API to unsubscribe from the server.

**Location:** `ui/main_dialog.py`, line ~437 in `unsubscribe_deck()`

**Fix:**
```python
def unsubscribe_deck(self):
    """Unsubscribe from deck"""
    if not self.selected_deck:
        return
    
    deck_id = self.selected_deck.get('deck_id')
    deck_name = self.selected_deck.get('name', 'Unknown')
    
    reply = QMessageBox.question(
        self, "Confirm Unsubscribe",
        f"Remove '{deck_name}' from your subscribed decks?\n\n"
        "The cards will remain in Anki but you won't receive updates.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        try:
            # Call API to unsubscribe from server
            token = config.get_access_token()
            if token:
                set_access_token(token)
                api.manage_subscription(action="unsubscribe", deck_id=deck_id)
                print(f"✓ Unsubscribed from server: {deck_id}")
        except Exception as e:
            print(f"⚠ Server unsubscribe failed (non-critical): {e}")
        
        # Remove from local config
        config.remove_downloaded_deck(deck_id)
        
        # Reset UI
        self.selected_deck = None
        self.detail_title.setText("Select a deck")
        self.open_web_btn.setEnabled(False)
        self.unsubscribe_btn.setEnabled(False)
        self.install_status.setText("")
        self.sync_btn.setVisible(False)
        self.info_container.setVisible(False)
        
        # Reload deck list
        self.load_decks()
        tooltip("Deck unsubscribed")
```

---

### Case 4: 23-Card Deck Causes UI Freeze ⚠️

**Root Cause:**
`import_deck_with_progress()` runs on main thread, blocking the UI.

**Location:** `deck_importer.py`, line ~148

**Current Implementation:**
```python
def import_deck_with_progress(deck_content: bytes, deck_name: str, 
                              on_success=None, on_failure=None, parent=None):
    """Import with progress tracking"""
    # Uses QueryOp for background operations
    op = QueryOp(
        parent=parent,
        op=lambda col: import_in_background(),  # ← Runs in background
        success=on_done
    )
    op.failure(on_error)
    op.run_in_background()  # ← Should work but may have issues
```

**Issue:**
The operation might be synchronous for small files. Add explicit progress dialog:

**Fix in main_dialog.py:**
```python
def _do_install(self, deck_id, deck_name, use_recommended=True):
    """Perform the actual deck installation"""
    # Show loading state
    self.setCursor(Qt.CursorShape.WaitCursor)
    self.sync_btn.setEnabled(False)
    self.sync_btn.setText("Downloading...")
    
    # Create progress dialog BEFORE starting
    progress = QProgressDialog(
        f"Installing {deck_name}...\n\nPlease wait.",
        None,  # No cancel button
        0, 0,  # Indeterminate
        self
    )
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setWindowTitle("Installing Deck")
    progress.setMinimumDuration(0)  # Show immediately
    progress.show()
    
    # Force UI update
    QApplication.processEvents()
    
    try:
        # ... download logic
        
        def on_success(anki_deck_id):
            progress.close()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # ... rest of success logic
        
        def on_failure(error_msg):
            progress.close()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # ... rest of failure logic
        
        import_deck_with_progress(
            deck_content, deck_name,
            on_success=on_success,
            on_failure=on_failure,
            parent=self
        )
    except Exception as e:
        progress.close()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        # ... error handling
```

---

### Case 5: Forgot Password / Register Links Don't Work ❌

**Root Cause:**
URLs point to `/auth` but don't specify which tab or trigger the right dialog.

**Location:** `constants.py`, lines 28-29

**Current:**
```python
REGISTER_URL: Final[str] = f"{BASE_URL}/auth"
FORGOT_PASSWORD_URL: Final[str] = f"{BASE_URL}/auth"
```

**Fix:**
```python
# Add URL fragments or query params to specify the correct tab/mode
REGISTER_URL: Final[str] = f"{BASE_URL}/auth?mode=signup"
FORGOT_PASSWORD_URL: Final[str] = f"{BASE_URL}/auth?mode=forgot-password"

# OR use dedicated routes if your webapp has them:
REGISTER_URL: Final[str] = f"{BASE_URL}/signup"
FORGOT_PASSWORD_URL: Final[str] = f"{BASE_URL}/forgot-password"
```

**Also Update login_dialog.py:**
```python
# Line ~115
register_link.clicked.connect(lambda: webbrowser.open(REGISTER_URL))

# Line ~133
forgot_link.clicked.connect(lambda: webbrowser.open(FORGOT_PASSWORD_URL))
```

---

### Case 6: Sign In → Deck Rebuild Slow (1+ second delay) ⚠️

**Root Cause:**
After login, the entire dialog rebuilds with `_rebuild_ui()`, which:
1. Destroys all widgets
2. Recreates everything
3. Loads data from API

**Location:** `ui/main_dialog.py`, line ~82

**Fix - Optimize Rebuild:**
```python
def _rebuild_ui(self):
    """Rebuild UI after login (OPTIMIZED)"""
    # Don't destroy everything - just swap content
    if self.layout():
        old_layout = self.layout()
        
        # Remove only the main content widget
        while old_layout.count():
            child = old_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    # Create new layout
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    # Setup tabbed UI (will load data async)
    self.setup_tabbed_ui(layout)
    
    self.setLayout(layout)
    
    # Apply styles once
    self.apply_styles()
    
    # Don't block - let tabs load data in background
    print("✓ UI rebuilt")
```

**Better Solution - Don't Rebuild at All:**
Instead of rebuilding, just close the login dialog and reopen main dialog:

```python
# In main_dialog.py, line ~451 in show_login():
def show_login(self):
    """Show login dialog and rebuild UI on success"""
    from .login_dialog import LoginDialog
    dialog = LoginDialog(self)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        tooltip("Login successful!")
        # Instead of rebuilding, close this dialog and reopen
        self.accept()  # Close current dialog
        # The user will click AnkiPH again to see their decks
```

---

### Case 7: Free Tier Can Browse/Download Paid Decks ❌

**Root Cause:**
Access tier check is missing in `browse_decks()` and `_do_install()`.

**Location:** `ui/main_dialog.py`, line ~286 in `load_browse_decks()`

**Fix:**
```python
def load_browse_decks(self):
    """Load available decks"""
    # ... existing code ...
    
    if "decks" in result or result.get('success'):
        decks = result.get('decks', [])
        self.all_decks = decks
        
        downloaded_decks = config.get_downloaded_decks()
        user_data = config.get_user()  # Get user subscription status
        
        for deck in decks:
            deck_id = deck.get('id')
            deck_name = deck.get('title') or deck.get('name', 'Unknown Deck')
            deck_version = deck.get('version', '1.0')
            
            # Check access tier
            from ..api_client import check_access
            access_tier = check_access(user_data, deck)
            
            if access_tier is None:
                # User has NO access to this deck
                display_text = f"🔒 {deck_name} (v{deck_version}) - Subscription Required"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, deck)
                item.setForeground(Qt.GlobalColor.gray)
                item.setToolTip("Subscribe to AnkiPH to access this deck")
            else:
                # User has access
                is_downloaded = deck_id in downloaded_decks
                display_text = f"{'✓ ' if is_downloaded else ''}{deck_name} (v{deck_version})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, deck)
                
                if is_downloaded:
                    item.setForeground(Qt.GlobalColor.darkGreen)
            
            self.browse_list.addItem(item)
```

**Also add check in download:**
```python
def download_selected_deck(self):
    """Download selected deck from browse tab"""
    current = self.browse_list.currentItem()
    if not current:
        QMessageBox.warning(self, "No Selection", "Please select a deck.")
        return
    
    deck = current.data(Qt.ItemDataRole.UserRole)
    
    # Check if user has access
    user_data = config.get_user()
    from ..api_client import check_access, show_upgrade_prompt
    access_tier = check_access(user_data, deck)
    
    if access_tier is None:
        # No access - show upgrade prompt
        show_upgrade_prompt()
        return
    
    self._download_deck(deck)
```

---

### Case 8: Unnecessary Blank Dialog Before Login ❌

**Root Cause:**
Main dialog shows a "Sign In" button screen before showing login dialog.

**Location:** `__init__.py`, line ~55 in `show_main_dialog()`

**Fix - Skip Intermediate Screen:**
```python
def show_main_dialog():
    """Show main dialog (or login if not authenticated)"""
    global _dialog_instance
    
    try:
        # Check if user is logged in FIRST
        if not config.is_logged_in():
            # Show login dialog directly
            from .ui.login_dialog import show_login_dialog
            if show_login_dialog(mw):
                # Login successful - now show main dialog
                _dialog_instance = MainDialog(mw)
                _dialog_instance.exec()
            else:
                # Login cancelled or failed
                return
        else:
            # Already logged in - show main dialog
            _dialog_instance = MainDialog(mw)
            _dialog_instance.exec()
        
        # Sync progress after dialog closes if logged in
        if config.is_logged_in():
            try:
                token = config.get_access_token()
                if token:
                    set_access_token(token)
                sync.sync_progress()
                print("✓ Progress synced successfully")
            except Exception as e: 
                print(f"Sync failed (non-critical): {e}")
    except Exception as e:
        showInfo(f"Error opening AnkiPH:\n{str(e)}")
        print(f"Dialog error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        _dialog_instance = None
```

**Remove the login prompt from main_dialog.py:**
```python
# In main_dialog.py, remove lines ~118-135 (_create_login_prompt)
# and modify setup_ui():

def setup_ui(self):
    """Setup the two-panel UI"""
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    # Assume user is logged in (checked in __init__.py)
    # Top action bar
    layout.addWidget(self._create_action_bar())
    
    # Main content
    layout.addWidget(self._create_main_content())
    
    # Bottom status bar
    layout.addWidget(self._create_status_bar())
    
    self.setLayout(layout)
```

---

## Summary of Fixes

| Case | Priority | Status | Fix Complexity |
|------|----------|--------|----------------|
| 1. No Download URL | 🔴 Critical | ❌ Broken | Medium - API response handling |
| 2. Deleted Deck Shows Installed | 🟡 High | ❌ Broken | Easy - Add cleanup logic |
| 3. Unsubscribe Doesn't Work | 🟡 High | ❌ Broken | Easy - Call API endpoint |
| 4. UI Freeze (23 cards) | 🟢 Medium | ⚠️ Minor | Easy - Add progress dialog |
| 5. Links Don't Open Correct Page | 🟢 Medium | ❌ Broken | Easy - Fix URLs |
| 6. Slow Rebuild After Login | 🟢 Low | ⚠️ Minor | Medium - Optimize or skip |
| 7. Free Tier Access Control | 🔴 Critical | ❌ Broken | Medium - Add tier checks |
| 8. Unnecessary Intermediate Screen | 🟢 Low | ⚠️ UX | Easy - Skip blank dialog |

---

## Testing Checklist

After implementing fixes:

- [ ] Case 1: Subscribe to deck → Should download successfully
- [ ] Case 2: Delete deck in Anki → Should disappear from "My Decks"
- [ ] Case 3: Unsubscribe → Should remove from server & local
- [ ] Case 4: Download small deck → Should show progress, no freeze
- [ ] Case 5: Click "Register" → Should open signup tab/page
- [ ] Case 5: Click "Forgot Password" → Should open recovery page
- [ ] Case 6: Login → Should load fast (<500ms)
- [ ] Case 7: Free tier → Should NOT see/download paid decks
- [ ] Case 8: Click AnkiPH when logged out → Should go straight to login

---

## Implementation Priority

### Phase 1 - Critical Fixes (Ship ASAP)
1. **Case 1** - No Download URL
2. **Case 7** - Free Tier Access Control
3. **Case 3** - Unsubscribe Functionality

### Phase 2 - High Priority
4. **Case 2** - Auto-cleanup Deleted Decks
5. **Case 5** - Fix Registration Links

### Phase 3 - UX Improvements
6. **Case 8** - Skip Intermediate Login Screen
7. **Case 4** - Improve Progress Feedback
8. **Case 6** - Optimize Rebuild Performance

---

**Estimated Implementation Time:**
- Phase 1: 3-4 hours
- Phase 2: 2-3 hours
- Phase 3: 2-3 hours
- **Total: ~8-10 hours**