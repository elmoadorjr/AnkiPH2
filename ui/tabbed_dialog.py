"""
Modern Tabbed Dialog for AnkiPH Addon
Features: My Decks, Browse, Updates, Notifications tabs
FIXED: Import errors resolved, proper relative imports
ENHANCED: Added tiered access support (v3.0)
Version: 3.1.0
"""

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, Qt,
    QTabWidget, QWidget, QProgressDialog
)
from aqt import mw
from aqt.utils import showInfo

# Use relative imports from parent package
from ..api_client import api, set_access_token, AnkiPHAPIError, AccessTier, can_sync_updates, show_upgrade_prompt
from ..config import config
from ..deck_importer import import_deck_with_progress
from ..update_checker import update_checker


class AnkiPHTabbedDialog(QDialog):
    """Modern tabbed dialog for AnkiPH operations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚖️ AnkiPH Deck Manager")
        self.setMinimumSize(800, 600)
        self.all_decks = []
        self.import_in_progress = False
        self.progress_dialog = None
        self.setup_ui()
    
    def closeEvent(self, event):
        """Override close event to prevent closing during import"""
        if self.import_in_progress:
            reply = QMessageBox.question(
                self,
                "Import in Progress",
                "A deck is being imported. Closing now may leave the import incomplete.\n\n"
                "Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Clean up progress dialog if it exists
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        event.accept()
    
    def setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel("⚖️ AnkiPH Deck Manager")
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Check if logged in
        if not config.is_logged_in():
            self.setup_login_ui(layout)
        else:
            self.setup_tabbed_ui(layout)
        
        self.setLayout(layout)
    
    def setup_login_ui(self, layout):
        """Setup login interface"""
        # Login message
        msg = QLabel("Please login to access your purchased decks")
        msg.setStyleSheet("color: #555; font-size: 14px; padding: 15px;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        
        # Login form
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        
        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-weight: bold;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        
        # Password
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.login)
        
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("padding: 10px; font-weight: bold; font-size: 14px;")
        login_btn.clicked.connect(self.login)
        button_layout.addWidget(login_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
    
    def setup_tabbed_ui(self, layout):
        """Setup tabbed interface"""
        # User info bar
        user_bar = QWidget()
        user_layout = QHBoxLayout()
        user_layout.setContentsMargins(5, 5, 5, 5)
        
        user_label = QLabel("Logged in")
        user_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        user_layout.addWidget(user_label)
        
        # Subscription status badge (v3.0)
        status_text = config.get_access_status_text()
        if config.has_full_access():
            status_style = (
                "color: #4CAF50; font-size: 11px; padding: 3px 10px; "
                "background: #E8F5E9; border-radius: 10px; font-weight: bold;"
            )
        else:
            status_style = (
                "color: #FF9800; font-size: 11px; padding: 3px 10px; "
                "background: #FFF3E0; border-radius: 10px; font-weight: bold;"
            )
        
        subscription_badge = QLabel(status_text)
        subscription_badge.setStyleSheet(status_style)
        user_layout.addWidget(subscription_badge)
        
        user_layout.addStretch()
        
        # Check for updates badge
        update_count = update_checker.get_update_count()
        if update_count > 0:
            update_badge = QLabel(f"🔔 {update_count} update(s)")
            update_badge.setStyleSheet(
                "background-color: #ff9800; color: white; "
                "padding: 5px 10px; border-radius: 10px; font-weight: bold;"
            )
            user_layout.addWidget(update_badge)
        
        # Check for notifications badge
        notif_count = config.get_unread_notification_count()
        if notif_count > 0:
            notif_badge = QLabel(f"📬 {notif_count} notification(s)")
            notif_badge.setStyleSheet(
                "background-color: #2196F3; color: white; "
                "padding: 5px 10px; border-radius: 10px; font-weight: bold;"
            )
            user_layout.addWidget(notif_badge)
        
        user_bar.setLayout(user_layout)
        layout.addWidget(user_bar)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 8px 20px; }")
        
        # Create tabs
        self.my_decks_tab = self.create_my_decks_tab()
        self.browse_tab = self.create_browse_tab()
        self.updates_tab = self.create_updates_tab()
        self.notifications_tab = self.create_notifications_tab()
        
        self.tabs.addTab(self.my_decks_tab, "📚 My Decks")
        self.tabs.addTab(self.browse_tab, "🔍 Browse")
        self.tabs.addTab(self.updates_tab, f"🔄 Updates ({update_count})")
        notif_tab_label = f"📬 Notifications ({notif_count})" if notif_count > 0 else "📬 Notifications"
        self.tabs.addTab(self.notifications_tab, notif_tab_label)
        
        layout.addWidget(self.tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        logout_btn = QPushButton("Logout")
        logout_btn.setToolTip("Logout and clear credentials")
        logout_btn.clicked.connect(self.logout)
        button_layout.addWidget(logout_btn)
        
        button_layout.addStretch()
        
        self.main_close_btn = QPushButton("Close")
        self.main_close_btn.setStyleSheet("padding: 8px 20px; font-weight: bold;")
        self.main_close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.main_close_btn)
        
        layout.addLayout(button_layout)
        
        # Load initial data
        self.load_my_decks()
        self.load_browse_decks()
        self.load_updates()
        self.load_notifications()
    
    def create_my_decks_tab(self):
        """Create My Decks tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Your Downloaded Decks")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        layout.addWidget(header)
        
        # Deck list
        self.my_decks_list = QListWidget()
        self.my_decks_list.setStyleSheet("QListWidget::item { padding: 10px; }")
        layout.addWidget(self.my_decks_list)
        
        # Status
        self.my_decks_status = QLabel("")
        self.my_decks_status.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.my_decks_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_my_decks)
        btn_layout.addWidget(refresh_btn)
        
        sync_btn = QPushButton("📊 Sync Progress")
        sync_btn.setToolTip("Sync your study progress to server")
        sync_btn.clicked.connect(self.sync_progress)
        btn_layout.addWidget(sync_btn)
        
        sync_changes_btn = QPushButton("🔄 Sync Changes")
        sync_changes_btn.setToolTip("Push/pull card changes with server")
        sync_changes_btn.clicked.connect(self.open_sync_dialog)
        btn_layout.addWidget(sync_changes_btn)
        
        history_btn = QPushButton("📜 Card History")
        history_btn.setToolTip("View card change history and rollback")
        history_btn.clicked.connect(self.open_history_browser)
        btn_layout.addWidget(history_btn)
        
        suggest_btn = QPushButton("💡 Suggest")
        suggest_btn.setToolTip("Suggest card improvement to maintainer")
        suggest_btn.clicked.connect(self.open_suggestion_browser)
        btn_layout.addWidget(suggest_btn)
        
        advanced_sync_btn = QPushButton("⚡ Advanced")
        advanced_sync_btn.setToolTip("Advanced sync: tags, suspend, media, note types")
        advanced_sync_btn.clicked.connect(self.open_advanced_sync_dialog)
        btn_layout.addWidget(advanced_sync_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_browse_tab(self):
        """Create Browse tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search decks by name...")
        self.search_input.textChanged.connect(self.filter_browse_decks)
        layout.addWidget(self.search_input)
        
        # Deck list
        self.browse_list = QListWidget()
        self.browse_list.setStyleSheet("QListWidget::item { padding: 10px; }")
        self.browse_list.itemDoubleClicked.connect(self.download_selected_deck)
        layout.addWidget(self.browse_list)
        
        # Status
        self.browse_status = QLabel("")
        self.browse_status.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.browse_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_browse_decks)
        btn_layout.addWidget(refresh_btn)
        
        download_btn = QPushButton("⬇️ Download Selected")
        download_btn.setStyleSheet("padding: 8px; font-weight: bold;")
        download_btn.clicked.connect(self.download_selected_deck)
        btn_layout.addWidget(download_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_updates_tab(self):
        """Create Updates tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Available Updates")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        check_btn = QPushButton("🔍 Check Now")
        check_btn.clicked.connect(self.check_updates_now)
        header_layout.addWidget(check_btn)
        
        layout.addLayout(header_layout)
        
        # Updates list
        self.updates_list = QListWidget()
        self.updates_list.setStyleSheet("QListWidget::item { padding: 12px; }")
        layout.addWidget(self.updates_list)
        
        # Status
        self.updates_status = QLabel("")
        self.updates_status.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.updates_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        update_all_btn = QPushButton("⬇️ Update All")
        update_all_btn.setStyleSheet("padding: 8px; font-weight: bold; background-color: #4CAF50; color: white;")
        update_all_btn.clicked.connect(self.update_all_decks)
        btn_layout.addWidget(update_all_btn)
        
        update_selected_btn = QPushButton("⬇️ Update Selected")
        update_selected_btn.clicked.connect(self.update_selected_deck)
        btn_layout.addWidget(update_selected_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_notifications_tab(self):
        """Create Notifications tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Your Notifications")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.check_notifications_now)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Notifications list
        self.notifications_list = QListWidget()
        self.notifications_list.setStyleSheet("""
            QListWidget::item { 
                padding: 12px; 
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.notifications_list.itemDoubleClicked.connect(self.view_notification_details)
        layout.addWidget(self.notifications_list)
        
        # Status
        self.notifications_status = QLabel("")
        self.notifications_status.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.notifications_status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        mark_read_btn = QPushButton("✓ Mark All Read")
        mark_read_btn.setStyleSheet("padding: 8px;")
        mark_read_btn.clicked.connect(self.mark_all_notifications_read)
        btn_layout.addWidget(mark_read_btn)
        
        mark_selected_btn = QPushButton("✓ Mark Selected Read")
        mark_selected_btn.clicked.connect(self.mark_selected_notification_read)
        btn_layout.addWidget(mark_selected_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        return tab
    
    # === LOGIN/LOGOUT ===
    
    def login(self):
        """Login user"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Missing Information", 
                              "Please enter both email and password.")
            return
        
        try:
            self.email_input.setEnabled(False)
            self.password_input.setEnabled(False)
            
            result = api.login(email, password)
            
            if result.get('success'):
                access_token = result.get('access_token')
                refresh_token = result.get('refresh_token')
                expires_at = result.get('expires_at')
                user_data = result.get('user', {})
            
                if access_token:
                    config.save_tokens(access_token, refresh_token, expires_at)
                    config.save_user_data(user_data)
                    set_access_token(access_token)
                    
                    # Customize message based on admin status
                    admin_note = " (Admin mode enabled)" if user_data.get('is_admin') else ""
                    QMessageBox.information(self, "Success", 
                                          f"Login successful!{admin_note}\nReopen AnkiPH to browse decks.")
                    self.accept()
                else:
                    raise Exception("No access token received")
            else:
                error_msg = result.get('message', 'Login failed')
                QMessageBox.warning(self, "Login Failed", error_msg)
        
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Invalid email or password."
            QMessageBox.critical(self, "Login Error", error_msg)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login failed:\n{str(e)}")
        
        finally:
            self.email_input.setEnabled(True)
            self.password_input.setEnabled(True)
    
    def logout(self):
        """Logout user"""
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            config.clear_tokens()
            set_access_token(None)
            QMessageBox.information(self, "Logged Out", 
                                  "You have been logged out successfully.")
            self.accept()
    
    # === MY DECKS TAB ===
    
    def load_my_decks(self):
        """Load user's downloaded decks"""
        self.my_decks_status.setText("⏳ Loading...")
        self.my_decks_list.clear()
        
        try:
            # Clean up deleted decks before displaying
            from ..sync import clean_deleted_decks
            cleaned = clean_deleted_decks()
            if cleaned > 0:
                print(f"✓ Cleaned up {cleaned} deleted deck(s)")
            
            downloaded_decks = config.get_downloaded_decks()
            
            if not downloaded_decks:
                self.my_decks_status.setText("No decks downloaded yet")
                return
            
            for deck_id, deck_info in downloaded_decks.items():
                version = deck_info.get('version', '1.0')
                anki_id = deck_info.get('anki_deck_id')
                
                # Check if update available
                has_update = config.has_update_available(deck_id)
                update_indicator = "🟡 " if has_update else "🟢 "
                
                display_text = f"{update_indicator}Deck {deck_id[:8]} (v{version})"
                if has_update:
                    display_text += " - Update available!"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, {'deck_id': deck_id, 'deck_info': deck_info})
                
                if has_update:
                    item.setForeground(Qt.GlobalColor.darkYellow)
                else:
                    item.setForeground(Qt.GlobalColor.darkGreen)
                
                self.my_decks_list.addItem(item)
            
            self.my_decks_status.setText(f"✓ {len(downloaded_decks)} deck(s) downloaded")
        
        except Exception as e:
            self.my_decks_status.setText(f"❌ Failed to load decks")
            print(f"Error loading my decks: {e}")
    
    def sync_progress(self):
        """Sync progress to server"""
        try:
            from ..sync import sync_progress
            
            self.my_decks_status.setText("⏳ Syncing progress...")
            sync_progress()
            self.my_decks_status.setText("✓ Progress synced successfully")
            QMessageBox.information(self, "Success", "Progress synced successfully!")
        
        except Exception as e:
            self.my_decks_status.setText("❌ Sync failed")
            QMessageBox.critical(self, "Sync Error", f"Failed to sync progress:\n{str(e)}")
    
    def open_sync_dialog(self):
        """Open sync dialog for selected deck"""
        current = self.my_decks_list.currentItem()
        if not current:
            QMessageBox.warning(
                self, "No Selection",
                "Please select a deck from 'My Decks' to sync."
            )
            return
        
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            QMessageBox.warning(self, "Error", "Could not get deck information.")
            return
        
        deck_id = data.get('deck_id')
        if not deck_id:
            QMessageBox.warning(self, "Error", "Could not determine deck ID.")
            return
        
        # Get deck name from Anki if possible
        deck_info = data.get('deck_info', {})
        anki_deck_id = deck_info.get('anki_deck_id')
        deck_name = f"Deck {deck_id[:8]}"
        
        if anki_deck_id and mw.col:
            try:
                deck = mw.col.decks.get(int(anki_deck_id))
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        try:
            from .sync_dialog import SyncDialog
            dialog = SyncDialog(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open sync dialog:\n{str(e)}")
            print(f"Sync dialog error: {e}")
            import traceback
            traceback.print_exc()
    
    def open_history_browser(self):
        """Open card history browser for selected deck"""
        current = self.my_decks_list.currentItem()
        if not current:
            QMessageBox.warning(
                self, "No Selection",
                "Please select a deck from 'My Decks' to view card history."
            )
            return
        
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            QMessageBox.warning(self, "Error", "Could not get deck information.")
            return
        
        deck_id = data.get('deck_id')
        if not deck_id:
            QMessageBox.warning(self, "Error", "Could not determine deck ID.")
            return
        
        # Get deck name from Anki if possible
        deck_info = data.get('deck_info', {})
        anki_deck_id = deck_info.get('anki_deck_id')
        deck_name = f"Deck {deck_id[:8]}"
        
        if anki_deck_id and mw.col:
            try:
                deck = mw.col.decks.get(int(anki_deck_id))
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        try:
            from .history_dialog import DeckHistoryBrowser
            dialog = DeckHistoryBrowser(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open history browser:\n{str(e)}")
            print(f"History browser error: {e}")
            import traceback
            traceback.print_exc()
    
    def open_suggestion_browser(self):
        """Open suggestion browser for selected deck"""
        current = self.my_decks_list.currentItem()
        if not current:
            QMessageBox.warning(
                self, "No Selection",
                "Please select a deck from 'My Decks' to suggest improvements."
            )
            return
        
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            QMessageBox.warning(self, "Error", "Could not get deck information.")
            return
        
        deck_id = data.get('deck_id')
        if not deck_id:
            QMessageBox.warning(self, "Error", "Could not determine deck ID.")
            return
        
        # Get deck name from Anki if possible
        deck_info = data.get('deck_info', {})
        anki_deck_id = deck_info.get('anki_deck_id')
        deck_name = f"Deck {deck_id[:8]}"
        
        if anki_deck_id and mw.col:
            try:
                deck = mw.col.decks.get(int(anki_deck_id))
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        try:
            from .suggestion_dialog import CardSuggestionBrowser
            dialog = CardSuggestionBrowser(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open suggestion browser:\n{str(e)}")
            print(f"Suggestion browser error: {e}")
            import traceback
            traceback.print_exc()
    
    def open_advanced_sync_dialog(self):
        """Open advanced sync dialog for selected deck"""
        current = self.my_decks_list.currentItem()
        if not current:
            QMessageBox.warning(
                self, "No Selection",
                "Please select a deck from 'My Decks' for advanced sync."
            )
            return
        
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            QMessageBox.warning(self, "Error", "Could not get deck information.")
            return
        
        deck_id = data.get('deck_id')
        if not deck_id:
            QMessageBox.warning(self, "Error", "Could not determine deck ID.")
            return
        
        # Get deck name
        deck_info = data.get('deck_info', {})
        anki_deck_id = deck_info.get('anki_deck_id')
        deck_name = f"Deck {deck_id[:8]}"
        
        if anki_deck_id and mw.col:
            try:
                deck = mw.col.decks.get(int(anki_deck_id))
                if deck:
                    deck_name = deck['name']
            except:
                pass
        
        try:
            from .advanced_sync_dialog import AdvancedSyncDialog
            dialog = AdvancedSyncDialog(deck_id, deck_name, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open advanced sync:\n{str(e)}")
            print(f"Advanced sync error: {e}")
            import traceback
            traceback.print_exc()
    
    # === BROWSE TAB ===
    
    def load_browse_decks(self):
        """Load available decks"""
        token = config.get_access_token()
        if not token:
            self.browse_status.setText("❌ Not logged in")
            return
        
        set_access_token(token)
        
        try:
            self.browse_status.setText("⏳ Loading decks...")
            self.browse_list.clear()
            self.all_decks = []
            
            result = api.browse_decks()
            
            if "decks" in result or result.get('success'):
                decks = result.get('decks', [])
                self.all_decks = decks
                
                downloaded_decks = config.get_downloaded_decks()
                
                for deck in decks:
                    deck_id = deck.get('id')
                    deck_name = deck.get('title') or deck.get('name', 'Unknown Deck')
                    deck_version = deck.get('version', '1.0')
                    
                    is_downloaded = deck_id in downloaded_decks
                    
                    display_text = f"{'✓ ' if is_downloaded else ''}{deck_name} (v{deck_version})"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, deck)
                    
                    if is_downloaded:
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    
                    self.browse_list.addItem(item)
                
                self.browse_status.setText(f"✓ Loaded {len(decks)} deck(s)")
            else:
                error_msg = result.get('message', 'Failed to load decks')
                self.browse_status.setText(f"❌ {error_msg}")
        
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Session expired. Please login again."
                config.clear_tokens()
            self.browse_status.setText(f"❌ {error_msg}")
        
        except Exception as e:
            self.browse_status.setText("❌ Load failed")
            print(f"Error loading browse decks: {e}")
    
    def filter_browse_decks(self):
        """Filter browse deck list"""
        query = self.search_input.text().lower()
        
        for i in range(self.browse_list.count()):
            item = self.browse_list.item(i)
            matches = query in item.text().lower()
            item.setHidden(not matches)
    
    def download_selected_deck(self):
        """Download selected deck from browse tab"""
        current = self.browse_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a deck to download.")
            return
        
        deck = current.data(Qt.ItemDataRole.UserRole)
        self._download_deck(deck)
    
    # === UPDATES TAB ===
    
    def load_updates(self):
        """Load available updates"""
        self.updates_list.clear()
        
        updates = config.get_available_updates()
        
        if not updates:
            self.updates_status.setText("All decks are up to date! ✓")
            item = QListWidgetItem("No updates available")
            item.setForeground(Qt.GlobalColor.gray)
            self.updates_list.addItem(item)
            return
        
        for deck_id, update_info in updates.items():
            current_ver = update_info.get('current_version')
            latest_ver = update_info.get('latest_version')
            summary = update_info.get('changelog_summary', '')
            
            display_text = f"Deck {deck_id[:8]}: {current_ver} → {latest_ver}"
            if summary:
                display_text += f"\n  {summary}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, update_info)
            item.setForeground(Qt.GlobalColor.darkYellow)
            
            self.updates_list.addItem(item)
        
        self.updates_status.setText(f"{len(updates)} update(s) available")
    
    def check_updates_now(self):
        """Manually check for updates"""
        self.updates_status.setText("⏳ Checking for updates...")
        updates = update_checker.check_for_updates(silent=False)
        
        if updates is not None:
            self.load_updates()
            # Update tab badge
            self.tabs.setTabText(2, f"🔄 Updates ({len(updates)})")
    
    def update_all_decks(self):
        """Update all decks with available updates"""
        updates = config.get_available_updates()
        
        if not updates:
            QMessageBox.information(self, "No Updates", "All decks are up to date!")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Update All",
            f"Update {len(updates)} deck(s)?\n\nThis will download the latest versions.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._perform_batch_update(list(updates.keys()))
    
    def _perform_batch_update(self, deck_ids: list):
        """Perform batch update for given deck IDs"""
        if not deck_ids:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.import_in_progress = True
        self.main_close_btn.setEnabled(False)
        
        # Track progress
        self._update_queue = deck_ids.copy()
        self._update_success_count = 0
        self._update_fail_count = 0
        self._total_updates = len(deck_ids)
        
        self.updates_status.setText(f"⏳ Updating 0/{self._total_updates}...")
        
        # Start updating first deck
        self._update_next_deck()
    
    def _update_next_deck(self):
        """Update the next deck in queue"""
        if not self._update_queue:
            # All done
            self._finish_batch_update()
            return
        
        deck_id = self._update_queue.pop(0)
        current_num = self._total_updates - len(self._update_queue)
        
        self.updates_status.setText(f"⏳ Updating {current_num}/{self._total_updates}...")
        
        try:
            # Get download URL
            result = api.download_deck(deck_id)
            
            if not result.get('success'):
                raise Exception(result.get('message', 'Failed to get download URL'))
            
            download_url = result.get('download_url')
            if not download_url:
                raise Exception("No download URL received")
            
            # Download deck file
            deck_content = api.download_deck_file(download_url)
            
            if not deck_content:
                raise Exception("Downloaded file is empty")
            
            # Get update info for version
            update_info = config.get_available_updates().get(deck_id, {})
            deck_version = update_info.get('latest_version', '1.0')
            
            # Import deck
            def on_success(anki_deck_id):
                # Update tracking with new version
                config.save_downloaded_deck(deck_id, deck_version, anki_deck_id)
                # Clear update notification
                update_checker.clear_update(deck_id)
                self._update_success_count += 1
                # Continue to next deck
                self._update_next_deck()
            
            def on_failure(error_msg):
                print(f"✗ Failed to update deck {deck_id}: {error_msg}")
                self._update_fail_count += 1
                # Continue to next deck anyway
                self._update_next_deck()
            
            import_deck_with_progress(
                deck_content, 
                f"Deck {deck_id[:8]}", 
                on_success=on_success,
                on_failure=on_failure,
                parent=self
            )
            
        except Exception as e:
            print(f"✗ Error updating deck {deck_id}: {e}")
            self._update_fail_count += 1
            # Continue to next deck
            self._update_next_deck()
    
    def _finish_batch_update(self):
        """Finish batch update and show results"""
        self.import_in_progress = False
        self.main_close_btn.setEnabled(True)
        
        # Reset main window to show changes
        mw.reset()
        
        # Show results
        if self._update_fail_count == 0:
            self.updates_status.setText(f"✓ All {self._update_success_count} deck(s) updated successfully!")
            QMessageBox.information(
                self, "Update Complete",
                f"Successfully updated {self._update_success_count} deck(s)!"
            )
        else:
            self.updates_status.setText(
                f"⚠️ Updated {self._update_success_count}, failed {self._update_fail_count}"
            )
            QMessageBox.warning(
                self, "Update Complete",
                f"Updated: {self._update_success_count}\nFailed: {self._update_fail_count}\n\n"
                "Check the console for error details."
            )
        
        # Reload all tabs
        self.load_my_decks()
        self.load_browse_decks()
        self.load_updates()
        
        # Update tab badge
        update_count = update_checker.get_update_count()
        self.tabs.setTabText(2, f"🔄 Updates ({update_count})")
    
    def update_selected_deck(self):
        """Update selected deck"""
        current = self.updates_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a deck to update.")
            return
        
        update_info = current.data(Qt.ItemDataRole.UserRole)
        if not update_info or not isinstance(update_info, dict):
            QMessageBox.warning(self, "Error", "Could not get deck information.")
            return
        
        deck_id = update_info.get('deck_id')
        if not deck_id:
            QMessageBox.warning(self, "Error", "Could not determine deck ID.")
            return
        
        current_ver = update_info.get('current_version', '?')
        latest_ver = update_info.get('latest_version', '?')
        
        reply = QMessageBox.question(
            self, "Confirm Update",
            f"Update deck from v{current_ver} to v{latest_ver}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reuse batch update infrastructure for single deck
            self._perform_batch_update([deck_id])
    
    # === NOTIFICATIONS TAB ===
    
    def load_notifications(self):
        """Load notifications from server or cache"""
        self.notifications_list.clear()
        self.notifications_status.setText("⏳ Loading notifications...")
        
        token = config.get_access_token()
        if not token:
            self.notifications_status.setText("❌ Not logged in")
            return
        
        set_access_token(token)
        
        try:
            result = api.check_notifications()
            
            if not result.get('success'):
                self.notifications_status.setText("❌ Failed to load notifications")
                return
            
            notifications = result.get('notifications', [])
            unread_count = result.get('unread_count', 0)
            
            # Update stored count
            config.set_unread_notification_count(unread_count)
            
            if not notifications:
                self.notifications_status.setText("No notifications")
                item = QListWidgetItem("📭 No notifications yet")
                item.setForeground(Qt.GlobalColor.gray)
                self.notifications_list.addItem(item)
                return
            
            for notif in notifications:
                notif_id = notif.get('id', '')
                notif_type = notif.get('type', 'info')
                title = notif.get('title', 'Notification')
                message = notif.get('message', '')
                created_at = notif.get('created_at', '')
                is_read = notif.get('read', False)
                
                # Format display
                type_icons = {
                    'deck_update': '🔄',
                    'announcement': '📢',
                    'promotion': '🎁',
                    'system': '⚙️',
                    'info': 'ℹ️'
                }
                icon = type_icons.get(notif_type, 'ℹ️')
                read_indicator = "" if is_read else "● "
                
                # Parse date if available
                date_str = ""
                if created_at:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%m/%d %H:%M")
                    except:
                        date_str = ""
                
                display_text = f"{read_indicator}{icon} {title}"
                if message:
                    display_text += f"\n   {message[:60]}{'...' if len(message) > 60 else ''}"
                if date_str:
                    display_text += f"\n   {date_str}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, notif)
                
                if not is_read:
                    item.setForeground(Qt.GlobalColor.blue)
                else:
                    item.setForeground(Qt.GlobalColor.darkGray)
                
                self.notifications_list.addItem(item)
            
            self.notifications_status.setText(f"✓ {len(notifications)} notification(s), {unread_count} unread")
            
            # Update tab badge
            tab_label = f"📬 Notifications ({unread_count})" if unread_count > 0 else "📬 Notifications"
            self.tabs.setTabText(3, tab_label)
            
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Session expired"
                config.clear_tokens()
            self.notifications_status.setText(f"❌ {error_msg}")
        
        except Exception as e:
            self.notifications_status.setText(f"❌ Failed to load")
            print(f"Error loading notifications: {e}")
    
    def check_notifications_now(self):
        """Manually refresh notifications"""
        self.load_notifications()
    
    def view_notification_details(self, item):
        """View full notification details"""
        notif = item.data(Qt.ItemDataRole.UserRole)
        if not notif or not isinstance(notif, dict):
            return
        
        title = notif.get('title', 'Notification')
        message = notif.get('message', 'No details available.')
        notif_type = notif.get('type', 'info')
        created_at = notif.get('created_at', '')
        
        # Format date
        date_str = ""
        if created_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = created_at
        
        details = f"{title}\n\n{message}"
        if date_str:
            details += f"\n\nReceived: {date_str}"
        
        QMessageBox.information(self, title, details)
    
    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        
        try:
            self.notifications_status.setText("⏳ Marking as read...")
            
            # Call API with mark_as_read=True
            result = api.check_notifications()
            
            if result.get('success'):
                config.set_unread_notification_count(0)
                self.notifications_status.setText("✓ All notifications marked as read")
                
                # Reload to update UI
                self.load_notifications()
            else:
                self.notifications_status.setText("❌ Failed to mark as read")
        
        except Exception as e:
            self.notifications_status.setText("❌ Error")
            print(f"Error marking notifications read: {e}")
    
    def mark_selected_notification_read(self):
        """Mark selected notification as read"""
        current = self.notifications_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a notification.")
            return
        
        notif = current.data(Qt.ItemDataRole.UserRole)
        if not notif or not isinstance(notif, dict):
            return
        
        # For now, just mark all as read (API may not support individual marking)
        # This could be enhanced if the API supports marking individual notifications
        QMessageBox.information(
            self, "Info",
            "Individual notification marking is not yet supported.\n\n"
            "Use 'Mark All Read' to clear all notifications."
        )
    
    # === COMMON DOWNLOAD LOGIC ===
    
    def _download_deck(self, deck):
        """Common deck download logic"""
        deck_id = deck.get('id')
        deck_name = deck.get('title') or deck.get('name', 'Unknown')
        deck_version = deck.get('version', '1.0')
        
        # Check if already downloaded
        if config.is_deck_downloaded(deck_id):
            reply = QMessageBox.question(
                self, "Already Downloaded",
                f"'{deck_name}' is already downloaded.\n\nDownload again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        
        # Set import in progress flag
        self.import_in_progress = True
        
        # Disable close button during download
        self.main_close_btn.setEnabled(False)
        
        try:
            self.browse_status.setText(f"⏳ Downloading {deck_name}...")
            
            result = api.download_deck(deck_id)
            
            if not result.get('success'):
                error_msg = result.get('message', 'Download failed')
                raise Exception(error_msg)
            
            download_url = result.get('download_url')
            if not download_url:
                raise Exception("No download URL received")
            
            self.browse_status.setText(f"⏳ Fetching deck file...")
            deck_content = api.download_deck_file(download_url)
            
            if not deck_content:
                raise Exception("Downloaded file is empty")
            
            # Show progress dialog
            self.progress_dialog = QProgressDialog(
                f"Importing '{deck_name}' into Anki...\n\nThis may take a few moments.",
                None,  # No cancel button
                0, 0,  # Indeterminate progress
                self
            )
            self.progress_dialog.setWindowTitle("Importing Deck")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.show()
            
            self.browse_status.setText(f"⏳ Importing into Anki...")
            
            def on_success(anki_deck_id):
                # Clear import in progress flag
                self.import_in_progress = False
                
                # Close progress dialog
                if self.progress_dialog:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                
                success = config.save_downloaded_deck(deck_id, deck_version, anki_deck_id)
                
                if success:
                    # Clear update notification if this was an update
                    update_checker.clear_update(deck_id)
                    
                    self.browse_status.setText(f"✓ '{deck_name}' imported successfully!")
                    QMessageBox.information(self, "Success", 
                                          f"'{deck_name}' has been imported successfully!")
                    
                    # Reload tabs
                    self.load_my_decks()
                    self.load_browse_decks()
                    self.load_updates()
                else:
                    self.browse_status.setText(f"⚠️ Import succeeded but tracking failed")
                
                # Re-enable close button
                self.main_close_btn.setEnabled(True)
            
            def on_failure(error_msg):
                # Clear import in progress flag
                self.import_in_progress = False
                
                # Close progress dialog
                if self.progress_dialog:
                    self.progress_dialog.close()
                    self.progress_dialog = None
                
                self.browse_status.setText(f"❌ Import failed")
                QMessageBox.critical(self, "Import Failed", 
                                   f"Failed to import '{deck_name}':\n\n{error_msg}")
                
                # Re-enable close button
                self.main_close_btn.setEnabled(True)
            
            # Import with progress tracking, passing self as parent
            import_deck_with_progress(deck_content, deck_name, 
                                    on_success=on_success, 
                                    on_failure=on_failure,
                                    parent=self)
        
        except AnkiPHAPIError as e:
            # Clear import in progress flag
            self.import_in_progress = False
            
            # Close progress dialog
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            error_msg = str(e)
            if e.status_code == 403:
                error_msg = f"You don't have access to '{deck_name}'.\n\nPlease purchase it first."
            elif e.status_code == 401:
                error_msg = "Session expired. Please login again."
                config.clear_tokens()
            
            self.browse_status.setText(f"❌ Download failed")
            QMessageBox.critical(self, "Download Error", error_msg)
            
            # Re-enable close button
            self.main_close_btn.setEnabled(True)
        
        except Exception as e:
            # Clear import in progress flag
            self.import_in_progress = False
            
            # Close progress dialog
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            self.browse_status.setText(f"❌ Download failed")
            QMessageBox.critical(self, "Error", f"Failed to download '{deck_name}':\n\n{str(e)}")
            
            # Re-enable close button
            self.main_close_btn.setEnabled(True)
