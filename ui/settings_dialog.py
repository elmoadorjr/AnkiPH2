"""
Settings Dialog for AnkiPH Addon
Features: General settings, Protected Fields, Sync, Admin (for admins)
Version: 2.1.0
"""

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, Qt,
    QTabWidget, QWidget, QCheckBox, QSpinBox, QGroupBox,
    QFormLayout, QComboBox, QTextEdit, QProgressBar
)
from aqt import mw
import webbrowser

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config
from ..utils import escape_anki_search
from ..constants import (
    ADDON_VERSION, HOMEPAGE_URL, DOCS_URL, HELP_URL,
    TERMS_URL, PRIVACY_URL, CHANGELOG_URL
)


def ensure_valid_token():
    """
    Ensure we have a valid access token, refreshing if needed.
    Returns True if we have a valid token, False otherwise.
    """
    token = config.get_access_token()
    if not token:
        return False
    
    # Try to refresh if we have a refresh token
    refresh_token = config.get_refresh_token()
    if refresh_token:
        try:
            result = api.refresh_token(refresh_token)
            if result.get('success'):
                new_access = result.get('access_token')
                new_refresh = result.get('refresh_token', refresh_token)
                expires_at = result.get('expires_at')
                
                if new_access:
                    config.save_tokens(new_access, new_refresh, expires_at)
                    set_access_token(new_access)
                    print("✓ Token refreshed successfully")
                    return True
        except Exception as e:
            print(f"✗ Token refresh failed: {e}")
    
    # Use existing token
    set_access_token(token)
    return True


def is_auth_error(error):
    """Check if an error is an authentication error"""
    error_str = str(error).lower()
    return any(x in error_str for x in ['expired', 'invalid', 'token', 'unauthorized', '401', 'auth'])


