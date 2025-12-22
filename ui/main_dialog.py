"""
Deck Management Dialog for AnkiPH Addon
AnkiHub-style two-panel layout with deck list and details
Version: 3.3.0 - FIXED: Sign in loop issue
"""

import webbrowser
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, Qt,
    QWidget, QSplitter, QFrame, QCheckBox, QSizePolicy, QApplication
)
from aqt import mw
from aqt.utils import showInfo, tooltip

from ..api_client import api, set_access_token, AnkiPHAPIError, show_upgrade_prompt, check_access
from ..config import config
from ..deck_importer import import_deck
from ..utils import escape_anki_search
from ..update_checker import update_checker
from ..constants import HOMEPAGE_URL, TERMS_URL, PRIVACY_URL, PLANS_URL, COMMUNITY_URL


class DeckManagementDialog(QDialog):
    """AnkiHub-style two-panel deck management dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AnkiPH | Deck Management")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)
        self.selected_deck = None
        self.all_decks = []  # Store deck data for filtering
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup the two-panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Check login state
        if not config.is_logged_in():
            layout.addWidget(self._create_login_prompt())
        else:
            # Top action bar (only when logged in)
            layout.addWidget(self._create_action_bar())
            
            # Main content - two panel splitter
            layout.addWidget(self._create_main_content())
            
            # Bottom status bar
            layout.addWidget(self._create_status_bar())
        
        self.setLayout(layout)
    
    def _rebuild_ui(self):
        """Rebuild the UI (used after login to refresh in-place)"""
        # Clear existing layout
        if self.layout():
            old_layout = self.layout()
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            QWidget().setLayout(old_layout)
        
        # Rebuild
        self.setup_ui()
        self.apply_styles()
    
    def _create_action_bar(self):
        """Create top action bar with Browse and Create buttons"""
        bar = QWidget()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # Browse Decks button (primary)
        browse_btn = QPushButton("🔗 Browse Decks")
        browse_btn.setObjectName("primaryBtn")
        browse_btn.clicked.connect(self.browse_decks)
        layout.addWidget(browse_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self.load_decks)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # Create Deck button (secondary/outline)
        create_btn = QPushButton("+ Create AnkiPH Deck")
        create_btn.setObjectName("secondaryBtn")
        create_btn.clicked.connect(self.create_deck)
        layout.addWidget(create_btn)
        
        return bar
    
    def _create_login_prompt(self):
        """Create login prompt for unauthenticated users"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel("Please sign in to manage your decks")
        msg.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        
        login_btn = QPushButton("Sign In")
        login_btn.setObjectName("primaryBtn")
        login_btn.setFixedWidth(200)
        login_btn.clicked.connect(self.show_login)
        layout.addWidget(login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return container
    
    def _create_main_content(self):
        """Create two-panel splitter layout"""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        
        # Left panel - deck list
        left_panel = self._create_deck_list_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - deck details
        self.details_panel = self._create_details_panel()
        splitter.addWidget(self.details_panel)
        
        # Set initial sizes (40% left, 60% right)
        splitter.setSizes([280, 420])
        
        return splitter
    
    def _create_deck_list_panel(self):
        """Create left panel with subscribed decks list"""
        panel = QFrame()
        panel.setObjectName("leftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("Subscribed AnkiPH Decks")
        header.setObjectName("panelHeader")
        layout.addWidget(header)
        
        # Deck list
        self.deck_list = QListWidget()
        self.deck_list.setObjectName("deckList")
        self.deck_list.itemClicked.connect(self.on_deck_selected)
        layout.addWidget(self.deck_list)
        
        # Load decks
        self.load_decks()
        
        return panel
    
    def _create_details_panel(self):
        """Create right panel with deck details"""
        panel = QFrame()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        # Deck title
        self.detail_title = QLabel("Select a deck")
        self.detail_title.setObjectName("detailTitle")
        layout.addWidget(self.detail_title)
        
        # Action buttons row
        btn_row = QHBoxLayout()
        
        self.open_web_btn = QPushButton("Open on Web")
        self.open_web_btn.setObjectName("outlineBtn")
        self.open_web_btn.clicked.connect(self.open_on_web)
        self.open_web_btn.setEnabled(False)
        btn_row.addWidget(self.open_web_btn)
        
        self.unsubscribe_btn = QPushButton("Unsubscribe")
        self.unsubscribe_btn.setObjectName("dangerOutlineBtn")
        self.unsubscribe_btn.clicked.connect(self.unsubscribe_deck)
        self.unsubscribe_btn.setEnabled(False)
        btn_row.addWidget(self.unsubscribe_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)
        
        # Deck Options section
        options_header = QLabel("Deck Options")
        options_header.setObjectName("sectionHeader")
        layout.addWidget(options_header)
        
        # Install status
        self.install_status = QLabel("")
        self.install_status.setObjectName("installStatus")
        layout.addWidget(self.install_status)
        
        # Sync/Install button
        self.sync_btn = QPushButton("🔄 Sync to Install")
        self.sync_btn.setObjectName("syncBtn")
        self.sync_btn.clicked.connect(self.sync_install_deck)
        self.sync_btn.setVisible(False)
        layout.addWidget(self.sync_btn)
        
        # Deck info
        self.info_container = QWidget()
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 10, 0, 0)
        info_layout.setSpacing(6)
        
        self.version_label = QLabel("")
        self.cards_label = QLabel("")
        self.updated_label = QLabel("")
        
        for lbl in [self.version_label, self.cards_label, self.updated_label]:
            lbl.setObjectName("infoLabel")
            info_layout.addWidget(lbl)
        
        layout.addWidget(self.info_container)
        self.info_container.setVisible(False)
        
        layout.addStretch()
        
        return panel
    
    def _create_status_bar(self):
        """Create bottom status bar"""
        bar = QWidget()
        bar.setObjectName("statusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # User info
        user = config.get_user()
        email = user.get('email', 'Unknown') if user else 'Unknown'
        user_label = QLabel(f"Logged in as: {email}")
        user_label.setObjectName("statusText")
        layout.addWidget(user_label)
        
        # Subscription status
        status = config.get_access_status_text()
        status_label = QLabel(status)
        status_label.setObjectName("subscriptionBadge" if config.has_full_access() else "freeBadge")
        layout.addWidget(status_label)
        
        layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("linkBtn")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        
        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("linkBtn")
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        
        return bar
    
    def apply_styles(self):
        """Apply dark theme styles matching AnkiHub"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            
            #actionBar {
                background-color: #252525;
                border-bottom: 1px solid #333;
            }
            
            #primaryBtn {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            #primaryBtn:hover {
                background-color: #5a9fe9;
            }
            
            #secondaryBtn {
                background-color: transparent;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
            }
            #secondaryBtn:hover {
                border-color: #888;
                color: #fff;
            }
            
            #leftPanel {
                background-color: #1e1e1e;
                border-right: 1px solid #333;
            }
            
            #panelHeader {
                background-color: #252525;
                color: #fff;
                font-weight: bold;
                font-size: 12px;
                padding: 12px 15px;
                border-bottom: 1px solid #333;
            }
            
            #deckList {
                background-color: #1e1e1e;
                border: none;
                color: #e0e0e0;
                font-size: 13px;
            }
            #deckList::item {
                padding: 10px 15px;
                border-bottom: 1px solid #2a2a2a;
            }
            #deckList::item:selected {
                background-color: #3a5070;
                color: white;
            }
            #deckList::item:hover:!selected {
                background-color: #2a2a2a;
            }
            
            #rightPanel {
                background-color: #1e1e1e;
            }
            
            #detailTitle {
                color: #4a90d9;
                font-size: 18px;
                font-weight: bold;
            }
            
            #outlineBtn {
                background-color: transparent;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            #outlineBtn:hover {
                border-color: #888;
                color: #fff;
            }
            #outlineBtn:disabled {
                color: #555;
                border-color: #333;
            }
            
            #dangerOutlineBtn {
                background-color: transparent;
                color: #e57373;
                border: 1px solid #e57373;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            #dangerOutlineBtn:hover {
                background-color: #e57373;
                color: white;
            }
            #dangerOutlineBtn:disabled {
                color: #555;
                border-color: #333;
            }
            
            #separator {
                color: #333;
            }
            
            #sectionHeader {
                color: #fff;
                font-weight: bold;
                font-size: 13px;
                margin-top: 5px;
            }
            
            #installStatus {
                color: #ffa726;
                font-size: 12px;
            }
            
            #syncBtn {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
            }
            #syncBtn:hover {
                background-color: #5a9fe9;
            }
            
            #infoLabel {
                color: #888;
                font-size: 12px;
            }
            
            #statusBar {
                background-color: #252525;
                border-top: 1px solid #333;
            }
            
            #statusText {
                color: #888;
                font-size: 11px;
            }
            
            #subscriptionBadge {
                background-color: #4CAF50;
                color: white;
                padding: 3px 10px;
                border-radius: 10px;
                font-size: 10px;
            }
            
            #freeBadge {
                background-color: #FF9800;
                color: white;
                padding: 3px 10px;
                border-radius: 10px;
                font-size: 10px;
            }
            
            #linkBtn {
                background: transparent;
                border: none;
                color: #4a90d9;
                font-size: 12px;
                padding: 5px 10px;
            }
            #linkBtn:hover {
                color: #6ab0f9;
                text-decoration: underline;
            }
        """)
    
    # === DATA LOADING ===
    
    def load_decks(self):
        """Load subscribed decks - sync with server first, then show list"""
        self.deck_list.clear()
        
        try:
            # First, sync subscriptions from server
            self._sync_subscriptions_from_server()
            
            downloaded_decks = config.get_downloaded_decks()
            
            if not downloaded_decks:
                item = QListWidgetItem("No decks yet - click Browse Decks")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.deck_list.addItem(item)
                return
            
            # Import deck_exists helper
            from ..deck_importer import deck_exists
            
            for deck_id, deck_info in downloaded_decks.items():
                # Get deck name - prefer server title, fallback to Anki deck name
                anki_deck_id = deck_info.get('anki_deck_id')
                server_title = deck_info.get('title')
                deck_name = server_title or f"Deck {deck_id[:8]}"
                is_installed = False
                
                if anki_deck_id and mw.col:
                    # Use proper deck_exists check
                    is_installed = deck_exists(anki_deck_id)
                    if is_installed and not server_title:
                        # Only use Anki name if no server title
                        try:
                            deck = mw.col.decks.get(int(anki_deck_id))
                            if deck and deck['name'] != 'Default':
                                deck_name = deck['name']
                        except:
                            pass
                
                # Show install status in list (only show ⚠ for not installed)
                prefix = "" if is_installed else "⚠ "
                item = QListWidgetItem(f"{prefix}{deck_name}")
                item.setData(Qt.ItemDataRole.UserRole, {
                    'deck_id': deck_id,
                    'info': deck_info,
                    'name': deck_name,
                    'is_installed': is_installed
                })
                self.deck_list.addItem(item)
        
        except Exception as e:
            print(f"Error loading decks: {e}")
    
    def _sync_subscriptions_from_server(self):
        """Sync subscriptions from server to local config"""
        if not config.is_logged_in():
            return
        
        try:
            token = config.get_access_token()
            if token:
                set_access_token(token)
            
            # Increase limit to capture all subscriptions (up to 100)
            result = api.browse_decks(category="subscribed", limit=100)
            
            if result.get('success') or 'decks' in result:
                server_decks = result.get('decks', [])
                local_decks = config.get_downloaded_decks()
                server_deck_ids = {d.get('id') for d in server_decks}
                
                # Add new subscriptions from server AND update existing metadata
                for deck in server_decks:
                    deck_id = deck.get('id')
                    if not deck_id:
                        continue
                        
                    if deck_id not in local_decks:
                        # New subscription from web - add to local config
                        config.save_downloaded_deck(
                            deck_id=deck_id,
                            version=deck.get('version', '1.0'),
                            anki_deck_id=None,  # Not installed yet
                            title=deck.get('title'),
                            card_count=deck.get('card_count'),
                            access_type=deck.get('access_type')
                        )
                        print(f"✓ Synced new subscription: {deck.get('title')} (Access: {deck.get('access_type')})")
                    else:
                        # Existing deck - update metadata (title, access_type) but PRESERVE installed version
                        current_version = local_decks[deck_id].get('version')
                        config.save_downloaded_deck(
                            deck_id=deck_id,
                            version=current_version,  # Keep current version
                            anki_deck_id=None,        # Keep current ID
                            title=deck.get('title'),
                            card_count=deck.get('card_count'),
                            access_type=deck.get('access_type') # Update access tier
                        )
                        print(f"✓ Updated deck metadata: {deck.get('title')} (Access: {deck.get('access_type')})")
                
                # Remove local entries not on server anymore
                for deck_id in list(local_decks.keys()):
                    if deck_id not in server_deck_ids:
                        config.remove_downloaded_deck(deck_id)
                        print(f"✓ Removed unsubscribed deck: {deck_id}")
        
        except Exception as e:
            print(f"⚠ Subscription sync failed (non-critical): {e}")
    
    def on_deck_selected(self, item):
        """Handle deck selection - show details in right panel"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        self.selected_deck = data
        deck_info = data.get('info', {})
        
        # Update title
        self.detail_title.setText(data.get('name', 'Unknown Deck'))
        
        # Enable buttons
        self.open_web_btn.setEnabled(True)
        self.unsubscribe_btn.setEnabled(True)
        
        # Use pre-computed install status from load_decks
        is_installed = data.get('is_installed', False)
        
        # Update install status
        has_update = config.has_update_available(data.get('deck_id', ''))
        
        if not is_installed:
            self.install_status.setText("⚠ This deck is not installed yet!")
            self.install_status.setStyleSheet("color: #ffa726;")
            self.sync_btn.setText("🔄 Sync to Install")
            self.sync_btn.setVisible(True)
        elif has_update:
            self.install_status.setText("⬆ Update available!")
            self.install_status.setStyleSheet("color: #4a90d9;")
            self.sync_btn.setText("🔄 Sync Update")
            self.sync_btn.setVisible(True)
        else:
            self.install_status.setText("✓ Installed and up to date")
            self.install_status.setStyleSheet("color: #4CAF50;")
            self.sync_btn.setVisible(False)
        
        # Show info
        version = deck_info.get('version', '1.0')
        self.version_label.setText(f"Version: {version}")
        self.cards_label.setText(f"Cards: {deck_info.get('card_count', 'Unknown')}")
        self.updated_label.setText(f"Downloaded: {deck_info.get('downloaded_at', 'Unknown')[:10] if deck_info.get('downloaded_at') else 'Not downloaded'}")
        self.info_container.setVisible(True)
    
    # === ACTIONS ===
    
    def browse_decks(self):
        """Open deck store on web"""
        webbrowser.open("https://ankiph.lovable.app/collection")
    
    def create_deck(self):
        """Create a new collaborative deck"""
        # Check if user can create decks
        if not config.can_create_decks():
            show_membership_required_dialog(self)
            return
        
        # Show confirmation dialog
        dialog = CreateDeckConfirmDialog(self)
        if dialog.exec():
            # Open deck creation form

            # For now, just show info - full creation UI would be added later
            showInfo("Deck creation feature coming soon!\n\nYou can create decks at:\n" + HOMEPAGE_URL)
    
    def sync_install_deck(self):
        """Sync/install the selected deck"""
        if not self.selected_deck:
            return
        
        deck_id = self.selected_deck.get('deck_id')
        deck_name = self.selected_deck.get('name', 'Unknown')
        
        # Double-check access (REMOVED: client-side access check disabled)
        # user_data = config.get_user()
        # deck_info = self.selected_deck.get('info', {})
        # if not check_access(user_data, deck_info):
        #     show_membership_required_dialog(self)
        #     return

        # Show sync confirmation dialog
        dialog = SyncInstallDialog(self, [deck_name])
        if dialog.exec():
            self._do_install(deck_id, deck_name, dialog.use_recommended_settings)
    

    def _do_install(self, deck_id, deck_name, use_recommended=True):
        """Perform the actual deck installation using v3.0 flow (Async)"""
        # Disable sync button to prevent double-clicks
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("Starting...")
        
        # Prepare context for background op
        token = config.get_access_token()
        
        # Define success callback
        def on_success(result):
            self._on_install_success(result, deck_id, deck_name)
            
        # Define failure callback
        def on_failure(error):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.sync_btn.setEnabled(True)
            self.sync_btn.setText("Sync")
            QMessageBox.critical(self, "Error", f"Install failed: {error}")
        
        # Run safely with QueryOp
        # QueryOp handles the threading and modal progress dialog
        from aqt.operations import QueryOp
        op = QueryOp(
            parent=self,
            op=lambda col: BackgroundInstallOp(token).run(deck_id, deck_name),
            success=on_success
        )
        op.failure(on_failure)
        
        # Show modal progress dialog
        op.with_progress(f"Installing {deck_name}...").run_in_background()

    def _on_install_success(self, result, deck_id, deck_name):
        """Handle successful install on main thread"""
        try:
            # Refresh UI
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.sync_btn.setEnabled(True)
            self.sync_btn.setText("Sync")
            
            anki_deck_id = result.get('anki_deck_id')
            version = result.get('version', '1.0')
            title = result.get('title', deck_name)
            card_count = result.get('card_count', 0)
            
            if anki_deck_id:
                # Update config
                config.save_downloaded_deck(
                    deck_id,
                    version,
                    anki_deck_id,
                    title=title,
                    card_count=card_count
                )
                
                # Update last change ID if present
                last_change_id = result.get('last_change_id')
                if last_change_id:
                    self._save_last_change_id(deck_id, last_change_id)
                
                # Reset Anki to show changes
                if mw:
                    mw.reset()
                
                tooltip(f"✓ {title} installed! ({card_count} cards)")
                self.load_decks()
            else:
                raise Exception("Install reported success but no deck ID returned")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Post-install update failed: {e}")


    
    def _save_last_change_id(self, deck_id, last_change_id):
        """Save last_change_id for incremental syncs"""
        downloaded = config.get_downloaded_decks()
        if deck_id in downloaded:
            downloaded[deck_id]['last_change_id'] = last_change_id
            config._set_profile_meta('downloaded_decks', downloaded)
    
    def open_on_web(self):
        """Open deck on web"""
        webbrowser.open(HOMEPAGE_URL)
    
    def unsubscribe_deck(self):
        """Unsubscribe from deck"""
        if not self.selected_deck:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Unsubscribe",
            f"Remove '{self.selected_deck.get('name')}' from your subscribed decks?\n\n"
            "The cards will remain in Anki but you won't receive updates.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            deck_id = self.selected_deck.get('deck_id')
            
            # Unsubscribe from server first
            try:
                self.setCursor(Qt.CursorShape.WaitCursor)
                QApplication.processEvents()
                
                token = config.get_access_token()
                if token:
                    set_access_token(token)
                    result = api.manage_subscription(action="unsubscribe", deck_id=deck_id)
                    
                    if not result.get('success'):
                        QMessageBox.warning(self, "Error", f"Failed to unsubscribe: {result.get('message', 'Unknown error')}")
                        self.setCursor(Qt.CursorShape.ArrowCursor)
                        return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unsubscribe failed: {e}")
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return
            finally:
                self.setCursor(Qt.CursorShape.ArrowCursor)

            config.remove_downloaded_deck(deck_id)
            self.selected_deck = None
            self.detail_title.setText("Select a deck")
            self.open_web_btn.setEnabled(False)
            self.unsubscribe_btn.setEnabled(False)
            self.install_status.setText("")
            self.sync_btn.setVisible(False)
            self.info_container.setVisible(False)
            self.load_decks()
            tooltip("Deck unsubscribed")
    
    def show_login(self):
        """Show login dialog and rebuild UI on success"""
        from .login_dialog import LoginDialog
        dialog = LoginDialog(self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Login successful - rebuild UI to show authenticated view
            tooltip("Login successful!")
            
            # Rebuild the entire dialog UI
            self._rebuild_ui()
    
    def open_settings(self):
        """Open settings dialog"""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def logout(self):
        """Logout user"""
        reply = QMessageBox.question(
            self, "Confirm Logout", "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            config.clear_tokens()
            set_access_token(None)
            QMessageBox.information(self, "Logged Out", "You have been logged out.")
            self.accept()



# === HELPER CLASSES ===

class BackgroundInstallOp:
    """Helper class to encapsulate background install steps"""
    
    def __init__(self, token):
        self.token = token
        
    def run(self, deck_id, deck_name):
        """Execute the installation flow in background"""
        if self.token:
            set_access_token(self.token)
            
        # 1. Get download info
        result = api.download_deck(deck_id)
        if not result.get('success'):
            raise Exception(result.get('error', 'Download info failed'))
            
        # 2. Choose flow
        if result.get('use_pull_changes'):
            return self._install_v3(deck_id, result)
        elif result.get('download_url'):
            return self._install_legacy(deck_id, deck_name, result)
        else:
            raise Exception("No supported install method available")
            
    def _install_v3(self, deck_id, download_info):
        """V3 Pull Changes Flow"""
        changes_result = api.pull_all_cards(deck_id)
        
        if not changes_result.get('success'):
            raise Exception(changes_result.get('error', 'Failed to fetch cards'))
            
        cards = changes_result.get('cards', [])
        note_types = changes_result.get('note_types', [])
        
        if not cards:
            raise Exception("No cards returned from server")
            
        if not mw.col:
            raise Exception("Anki collection not available")
            
        anki_deck_id = self._build_deck_from_json(mw.col, deck_id, download_info, cards, note_types)
        
        return {
            'anki_deck_id': anki_deck_id,
            'version': download_info.get('version', '1.0'),
            'title': download_info.get('title'),
            'card_count': len(cards),
            'last_change_id': changes_result.get('latest_change_id')
        }

    def _install_legacy(self, deck_id, deck_name, result):
        """Legacy .apkg Flow"""
        download_url = result['download_url']
        deck_content = api.download_deck_file(download_url)
        
        anki_deck_id = import_deck(deck_content, deck_name)
        
        if not anki_deck_id:
            raise Exception("Import returned no deck ID")
            
        return {
            'anki_deck_id': anki_deck_id,
            'version': result.get('version', '1.0'),
            'title': result.get('title', deck_name),
            'card_count': 0,
            'last_change_id': None
        }

    def _build_deck_from_json(self, col, deck_id, deck_info, cards, note_types):
        """Build deck (thread-safe, does NOT call mw.reset)"""
        deck_name = deck_info.get('title', 'Imported Deck')
        if cards and cards[0].get('subdeck_path'):
            deck_name = cards[0]['subdeck_path'].split('::')[0]
            
        for nt in note_types:
             self._create_or_update_note_type(col, nt)
             
        did = None
        for card_data in cards:
            self._add_card_to_deck(col, did, deck_name, card_data)
            
        actual_did = col.decks.id(deck_name)
        col.save()
        
        return actual_did
    
    def _create_or_update_note_type(self, col, note_type_data):
        """Create or update note type (Helper)"""
        model_name = note_type_data.get('name')
        if not model_name: return None
        
        existing = col.models.by_name(model_name)
        if existing: return existing
        
        model = col.models.new(model_name)
        
        fields = note_type_data.get('fields', [])
        for field_data in fields:
            field_name = field_data.get('name') if isinstance(field_data, dict) else field_data
            field = col.models.new_field(field_name)
            col.models.add_field(model, field)
        
        templates = note_type_data.get('templates', [])
        for tmpl_data in templates:
            tmpl_name = tmpl_data.get('name', 'Card 1')
            tmpl = col.models.new_template(tmpl_name)
            tmpl['qfmt'] = tmpl_data.get('qfmt', '{{Front}}')
            tmpl['afmt'] = tmpl_data.get('afmt', '{{FrontSide}}<hr id="answer">{{Back}}')
            col.models.add_template(model, tmpl)
        
        model['css'] = note_type_data.get('css', '')
        col.models.add(model)
        return model

    def _add_card_to_deck(self, col, did, deck_name, card_data):
        """Add or update a card in Anki from JSON data"""
        from anki.notes import Note
        
        guid = card_data.get('card_guid')
        if not guid: return None
        
        note_type_name = card_data.get('note_type', 'Basic')
        model = col.models.by_name(note_type_name)
        
        if not model:
            model = col.models.by_name('Basic')
            if not model: return None
        
        escaped_guid = escape_anki_search(guid)
        existing_nids = col.find_notes(f'guid:{escaped_guid}')
        
        if existing_nids:
            note = col.get_note(existing_nids[0])
            fields = card_data.get('fields', {})
            field_names = col.models.field_names(note.mid)
            
            for i, field_name in enumerate(field_names):
                if field_name in fields:
                    note.fields[i] = fields[field_name]
            
            note.tags = card_data.get('tags', [])
            col.update_note(note)
            return 'updated'
        
        note = Note(col, model)
        note.guid = guid
        
        fields = card_data.get('fields', {})
        field_names = col.models.field_names(model)
        
        for i, field_name in enumerate(field_names):
            if field_name in fields:
                note.fields[i] = fields[field_name]
        
        note.tags = card_data.get('tags', [])
        
        subdeck_path = card_data.get('subdeck_path')
        if subdeck_path:
            note_deck_id = col.decks.id(subdeck_path)
        elif did: # did might be None here...
             # Actually original code used `deck_id` param but called `deck_id` earlier.
             # The new signature has `did` as 2nd arg
             note_deck_id = did or col.decks.id(deck_name)
        else:
             note_deck_id = col.decks.id(deck_name)
        
        col.add_note(note, note_deck_id)
        return 'added'


# === HELPER DIALOGS ===




class SyncInstallDialog(QDialog):
    """Sync/Install confirmation with warnings"""
    
    def __init__(self, parent=None, deck_names=None):
        super().__init__(parent)
        self.setWindowTitle("AnkiPH | Sync")
        self.setMinimumWidth(400)
        self.deck_names = deck_names or []
        self.use_recommended_settings = True
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header
        header = QLabel("You have new AnkiPH decks to install:")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        
        # Deck list
        for name in self.deck_names:
            item = QLabel(f"• {name}")
            item.setStyleSheet("color: #4a90d9; padding-left: 10px;")
            layout.addWidget(item)
        
        # Warning
        warning = QLabel(
            "⚠ Please go to your other devices with Anki and sync before installing new deck(s).\n"
            "Any unsynchronized reviews or changes on other devices may be lost during installation."
        )
        warning.setStyleSheet("color: #ffa726; font-size: 11px; padding: 10px; background-color: #2d2d2d; border-radius: 4px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Checkbox
        self.checkbox = QCheckBox("Use recommended deck settings")
        self.checkbox.setChecked(True)
        self.checkbox.setStyleSheet("color: #888;")
        layout.addWidget(self.checkbox)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        install_btn = QPushButton("Install")
        install_btn.setStyleSheet("background-color: #4a90d9; color: white; padding: 8px 20px; border: none; border-radius: 4px;")
        install_btn.clicked.connect(self.on_install)
        btn_row.addWidget(install_btn)
        
        skip_btn = QPushButton("Skip")
        skip_btn.setStyleSheet("padding: 8px 20px;")
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(skip_btn)
        
        layout.addLayout(btn_row)
        self.setLayout(layout)
    
    def on_install(self):
        self.use_recommended_settings = self.checkbox.isChecked()
        self.accept()


class CreateDeckConfirmDialog(QDialog):
    """Confirm deck creation with terms"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm AnkiPH Deck Creation")
        self.setMinimumWidth(400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Question
        question = QLabel("Are you sure you want to create a new AnkiPH deck?")
        question.setStyleSheet("font-size: 13px;")
        layout.addWidget(question)
        
        # Links
        terms_link = QLabel(f'Terms of use: <a href="{TERMS_URL}" style="color: #4a90d9;">{TERMS_URL}</a>')
        terms_link.setOpenExternalLinks(True)
        layout.addWidget(terms_link)
        
        privacy_link = QLabel(f'Privacy Policy: <a href="{PRIVACY_URL}" style="color: #4a90d9;">{PRIVACY_URL}</a>')
        privacy_link.setOpenExternalLinks(True)
        layout.addWidget(privacy_link)
        
        # Checkbox
        self.agree_checkbox = QCheckBox("by checking this checkbox you agree to the terms of use")
        self.agree_checkbox.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.agree_checkbox)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        yes_btn = QPushButton("Yes")
        yes_btn.setStyleSheet("background-color: #4a90d9; color: white; padding: 8px 20px; border: none; border-radius: 4px;")
        yes_btn.clicked.connect(self.on_yes)
        btn_row.addWidget(yes_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px 20px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        
        layout.addLayout(btn_row)
        self.setLayout(layout)
    
    def on_yes(self):
        if not self.agree_checkbox.isChecked():
            QMessageBox.warning(self, "Terms Required", "Please agree to the terms of use to continue.")
            return
        self.accept()



class UpgradePromptDialog(QDialog):
    """Premium upgrade prompt with learning resources"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AnkiPH Membership")
        self.setFixedWidth(400)
        self.setup_ui()
        self.apply_styles()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon/Header
        header = QLabel("💎")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 48px; margin-bottom: 5px;")
        layout.addWidget(header)
        
        # Title
        title = QLabel("Unlock Full Access")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc_text = (
            "The action you are trying to perform is exclusive to AnkiPH members.\n\n"
            "Unlock unlimited collaborative decks, passive background syncing, and priority support."
        )
        desc = QLabel(desc_text)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #b0b0b0; font-size: 14px; line-height: 1.4;")
        layout.addWidget(desc)
        
        # Spacer
        layout.addSpacing(10)
        
        # Buttons container
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        # Upgrade Button (Primary)
        from aqt.utils import openLink
        
        upgrade_btn = QPushButton("Unlock Membership")
        upgrade_btn.setObjectName("upgradeBtn")
        upgrade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        upgrade_btn.setMinimumHeight(45)
        upgrade_btn.clicked.connect(lambda: [openLink(PLANS_URL), self.accept()])
        btn_layout.addWidget(upgrade_btn)
        
        # Learn More Button (Secondary)
        learn_btn = QPushButton("Learn More")
        learn_btn.setObjectName("learnBtn")
        learn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        learn_btn.setMinimumHeight(35)
        # Point to community or a learn page if available, defaulting to plans for now as it usually describes features
        learn_btn.clicked.connect(lambda: openLink(PLANS_URL)) 
        btn_layout.addWidget(learn_btn)
        
        # Cancel (Tertiary)
        cancel_btn = QPushButton("Maybe Later")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            #upgradeBtn {
                background-color: #E6C200; /* Gold/Premium Color */
                color: #000;
                font-weight: bold;
                font-size: 15px;
                border-radius: 6px;
                border: none;
            }
            #upgradeBtn:hover {
                background-color: #FFD54F;
            }
            #learnBtn {
                background-color: transparent;
                color: #4a90d9;
                font-size: 14px;
                border: 1px solid #333;
                border-radius: 6px;
                font-weight: bold;
            }
            #learnBtn:hover {
                background-color: #2a2a2a;
                border-color: #4a90d9;
            }
            #cancelBtn {
                background-color: transparent;
                color: #666;
                font-size: 13px;
                border: none;
                margin-top: 5px;
            }
            #cancelBtn:hover {
                color: #888;
                text-decoration: underline;
            }
        """)


def show_membership_required_dialog(parent=None):
    """Show beautiful upgrade prompt"""
    dialog = UpgradePromptDialog(parent)
    dialog.exec()



# For backwards compatibility - alias to new dialog
AnkiPHMainDialog = DeckManagementDialog