class SettingsDialog(QDialog):
    """Settings dialog with multiple configuration tabs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ AnkiPH Settings")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 8px 20px; }")
        
        # Create tabs
        self.general_tab = self.create_general_tab()
        self.protected_fields_tab = self.create_protected_fields_tab()
        self.advanced_tab = self.create_advanced_tab()
        
        self.tabs.addTab(self.general_tab, "🔧 General")
        self.tabs.addTab(self.protected_fields_tab, "🛡️ Protected Fields")
        self.tabs.addTab(self.advanced_tab, "⚡ Advanced")
        
        # Add About tab
        self.about_tab = self.create_about_tab()
        self.tabs.addTab(self.about_tab, "ℹ️ About")
        
        # Add Admin tab only if user is admin
        if config.is_admin():
            self.admin_tab = self.create_admin_tab()
            self.tabs.addTab(self.admin_tab, "👑 Admin")
        
        layout.addWidget(self.tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #4CAF50; color: white;")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 10px;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_general_tab(self):
        """Create General settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Update Checking
        update_group = QGroupBox("Update Checking")
        update_layout = QFormLayout()
        
        self.auto_check_updates = QCheckBox("Automatically check for deck updates")
        update_layout.addRow(self.auto_check_updates)
        
        self.update_interval = QSpinBox()
        self.update_interval.setMinimum(1)
        self.update_interval.setMaximum(168)  # 1 week max
        self.update_interval.setSuffix(" hours")
        update_layout.addRow("Check interval:", self.update_interval)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # Auto Sync
        sync_group = QGroupBox("Progress Sync")
        sync_layout = QFormLayout()
        
        self.auto_sync_enabled = QCheckBox("Automatically sync study progress")
        sync_layout.addRow(self.auto_sync_enabled)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_protected_fields_tab(self):
        """Create Protected Fields settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Protected fields are preserved during sync updates.\n"
            "Add field names that you want to keep from being overwritten."
        )
        instructions.setStyleSheet("color: #666; padding: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Deck selector
        deck_layout = QHBoxLayout()
        deck_label = QLabel("Select Deck:")
        deck_label.setStyleSheet("font-weight: bold;")
        deck_layout.addWidget(deck_label)
        
        self.deck_selector = QComboBox()
        self.deck_selector.setMinimumWidth(300)
        self.deck_selector.currentIndexChanged.connect(self.on_deck_selected)
        deck_layout.addWidget(self.deck_selector)
        
        deck_layout.addStretch()
        layout.addLayout(deck_layout)
        
        # Protected fields list
        fields_group = QGroupBox("Protected Fields for Selected Deck")
        fields_layout = QVBoxLayout()
        
        self.protected_fields_list = QListWidget()
        self.protected_fields_list.setStyleSheet("QListWidget::item { padding: 8px; }")
        fields_layout.addWidget(self.protected_fields_list)
        
        # Add/Remove buttons
        field_btn_layout = QHBoxLayout()
        
        self.new_field_input = QLineEdit()
        self.new_field_input.setPlaceholderText("Enter field name to protect...")
        field_btn_layout.addWidget(self.new_field_input)
        
        add_field_btn = QPushButton("➕ Add")
        add_field_btn.clicked.connect(self.add_protected_field)
        field_btn_layout.addWidget(add_field_btn)
        
        remove_field_btn = QPushButton("➖ Remove Selected")
        remove_field_btn.clicked.connect(self.remove_protected_field)
        field_btn_layout.addWidget(remove_field_btn)
        
        fields_layout.addLayout(field_btn_layout)
        fields_group.setLayout(fields_layout)
        layout.addWidget(fields_group)
        
        # Fetch from server button
        fetch_btn = QPushButton("🔄 Fetch Protected Fields from Server")
        fetch_btn.clicked.connect(self.fetch_protected_fields)
        layout.addWidget(fetch_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_advanced_tab(self):
        """Create Advanced tab with power user features"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Deck selector for advanced operations
        deck_layout = QHBoxLayout()
        deck_label = QLabel("Select Deck:")
        deck_label.setStyleSheet("font-weight: bold;")
        deck_layout.addWidget(deck_label)
        
        self.advanced_deck_selector = QComboBox()
        self.advanced_deck_selector.setMinimumWidth(300)
        deck_layout.addWidget(self.advanced_deck_selector)
        deck_layout.addStretch()
        layout.addLayout(deck_layout)
        
        # Load decks into selector
        self._load_advanced_decks()
        
        # Card Operations group
        card_group = QGroupBox("Card Operations")
        card_layout = QVBoxLayout()
        
        history_btn = QPushButton("📜 Card History")
        history_btn.setToolTip("View card change history and rollback")
        history_btn.clicked.connect(self._open_card_history)
        card_layout.addWidget(history_btn)
        
        suggest_btn = QPushButton("💡 Submit Suggestion")
        suggest_btn.setToolTip("Suggest improvements to card maintainer")
        suggest_btn.clicked.connect(self._open_suggestions)
        card_layout.addWidget(suggest_btn)
        
        sync_changes_btn = QPushButton("🔄 Sync Changes")
        sync_changes_btn.setToolTip("Push/pull individual card changes")
        sync_changes_btn.clicked.connect(self._open_sync_changes)
        card_layout.addWidget(sync_changes_btn)
        
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)
        
        # Advanced Sync group
        sync_group = QGroupBox("Advanced Sync")
        sync_layout = QVBoxLayout()
        
        sync_tags_btn = QPushButton("🏷️ Sync Tags")
        sync_tags_btn.clicked.connect(self._sync_tags)
        sync_layout.addWidget(sync_tags_btn)
        
        sync_suspend_btn = QPushButton("⏸️ Sync Suspend/Buried State")
        sync_suspend_btn.clicked.connect(self._sync_suspend)
        sync_layout.addWidget(sync_suspend_btn)
        
        sync_media_btn = QPushButton("🖼️ Sync Media")
        sync_media_btn.clicked.connect(self._sync_media)
        sync_layout.addWidget(sync_media_btn)
        
        sync_notetypes_btn = QPushButton("📝 Sync Note Types")
        sync_notetypes_btn.clicked.connect(self._sync_note_types)
        sync_layout.addWidget(sync_notetypes_btn)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        # Status
        self.advanced_status = QLabel("")
        self.advanced_status.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.advanced_status)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_about_tab(self):
        """Create About tab with version, help, and legal links"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Version header
        version_label = QLabel(f"⚖️ AnkiPH v{ADDON_VERSION}")
        version_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Tagline
        tagline = QLabel("Collaborative flashcard decks for Filipino law students")
        tagline.setStyleSheet("font-size: 12px; color: #666; padding-bottom: 10px;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)
        
        # Help & Resources group
        help_group = QGroupBox("Help & Resources")
        help_layout = QVBoxLayout()
        help_layout.setSpacing(8)
        
        docs_btn = QPushButton("📖 Documentation")
        docs_btn.setStyleSheet("text-align: left; padding: 10px;")
        docs_btn.clicked.connect(lambda: webbrowser.open(DOCS_URL))
        help_layout.addWidget(docs_btn)
        
        help_btn = QPushButton("🆘 Get Help")
        help_btn.setStyleSheet("text-align: left; padding: 10px;")
        help_btn.clicked.connect(lambda: webbrowser.open(HELP_URL))
        help_layout.addWidget(help_btn)
        
        changelog_btn = QPushButton("📝 Changelog")
        changelog_btn.setStyleSheet("text-align: left; padding: 10px;")
        changelog_btn.clicked.connect(lambda: webbrowser.open(CHANGELOG_URL))
        help_layout.addWidget(changelog_btn)
        
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        # Legal group
        legal_group = QGroupBox("Legal")
        legal_layout = QVBoxLayout()
        legal_layout.setSpacing(8)
        
        terms_btn = QPushButton("📜 Terms & Conditions")
        terms_btn.setStyleSheet("text-align: left; padding: 10px;")
        terms_btn.clicked.connect(lambda: webbrowser.open(TERMS_URL))
        legal_layout.addWidget(terms_btn)
        
        privacy_btn = QPushButton("🔒 Privacy Policy")
        privacy_btn.setStyleSheet("text-align: left; padding: 10px;")
        privacy_btn.clicked.connect(lambda: webbrowser.open(PRIVACY_URL))
        legal_layout.addWidget(privacy_btn)
        
        legal_group.setLayout(legal_layout)
        layout.addWidget(legal_group)
        
        # Homepage link
        homepage_btn = QPushButton("🌐 Visit AnkiPH Website")
        homepage_btn.setStyleSheet(
            "padding: 12px; font-weight: bold; "
            "background-color: #3b82f6; color: white; border-radius: 5px;"
        )
        homepage_btn.clicked.connect(lambda: webbrowser.open(HOMEPAGE_URL))
        layout.addWidget(homepage_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _load_advanced_decks(self):
        """Load decks into advanced deck selector"""
        self.advanced_deck_selector.clear()
        self.advanced_deck_selector.addItem("-- Select a deck --", None)
        
        downloaded_decks = config.get_downloaded_decks()
        
        for deck_id, deck_info in downloaded_decks.items():
            anki_deck_id = deck_info.get('anki_deck_id')
            deck_name = f"Deck {deck_id[:8]}"
            
            if anki_deck_id and mw.col:
                try:
                    deck = mw.col.decks.get(int(anki_deck_id))
                    if deck:
                        deck_name = deck['name']
                except:
                    pass
            
            version = deck_info.get('version', '?')
            self.advanced_deck_selector.addItem(f"{deck_name} (v{version})", deck_id)
    
    def _get_selected_deck(self):
        """Get selected deck ID and name for advanced operations"""
        deck_id = self.advanced_deck_selector.currentData()
        if not deck_id:
            QMessageBox.warning(self, "No Deck", "Please select a deck first.")
            return None, None
        
        deck_info = config.get_downloaded_decks().get(deck_id, {})
        anki_deck_id = deck_info.get('anki_deck_id')
        deck_name = f"Deck {deck_id[:8]}"
        
        if anki_deck_id and mw.col:
            try:
                deck = mw.col.decks.get(int(anki_deck_id))
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        return deck_id, deck_name
    
    def _open_card_history(self):
        """Open card history dialog"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        try:
            from .history_dialog import DeckHistoryBrowser
            dialog = DeckHistoryBrowser(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open history: {e}")
    
    def _open_suggestions(self):
        """Open suggestion dialog"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        try:
            from .suggestion_dialog import CardSuggestionBrowser
            dialog = CardSuggestionBrowser(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open suggestions: {e}")
    
    def _open_sync_changes(self):
        """Open sync changes dialog"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        try:
            from .sync_dialog import SyncDialog
            dialog = SyncDialog(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open sync: {e}")
    
    def _sync_tags(self):
        """Sync tags with server"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        self.advanced_status.setText("⏳ Syncing tags...")
        try:
            if ensure_valid_token():
                result = api.sync_tags(deck_id, action="pull")
                if result.get('success'):
                    self.advanced_status.setText(f"✓ Tags synced: +{result.get('tags_added', 0)} -{result.get('tags_removed', 0)}")
                else:
                    self.advanced_status.setText("❌ Tag sync failed")
            else:
                self.advanced_status.setText("❌ Not logged in")
        except Exception as e:
            self.advanced_status.setText(f"❌ Error: {e}")
    
    def _sync_suspend(self):
        """Sync suspend state with server"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        self.advanced_status.setText("⏳ Syncing suspend state...")
        try:
            if ensure_valid_token():
                result = api.sync_suspend_state(deck_id, action="pull")
                if result.get('success'):
                    self.advanced_status.setText(f"✓ Suspend state synced: {result.get('cards_updated', 0)} cards")
                else:
                    self.advanced_status.setText("❌ Suspend sync failed")
            else:
                self.advanced_status.setText("❌ Not logged in")
        except Exception as e:
            self.advanced_status.setText(f"❌ Error: {e}")
    
    def _sync_media(self):
        """Sync media with server"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        self.advanced_status.setText("⏳ Syncing media...")
        try:
            if ensure_valid_token():
                result = api.sync_media(deck_id, action="download")
                if result.get('success'):
                    self.advanced_status.setText(f"✓ Media synced: {result.get('files_downloaded', 0)} files")
                else:
                    self.advanced_status.setText("❌ Media sync failed")
            else:
                self.advanced_status.setText("❌ Not logged in")
        except Exception as e:
            self.advanced_status.setText(f"❌ Error: {e}")
    
    def _sync_note_types(self):
        """Sync note types with server"""
        deck_id, deck_name = self._get_selected_deck()
        if not deck_id:
            return
        
        self.advanced_status.setText("⏳ Syncing note types...")
        try:
            if ensure_valid_token():
                result = api.sync_note_types(deck_id, action="get")
                if result.get('success'):
                    self.advanced_status.setText(f"✓ Note types synced: {result.get('types_updated', 0)} types")
                else:
                    self.advanced_status.setText("❌ Note type sync failed")
            else:
                self.advanced_status.setText("❌ Not logged in")
        except Exception as e:
            self.advanced_status.setText(f"❌ Error: {e}")
    
    def load_settings(self):
        """Load current settings into UI"""
        # General tab
        self.auto_check_updates.setChecked(config.get_auto_check_updates())
        self.update_interval.setValue(config.get_update_check_interval_hours())
        self.auto_sync_enabled.setChecked(config.get_auto_sync_enabled())
        
        # Protected fields tab - load decks
        self.load_deck_list()
    
    def load_deck_list(self):
        """Load downloaded decks into deck selector"""
        self.deck_selector.clear()
        self.deck_selector.addItem("-- Select a deck --", None)
        
        downloaded_decks = config.get_downloaded_decks()
        
        for deck_id, deck_info in downloaded_decks.items():
            # Get deck name from Anki if possible
            anki_deck_id = deck_info.get('anki_deck_id')
            deck_name = f"Deck {deck_id[:8]}"
            
            if anki_deck_id and mw.col:
                try:
                    deck = mw.col.decks.get(int(anki_deck_id))
                    if deck:
                        deck_name = deck['name']
                except:
                    pass
            
            version = deck_info.get('version', '?')
            display_text = f"{deck_name} (v{version})"
            self.deck_selector.addItem(display_text, deck_id)
    
    def on_deck_selected(self, index):
        """Handle deck selection change"""
        self.protected_fields_list.clear()
        
        deck_id = self.deck_selector.currentData()
        if not deck_id:
            return
        
        # Load protected fields for this deck
        protected = config.get_protected_fields(deck_id)
        
        for field_name in protected:
            item = QListWidgetItem(f"🛡️ {field_name}")
            item.setData(Qt.ItemDataRole.UserRole, field_name)
            self.protected_fields_list.addItem(item)
    
    def add_protected_field(self):
        """Add a new protected field"""
        deck_id = self.deck_selector.currentData()
        if not deck_id:
            QMessageBox.warning(self, "No Deck Selected", "Please select a deck first.")
            return
        
        field_name = self.new_field_input.text().strip()
        if not field_name:
            QMessageBox.warning(self, "Empty Field", "Please enter a field name.")
            return
        
        # Get current protected fields
        protected = list(config.get_protected_fields(deck_id))
        
        if field_name in protected:
            QMessageBox.warning(self, "Already Protected", f"'{field_name}' is already protected.")
            return
        
        # Add to list
        protected.append(field_name)
        config.save_protected_fields(deck_id, protected)
        
        # Update UI
        item = QListWidgetItem(f"🛡️ {field_name}")
        item.setData(Qt.ItemDataRole.UserRole, field_name)
        self.protected_fields_list.addItem(item)
        
        self.new_field_input.clear()
        QMessageBox.information(self, "Added", f"'{field_name}' is now protected.")
    
    def remove_protected_field(self):
        """Remove selected protected field"""
        current = self.protected_fields_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a field to remove.")
            return
        
        deck_id = self.deck_selector.currentData()
        if not deck_id:
            return
        
        field_name = current.data(Qt.ItemDataRole.UserRole)
        
        # Remove from config
        protected = list(config.get_protected_fields(deck_id))
        if field_name in protected:
            protected.remove(field_name)
            config.save_protected_fields(deck_id, protected)
        
        # Update UI
        row = self.protected_fields_list.row(current)
        self.protected_fields_list.takeItem(row)
        
        QMessageBox.information(self, "Removed", f"'{field_name}' is no longer protected.")
    
    def fetch_protected_fields(self):
        """Fetch protected fields from server"""
        deck_id = self.deck_selector.currentData()
        if not deck_id:
            QMessageBox.warning(self, "No Deck Selected", "Please select a deck first.")
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        
        try:
            result = api.get_protected_fields(deck_id)
            
            if result.get('success'):
                server_fields = result.get('protected_fields', [])
                
                if server_fields:
                    # Update local config
                    config.save_protected_fields(deck_id, server_fields)
                    
                    # Reload UI
                    self.on_deck_selected(self.deck_selector.currentIndex())
                    
                    QMessageBox.information(
                        self, "Success",
                        f"Loaded {len(server_fields)} protected field(s) from server."
                    )
                else:
                    QMessageBox.information(
                        self, "No Fields",
                        "No protected fields configured on server for this deck."
                    )
            else:
                QMessageBox.warning(self, "Error", "Failed to fetch from server.")
        
        except AnkiPHAPIError as e:
            QMessageBox.critical(self, "API Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch: {e}")
    
    def create_admin_tab(self):
        """Create Admin tab (only visible to admins)"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Warning banner
        warning = QLabel(
            "⚠️ Admin Mode - Changes here affect ALL users of your decks!\n"
            "Only use these features if you are a deck publisher."
        )
        warning.setStyleSheet(
            "background-color: #fff3cd; color: #856404; "
            "padding: 12px; border-radius: 5px; font-weight: bold;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Deck selector
        deck_group = QGroupBox("Select Deck to Manage")
        deck_layout = QFormLayout()
        deck_layout.setSpacing(10)
        deck_layout.setContentsMargins(10, 15, 10, 10)
        
        self.admin_deck_selector = QComboBox()
        self.admin_deck_selector.setMinimumWidth(300)
        self.admin_deck_selector.setMinimumHeight(30)
        self.admin_deck_selector.currentIndexChanged.connect(self.on_admin_deck_selected)
        deck_layout.addRow("Anki Deck:", self.admin_deck_selector)
        
        # Create new deck option
        self.admin_create_new = QCheckBox("Create NEW deck (first-time import)")
        self.admin_create_new.setStyleSheet("color: #28a745; font-weight: bold;")
        self.admin_create_new.stateChanged.connect(self.on_create_new_changed)
        deck_layout.addRow("", self.admin_create_new)
        
        # Deck title for new deck
        self.admin_deck_title = QLineEdit()
        self.admin_deck_title.setPlaceholderText("Enter deck title for new deck")
        self.admin_deck_title.setEnabled(False)
        self.admin_deck_title.setMinimumHeight(28)
        deck_layout.addRow("Deck Title:", self.admin_deck_title)
        
        # Deck ID input for existing deck with unlink button
        deck_id_layout = QHBoxLayout()
        self.admin_deck_id_input = QLineEdit()
        self.admin_deck_id_input.setPlaceholderText("Auto-filled from selected deck, or enter manually")
        self.admin_deck_id_input.setMinimumHeight(28)
        deck_id_layout.addWidget(self.admin_deck_id_input)
        
        self.admin_unlink_btn = QPushButton("🔗 Unlink")
        self.admin_unlink_btn.setToolTip("Remove server link (useful if server deck was deleted)")
        self.admin_unlink_btn.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.admin_unlink_btn.setFixedWidth(80)
        self.admin_unlink_btn.clicked.connect(self.admin_unlink_deck)
        self.admin_unlink_btn.setEnabled(False)  # Disabled until a linked deck is selected
        deck_id_layout.addWidget(self.admin_unlink_btn)
        
        deck_layout.addRow("Server Deck ID:", deck_id_layout)
        
        # Load decks
        self.load_admin_decks()
        
        deck_group.setLayout(deck_layout)
        layout.addWidget(deck_group)
        
        # Push Changes Section
        push_group = QGroupBox("Push Changes to Server")
        push_layout = QVBoxLayout()
        push_layout.setSpacing(8)
        push_layout.setContentsMargins(10, 15, 10, 10)
        
        push_info = QLabel(
            "Push modified cards from your Anki to the server database. "
            "This will create a new version for all users to sync."
        )
        push_info.setWordWrap(True)
        push_layout.addWidget(push_info)
        
        # Version and notes inputs using form layout for better alignment
        push_form = QFormLayout()
        push_form.setSpacing(8)
        
        self.admin_version_input = QLineEdit()
        self.admin_version_input.setPlaceholderText("e.g., 2.2.0")
        self.admin_version_input.setMinimumHeight(28)
        push_form.addRow("New Version:", self.admin_version_input)
        
        self.admin_notes_input = QLineEdit()
        self.admin_notes_input.setPlaceholderText("e.g., Updated 50 cards with new citations")
        self.admin_notes_input.setMinimumHeight(28)
        push_form.addRow("Version Notes:", self.admin_notes_input)
        
        push_layout.addLayout(push_form)
        
        push_btn = QPushButton("🚀 Push Changes to Server")
        push_btn.setStyleSheet(
            "padding: 10px; font-weight: bold; "
            "background-color: #007bff; color: white;"
        )
        push_btn.clicked.connect(self.admin_push_changes)
        push_layout.addWidget(push_btn)
        
        push_group.setLayout(push_layout)
        layout.addWidget(push_group)
        
        # Import Deck Section
        import_group = QGroupBox("Import Full Deck to Database")
        import_layout = QVBoxLayout()
        import_layout.setSpacing(8)
        import_layout.setContentsMargins(10, 15, 10, 10)
        
        import_info = QLabel(
            "One-time import of all cards from your Anki deck to the server. "
            "Use this for initial setup or to completely refresh the database."
        )
        import_info.setWordWrap(True)
        import_layout.addWidget(import_info)
        
        self.admin_clear_existing = QCheckBox("Clear existing cards before import")
        self.admin_clear_existing.setStyleSheet("color: #dc3545;")
        import_layout.addWidget(self.admin_clear_existing)
        
        import_btn = QPushButton("📥 Import Full Deck to Database")
        import_btn.setStyleSheet(
            "padding: 10px; font-weight: bold; "
            "background-color: #28a745; color: white;"
        )
        import_btn.clicked.connect(self.admin_import_deck)
        import_layout.addWidget(import_btn)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # Status output
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        status_layout.setContentsMargins(10, 15, 10, 10)
        
        # Progress bar
        self.admin_progress = QProgressBar()
        self.admin_progress.setMinimumHeight(20)
        self.admin_progress.setTextVisible(True)
        self.admin_progress.setValue(0)
        status_layout.addWidget(self.admin_progress)
        
        # Status log
        self.admin_status = QTextEdit()
        self.admin_status.setReadOnly(True)
        self.admin_status.setMaximumHeight(80)
        self.admin_status.setPlaceholderText("Operation status will appear here...")
        status_layout.addWidget(self.admin_status)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def load_admin_decks(self):
        """Load ALL Anki decks into admin deck selector"""
        self.admin_deck_selector.clear()
        self.admin_deck_selector.addItem("-- Select a deck --", None)
        
        if not mw.col:
            return
        
        # Clean up stale backend entries first
        try:
            from ..sync import clean_deleted_backend_decks
            cleaned = clean_deleted_backend_decks()
            if cleaned > 0:
                print(f"✓ Cleaned {cleaned} server-deleted deck(s) from config")
        except Exception as e:
            print(f"⚠ Cleanup check failed: {e}")
        
        # Get all Anki decks
        all_decks = mw.col.decks.all_names_and_ids()
        
        for deck in all_decks:
            deck_name = deck.name
            anki_id = deck.id
            
            # Skip default deck
            if deck_name == "Default":
                continue
            
            # Check if this deck is already tracked (has a AnkiPH deck_id)
            downloaded = config.get_downloaded_decks()
            ankiph_id = None
            for nid, info in downloaded.items():
                if info.get('anki_deck_id') == anki_id:
                    ankiph_id = nid
                    break
            
            # Store anki_id as data since we need to look up cards by it
            display_text = f"{deck_name}"
            if ankiph_id:
                display_text += f" (ID: {ankiph_id[:8]}...)"
            
            # Store tuple of (anki_id, ankiph_id)
            self.admin_deck_selector.addItem(display_text, (anki_id, ankiph_id))
    
    def admin_log(self, message):
        """Add message to admin status log"""
        self.admin_status.append(message)
        # Scroll to bottom
        scrollbar = self.admin_status.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def admin_set_progress(self, value, maximum=100):
        """Update progress bar"""
        self.admin_progress.setMaximum(maximum)
        self.admin_progress.setValue(value)
        # Process events to update UI
        from aqt.qt import QApplication
        QApplication.processEvents()
    
    def on_admin_deck_selected(self, index):
        """Handle admin deck selection - auto-fill the server deck ID if known"""
        deck_data = self.admin_deck_selector.currentData()
        
        if not deck_data:
            # No deck selected, clear the ID field
            self.admin_deck_id_input.clear()
            self.admin_deck_id_input.setReadOnly(False)
            self.admin_deck_id_input.setPlaceholderText("Select a deck first")
            self.admin_unlink_btn.setEnabled(False)
            return
        
        anki_deck_id, existing_ankiph_id = deck_data
        
        if existing_ankiph_id:
            # This deck already has a AnkiPH ID - auto-fill and make read-only
            self.admin_deck_id_input.setText(existing_ankiph_id)
            self.admin_deck_id_input.setReadOnly(True)
            self.admin_deck_id_input.setStyleSheet("background-color: #333; color: #aaa;")
            self.admin_deck_id_input.setToolTip("This deck is already linked to a server deck. Click 'Unlink' to remove.")
            # Disable create new option since deck already exists
            self.admin_create_new.setChecked(False)
            self.admin_create_new.setEnabled(False)
            # Enable unlink button
            self.admin_unlink_btn.setEnabled(True)
        else:
            # New deck - allow entering ID or creating new
            self.admin_deck_id_input.clear()
            self.admin_deck_id_input.setReadOnly(False)
            self.admin_deck_id_input.setStyleSheet("")
            self.admin_deck_id_input.setPlaceholderText("Enter server deck UUID, or check 'Create NEW deck'")
            self.admin_deck_id_input.setToolTip("")
            self.admin_create_new.setEnabled(True)
            # Disable unlink button (nothing to unlink)
            self.admin_unlink_btn.setEnabled(False)
    
    def admin_unlink_deck(self):
        """Unlink the selected deck from its server deck ID"""
        deck_data = self.admin_deck_selector.currentData()
        if not deck_data:
            return
        
        anki_deck_id, existing_ankiph_id = deck_data
        
        if not existing_ankiph_id:
            QMessageBox.information(self, "Not Linked", "This deck is not linked to a server deck.")
            return
        
        # Get deck name for confirmation
        deck_name = "Unknown"
        if mw.col:
            try:
                deck = mw.col.decks.get(anki_deck_id)
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        reply = QMessageBox.question(
            self, "Confirm Unlink",
            f"This will remove the link between:\n\n"
            f"Anki Deck: {deck_name}\n"
            f"Server ID: {existing_ankiph_id}\n\n"
            "The deck will remain in Anki, but you'll need to re-link it "
            "or create a new server deck to push/import.\n\n"
            "This is useful if the server deck was deleted.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Remove from tracking
        success = config.remove_downloaded_deck(existing_ankiph_id)
        
        if success:
            self.admin_log(f"✓ Unlinked deck: {deck_name}")
            QMessageBox.information(
                self, "Unlinked",
                f"Successfully unlinked '{deck_name}' from server.\n\n"
                "You can now link it to a different server deck or create a new one."
            )
            # Reload the deck list to reflect the change
            self.load_admin_decks()
        else:
            self.admin_log(f"✗ Failed to unlink deck")
            QMessageBox.warning(self, "Error", "Failed to unlink deck. Please try again.")
    
    def on_create_new_changed(self, state):
        """Toggle create new deck options"""
        is_new = self.admin_create_new.isChecked()
        self.admin_deck_title.setEnabled(is_new)
        self.admin_deck_id_input.setEnabled(not is_new)
        if is_new:
            self.admin_deck_id_input.clear()
    
    def admin_push_changes(self):
        """Push changes from Anki to server"""
        deck_data = self.admin_deck_selector.currentData()
        if not deck_data:
            QMessageBox.warning(self, "No Deck Selected", "Please select a deck first.")
            return
        
        anki_deck_id, existing_ankiph_id = deck_data
        
        # Get deck_id from input or existing mapping
        deck_id = self.admin_deck_id_input.text().strip()
        if not deck_id and existing_ankiph_id:
            deck_id = existing_ankiph_id
        
        if not deck_id:
            QMessageBox.warning(
                self, "Deck ID Required", 
                "Please enter the Server Deck ID (UUID from AnkiPH database)."
            )
            return
        
        version = self.admin_version_input.text().strip()
        if not version:
            QMessageBox.warning(self, "Version Required", "Please enter a version number.")
            return
        
        version_notes = self.admin_notes_input.text().strip() or None
        
        if not mw.col:
            QMessageBox.warning(self, "No Collection", "Anki collection not available.")
            return
        
        # Confirm action
        reply = QMessageBox.question(
            self, "Confirm Push",
            f"This will push all cards from this deck to the server as version {version}.\n\n"
            f"Server Deck ID: {deck_id}\n\n"
            "All users will receive these changes on their next sync.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.admin_log(f"🔄 Collecting cards from deck...")
        
        try:
            # Get all notes from this deck (escape special chars like parentheses in deck names)
            deck_name = mw.col.decks.get(anki_deck_id)['name']
            escaped_deck_name = escape_anki_search(deck_name)
            note_ids = mw.col.find_notes(f'"deck:{escaped_deck_name}"')
            
            changes = []
            for nid in note_ids:
                note = mw.col.get_note(nid)
                fields = {}
                for field_name in note.keys():
                    fields[field_name] = note[field_name]
                
                # Get the deck path from the first card of this note
                card_ids = note.card_ids()
                deck_path = None
                if card_ids:
                    first_card = mw.col.get_card(card_ids[0])
                    deck_path = mw.col.decks.name(first_card.did)
                
                changes.append({
                    "card_guid": note.guid,
                    "note_type": note.note_type()['name'],
                    "fields": fields,
                    "tags": note.tags,
                    "change_type": "modify",
                    "deck_path": deck_path
                })
            
            self.admin_log(f"📦 Found {len(changes)} cards to push")
            
            # Validate and refresh token before starting long operation
            self.admin_log(f"🔑 Validating token...")
            if not ensure_valid_token():
                QMessageBox.warning(
                    self, "Not Logged In", 
                    "Please login first via the main AnkiPH dialog."
                )
                return
            
            # Chunk the changes for large pushes (500 per batch - backend uses batch ops)
            CHUNK_SIZE = 500
            total_cards = len(changes)
            total_pushed = 0
            total_added = 0
            total_modified = 0
            total_batches = (total_cards + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            self.admin_log(f"🚀 Pushing in {total_batches} batches of {CHUNK_SIZE}...")
            self.admin_set_progress(0, total_batches)
            
            for i in range(0, total_cards, CHUNK_SIZE):
                chunk = changes[i:i + CHUNK_SIZE]
                batch_num = (i // CHUNK_SIZE) + 1
                
                self.admin_log(f"📤 Pushing batch {batch_num}/{total_batches} ({len(chunk)} cards)...")
                self.admin_set_progress(batch_num - 1, total_batches)
                
                # Only first batch gets version_notes
                notes = version_notes if i == 0 else None
                result = api.admin_push_changes(deck_id, chunk, version, notes, timeout=120)
                
                if result.get('success'):
                    batch_added = result.get('cards_added', 0)
                    batch_modified = result.get('cards_modified', 0)
                    total_pushed += len(chunk)
                    total_added += batch_added
                    total_modified += batch_modified
                    self.admin_log(f"✓ Batch {batch_num} done ({total_pushed}/{total_cards})")
                else:
                    self.admin_log(f"⚠ Batch {batch_num} error: {result.get('error', 'Unknown')}")
                
                self.admin_set_progress(batch_num, total_batches)
            
            # Final success
            self.admin_log(f"✅ Push complete! {total_pushed} cards pushed")
            self.admin_log(f"📌 Added: {total_added}, Modified: {total_modified}")
            self.admin_log(f"📌 New version: {version}")
            
            # Update local version
            config.update_deck_version(deck_id, version)
            
            QMessageBox.information(
                self, "Push Successful",
                f"Pushed {total_pushed} cards to server.\n\n"
                f"Added: {total_added}, Modified: {total_modified}\n"
                f"New version: {version}"
            )
                
        except AnkiPHAPIError as e:
            self.admin_log(f"❌ API Error: {e}")
            QMessageBox.critical(self, "API Error", str(e))
        except Exception as e:
            self.admin_log(f"❌ Error: {e}")
            QMessageBox.critical(self, "Error", f"Push failed: {e}")
    
    def admin_import_deck(self):
        """Import full deck to database"""
        deck_data = self.admin_deck_selector.currentData()
        if not deck_data:
            QMessageBox.warning(self, "No Deck Selected", "Please select a deck first.")
            return
        
        anki_deck_id, existing_ankiph_id = deck_data
        is_new_deck = self.admin_create_new.isChecked()
        
        # For new deck, require title. For existing deck, require ID.
        deck_id = None
        deck_title = None
        
        if is_new_deck:
            deck_title = self.admin_deck_title.text().strip()
            if not deck_title:
                QMessageBox.warning(
                    self, "Deck Title Required", 
                    "Please enter a title for the new deck."
                )
                return
        else:
            # Get deck_id from input or existing mapping
            deck_id = self.admin_deck_id_input.text().strip()
            if not deck_id and existing_ankiph_id:
                deck_id = existing_ankiph_id
            
            if not deck_id:
                QMessageBox.warning(
                    self, "Deck ID Required", 
                    "Please enter the existing Deck ID, or check 'Create NEW deck'."
                )
                return
        
        version = self.admin_version_input.text().strip()
        if not version:
            QMessageBox.warning(self, "Version Required", "Please enter a version number.")
            return
        
        version_notes = self.admin_notes_input.text().strip() or None
        clear_existing = self.admin_clear_existing.isChecked()
        
        if not mw.col:
            QMessageBox.warning(self, "No Collection", "Anki collection not available.")
            return
        
        # Confirm action
        if is_new_deck:
            warning_text = (
                f"This will CREATE a new deck '{deck_title}' and import ALL cards "
                f"as version {version}.\n\nContinue?"
            )
        else:
            warning_text = (
                f"This will import ALL cards from this deck to the server database "
                f"as version {version}.\n\n"
                f"Server Deck ID: {deck_id}\n\n"
            )
            if clear_existing:
                warning_text += "⚠️ WARNING: Existing cards will be DELETED first!\n\n"
            warning_text += "This is typically used for initial setup. Continue?"
        
        reply = QMessageBox.question(
            self, "Confirm Import",
            warning_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.admin_log(f"🔄 Collecting all cards from deck...")
        
        try:
            # Get all notes from this deck (escape special chars like parentheses in deck names)
            deck_name = mw.col.decks.get(anki_deck_id)['name']
            escaped_deck_name = escape_anki_search(deck_name)
            note_ids = mw.col.find_notes(f'"deck:{escaped_deck_name}"')
            
            cards = []
            for nid in note_ids:
                note = mw.col.get_note(nid)
                fields = {}
                for field_name in note.keys():
                    fields[field_name] = note[field_name]
                
                # Get the deck path from the first card of this note
                card_ids = note.card_ids()
                deck_path = None
                if card_ids:
                    first_card = mw.col.get_card(card_ids[0])
                    deck_path = mw.col.decks.name(first_card.did)
                
                cards.append({
                    "card_guid": note.guid,
                    "note_type": note.note_type()['name'],
                    "fields": fields,
                    "tags": note.tags,
                    "deck_path": deck_path  # e.g., "AnkiPH::Political Law::Constitutional Law I"
                })
            
            self.admin_log(f"📦 Found {len(cards)} cards to import")
            
            # Validate and refresh token before starting long operation
            self.admin_log(f"🔑 Validating token...")
            if not ensure_valid_token():
                QMessageBox.warning(
                    self, "Not Logged In", 
                    "Please login first via the main AnkiPH dialog."
                )
                return
            
            # Chunk the cards for large imports (500 per batch - backend uses batch ops)
            CHUNK_SIZE = 500
            total_cards = len(cards)
            total_imported = 0
            created_deck_id = deck_id
            total_batches = (total_cards + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            self.admin_log(f"📥 Uploading in {total_batches} batches of {CHUNK_SIZE}...")
            self.admin_set_progress(0, total_batches)
            
            failed_batch = None
            retry_count = 0
            max_retries = 3
            
            for i in range(0, total_cards, CHUNK_SIZE):
                chunk = cards[i:i + CHUNK_SIZE]
                batch_num = (i // CHUNK_SIZE) + 1
                
                self.admin_log(f"📤 Uploading batch {batch_num}/{total_batches} ({len(chunk)} cards)...")
                self.admin_set_progress(batch_num - 1, total_batches)
                
                # Retry logic for each batch
                batch_success = False
                for attempt in range(max_retries):
                    try:
                        # First batch creates the deck (if new), subsequent batches append
                        if i == 0:
                            # First batch - may create new deck
                            if is_new_deck:
                                result = api.admin_import_deck(
                                    deck_id=None, 
                                    cards=chunk, 
                                    version=version, 
                                    version_notes=version_notes, 
                                    clear_existing=False,
                                    deck_title=deck_title,
                                    timeout=180  # Increased timeout
                                )
                            else:
                                result = api.admin_import_deck(
                                    deck_id=deck_id, 
                                    cards=chunk, 
                                    version=version, 
                                    version_notes=version_notes, 
                                    clear_existing=clear_existing,
                                    timeout=180  # Increased timeout
                                )
                            
                            if result.get('success'):
                                created_deck_id = result.get('deck_id', deck_id)
                                if is_new_deck:
                                    self.admin_log(f"🆕 Created deck: {created_deck_id}")
                                    # Save tracking immediately after deck creation
                                    config.save_downloaded_deck(created_deck_id, version, anki_deck_id)
                                batch_success = True
                            else:
                                raise Exception(f"First batch failed: {result.get('error')}")
                        else:
                            # Subsequent batches - append to existing deck
                            result = api.admin_import_deck(
                                deck_id=created_deck_id, 
                                cards=chunk, 
                                version=version, 
                                version_notes=None,  # Only set on first batch
                                clear_existing=False,  # Never clear on subsequent batches
                                timeout=180  # Increased timeout
                            )
                            
                            if result.get('success'):
                                batch_success = True
                            else:
                                raise Exception(f"Batch {batch_num} failed: {result.get('error')}")
                        
                        break  # Success, exit retry loop
                        
                    except Exception as batch_error:
                        # Check if this is an auth error - don't retry auth errors
                        if is_auth_error(batch_error):
                            self.admin_log(f"❌ Authentication error: {batch_error}")
                            self.admin_log(f"🔑 Please re-login and try again")
                            raise batch_error
                        
                        retry_count = attempt + 1
                        if retry_count < max_retries:
                            self.admin_log(f"⚠ Batch {batch_num} failed (attempt {retry_count}/{max_retries}), retrying...")
                            # Short delay before retry
                            from aqt.qt import QApplication
                            import time
                            QApplication.processEvents()
                            time.sleep(2)
                        else:
                            # All retries exhausted
                            failed_batch = batch_num
                            self.admin_log(f"❌ Batch {batch_num} failed after {max_retries} attempts: {batch_error}")
                            raise batch_error
                
                if batch_success:
                    batch_imported = result.get('cards_imported', len(chunk))
                    total_imported += batch_imported
                    self.admin_log(f"✓ Batch {batch_num} done ({total_imported}/{total_cards})")
                
                self.admin_set_progress(batch_num, total_batches)
            
            # Final success
            self.admin_log(f"✅ Import complete! {total_imported} cards imported")
            self.admin_log(f"📌 Version: {version}")
            
            # Update deck tracking with final version
            if created_deck_id:
                config.save_downloaded_deck(created_deck_id, version, anki_deck_id)
            
            QMessageBox.information(
                self, "Import Successful",
                f"Imported {total_imported} cards to database.\n\n"
                f"Deck ID: {created_deck_id}\n"
                f"Version: {version}"
            )
                
        except AnkiPHAPIError as e:
            self.admin_log(f"❌ API Error: {e}")
            # Save partial progress
            if created_deck_id and total_imported > 0:
                config.save_downloaded_deck(created_deck_id, version, anki_deck_id)
                self.admin_log(f"💾 Saved partial progress: {total_imported} cards")
                self.admin_log(f"📋 Deck ID: {created_deck_id}")
                
                reply = QMessageBox.warning(
                    self, "Partial Import",
                    f"Import failed after {total_imported} cards.\n\n"
                    f"Deck ID: {created_deck_id}\n\n"
                    "The partial import has been saved. You can:\n"
                    "1. Try importing again (remaining cards will be added)\n"
                    "2. Note down the Deck ID for manual recovery\n\n"
                    f"Error: {e}\n\n"
                    "Copy Deck ID to clipboard?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    from aqt.qt import QApplication
                    QApplication.clipboard().setText(created_deck_id)
                    self.admin_log("📋 Deck ID copied to clipboard")
            else:
                QMessageBox.critical(self, "API Error", str(e))
                
        except Exception as e:
            self.admin_log(f"❌ Error: {e}")
            # Save partial progress
            if created_deck_id and total_imported > 0:
                config.save_downloaded_deck(created_deck_id, version, anki_deck_id)
                self.admin_log(f"💾 Saved partial progress: {total_imported} cards")
                self.admin_log(f"📋 Deck ID: {created_deck_id}")
                
                QMessageBox.warning(
                    self, "Partial Import",
                    f"Import failed after {total_imported} cards.\n\n"
                    f"Deck ID: {created_deck_id}\n\n"
                    "The partial import has been saved.\n"
                    f"Error: {e}"
                )
            else:
                QMessageBox.critical(self, "Error", f"Import failed: {e}")

    
    def save_settings(self):
        """Save all settings"""
        try:
            # General settings
            config.set_auto_check_updates(self.auto_check_updates.isChecked())
            config.set_update_check_interval_hours(self.update_interval.value())
            config.set_auto_sync_enabled(self.auto_sync_enabled.isChecked())

            
            # Protected fields are saved immediately when added/removed
            
            # Show success
            QMessageBox.information(
                self, "Settings Saved",
                "Settings saved successfully!\n\n"
                "Some changes may require restarting Anki."
            )
            
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")


def show_settings_dialog(parent=None):
    """Show the settings dialog"""
    dialog = SettingsDialog(parent or mw)
    dialog.exec()
