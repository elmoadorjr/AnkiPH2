"""
Card History Dialog for AnkiPH Addon
Features: View card change history, Rollback to previous versions
Version: 2.1.0
"""

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, Qt,
    QGroupBox, QTextEdit, QSplitter, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from aqt import mw

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config


class CardHistoryDialog(QDialog):
    """Dialog for viewing card history and rollback"""
    
    def __init__(self, deck_id: str, card_guid: str, deck_name: str = "", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.card_guid = card_guid
        self.deck_name = deck_name or f"Deck {deck_id[:8]}"
        self.history = []
        
        self.setWindowTitle(f"📜 Card History - {card_guid[:12]}...")
        self.setMinimumSize(700, 550)
        self.setup_ui()
        self.load_history()
    
    def setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel(f"📜 Card History")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Card info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>Deck:</b> {self.deck_name}"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel(f"<b>Card GUID:</b> {self.card_guid[:16]}..."))
        layout.addLayout(info_layout)
        
        # Version timeline
        timeline_group = QGroupBox("Version Timeline")
        timeline_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Version", "Date", "Changed By", "Summary"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.history_table.itemSelectionChanged.connect(self.on_version_selected)
        timeline_layout.addWidget(self.history_table)
        
        timeline_group.setLayout(timeline_layout)
        layout.addWidget(timeline_group)
        
        # Version details panel
        details_group = QGroupBox("Version Details")
        details_layout = QVBoxLayout()
        
        # Changes display
        changes_label = QLabel("Changes in this version:")
        changes_label.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(changes_label)
        
        self.changes_list = QListWidget()
        self.changes_list.setMaximumHeight(120)
        self.changes_list.setStyleSheet("QListWidget::item { padding: 5px; }")
        details_layout.addWidget(self.changes_list)
        
        # Content preview
        preview_layout = QHBoxLayout()
        
        # Previous version
        prev_frame = QFrame()
        prev_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        prev_layout = QVBoxLayout()
        prev_label = QLabel("📄 Previous Value")
        prev_label.setStyleSheet("font-weight: bold; color: #888;")
        prev_layout.addWidget(prev_label)
        self.prev_text = QTextEdit()
        self.prev_text.setReadOnly(True)
        self.prev_text.setMaximumHeight(80)
        prev_layout.addWidget(self.prev_text)
        prev_frame.setLayout(prev_layout)
        preview_layout.addWidget(prev_frame)
        
        # This version
        current_frame = QFrame()
        current_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        current_layout = QVBoxLayout()
        current_label = QLabel("📝 This Version")
        current_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        current_layout.addWidget(current_label)
        self.current_text = QTextEdit()
        self.current_text.setReadOnly(True)
        self.current_text.setMaximumHeight(80)
        current_layout.addWidget(self.current_text)
        current_frame.setLayout(current_layout)
        preview_layout.addWidget(current_frame)
        
        details_layout.addLayout(preview_layout)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_history)
        button_layout.addWidget(refresh_btn)
        
        rollback_btn = QPushButton("⏪ Rollback to Selected Version")
        rollback_btn.setStyleSheet("padding: 8px; font-weight: bold; background-color: #ff9800; color: white;")
        rollback_btn.clicked.connect(self.rollback_to_selected)
        button_layout.addWidget(rollback_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 8px 20px;")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_history(self):
        """Load card history from server"""
        token = config.get_access_token()
        if not token:
            self.status_label.setText("❌ Not logged in")
            return
        
        set_access_token(token)
        self.status_label.setText("⏳ Loading history...")
        
        try:
            result = api.get_card_history(
                deck_id=self.deck_id,
                card_guid=self.card_guid,
                limit=50
            )
            
            if not result.get('success'):
                self.status_label.setText("❌ Failed to load history")
                return
            
            self.history = result.get('history', [])
            
            # Populate table
            self.history_table.setRowCount(len(self.history))
            
            for i, entry in enumerate(self.history):
                version = entry.get('version', 'Unknown')
                changed_at = entry.get('changed_at', 'Unknown')
                changed_by = entry.get('changed_by', 'Unknown')
                
                # Format date
                date_str = changed_at
                if changed_at and changed_at != 'Unknown':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(changed_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                # Get summary
                changes = entry.get('changes', {})
                summary = ", ".join(changes.keys())[:50] or "No changes"
                
                self.history_table.setItem(i, 0, QTableWidgetItem(str(version)))
                self.history_table.setItem(i, 1, QTableWidgetItem(date_str))
                self.history_table.setItem(i, 2, QTableWidgetItem(changed_by))
                self.history_table.setItem(i, 3, QTableWidgetItem(summary))
            
            self.status_label.setText(f"✓ Loaded {len(self.history)} version(s)")
            
            # Select first row if available
            if self.history:
                self.history_table.selectRow(0)
            
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Session expired"
                config.clear_tokens()
            self.status_label.setText(f"❌ {error_msg}")
        
        except Exception as e:
            self.status_label.setText("❌ Error loading history")
            print(f"Error loading card history: {e}")
    
    def on_version_selected(self):
        """Handle version selection"""
        self.changes_list.clear()
        self.prev_text.clear()
        self.current_text.clear()
        
        selected_rows = self.history_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row >= len(self.history):
            return
        
        entry = self.history[row]
        changes = entry.get('changes', {})
        
        # Populate changes list
        for field_name, old_value in changes.items():
            item = QListWidgetItem(f"📝 {field_name}")
            item.setData(Qt.ItemDataRole.UserRole, {'field': field_name, 'old_value': old_value})
            self.changes_list.addItem(item)
        
        if not changes:
            item = QListWidgetItem("No field changes recorded")
            item.setForeground(Qt.GlobalColor.gray)
            self.changes_list.addItem(item)
        
        # Show first change details if available
        if changes:
            first_field = list(changes.keys())[0]
            old_value = changes.get(first_field, "")
            self.prev_text.setText(str(old_value))
            self.current_text.setText("(View in Anki)")
    
    def rollback_to_selected(self):
        """Rollback card to selected version"""
        selected_rows = self.history_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a version to rollback to.")
            return
        
        row = selected_rows[0].row()
        if row >= len(self.history):
            return
        
        entry = self.history[row]
        version = entry.get('version', 'Unknown')
        
        reply = QMessageBox.question(
            self, "Confirm Rollback",
            f"Rollback this card to version {version}?\n\n"
            "This will restore the card to its previous state.\n"
            "Your current changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.status_label.setText("⏳ Rolling back...")
        
        try:
            result = api.rollback_card(
                deck_id=self.deck_id,
                card_guid=self.card_guid,
                target_version=str(version)
            )
            
            if result.get('success'):
                self.status_label.setText(f"✓ Rolled back to version {version}")
                QMessageBox.information(
                    self, "Rollback Complete",
                    f"Card successfully rolled back to version {version}.\n\n"
                    "Sync your deck to apply the changes locally."
                )
                
                # Refresh history
                self.load_history()
            else:
                error_msg = result.get('message', 'Rollback failed')
                self.status_label.setText(f"❌ {error_msg}")
                QMessageBox.warning(self, "Rollback Failed", error_msg)
        
        except AnkiPHAPIError as e:
            self.status_label.setText(f"❌ {str(e)}")
            QMessageBox.critical(self, "API Error", str(e))
        
        except Exception as e:
            self.status_label.setText("❌ Rollback failed")
            QMessageBox.critical(self, "Error", f"Rollback failed:\n{str(e)}")


class DeckHistoryBrowser(QDialog):
    """Browser to select a card and view its history"""
    
    def __init__(self, deck_id: str, deck_name: str = "", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.deck_name = deck_name or f"Deck {deck_id[:8]}"
        
        self.setWindowTitle(f"📜 Browse Card History - {self.deck_name}")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.load_cards()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"📜 Select a Card to View History")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            f"Deck: {self.deck_name}\n\n"
            "Select a card below to view its change history and rollback options."
        )
        instructions.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(instructions)
        
        # Card list
        self.cards_list = QListWidget()
        self.cards_list.setStyleSheet("QListWidget::item { padding: 10px; }")
        self.cards_list.itemDoubleClicked.connect(self.view_card_history)
        layout.addWidget(self.cards_list)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        view_btn = QPushButton("📜 View History")
        view_btn.setStyleSheet("padding: 8px; font-weight: bold;")
        view_btn.clicked.connect(self.view_card_history)
        btn_layout.addWidget(view_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_cards(self):
        """Load cards from deck"""
        self.cards_list.clear()
        
        # Get Anki deck ID
        downloaded_decks = config.get_downloaded_decks()
        deck_info = downloaded_decks.get(self.deck_id, {})
        anki_deck_id = deck_info.get('anki_deck_id')
        
        if not anki_deck_id or not mw.col:
            self.status_label.setText("❌ Deck not found locally")
            return
        
        try:
            # Get card IDs for this deck
            card_ids = mw.col.decks.cids(int(anki_deck_id), children=True)
            
            if not card_ids:
                self.status_label.setText("No cards found in deck")
                return
            
            # Limit to first 100 cards for performance
            display_count = min(len(card_ids), 100)
            
            for cid in card_ids[:display_count]:
                try:
                    card = mw.col.get_card(cid)
                    note = card.note()
                    
                    # Get first field content for display
                    first_field = ""
                    if note.fields:
                        first_field = note.fields[0][:50]
                        # Strip HTML
                        import re
                        first_field = re.sub(r'<[^>]+>', '', first_field)
                    
                    guid = note.guid
                    
                    display_text = f"📄 {first_field}{'...' if len(note.fields[0]) > 50 else ''}"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, guid)
                    item.setToolTip(f"GUID: {guid}")
                    self.cards_list.addItem(item)
                    
                except Exception as e:
                    print(f"Error loading card {cid}: {e}")
                    continue
            
            if len(card_ids) > display_count:
                self.status_label.setText(f"Showing {display_count} of {len(card_ids)} cards")
            else:
                self.status_label.setText(f"✓ Loaded {len(card_ids)} cards")
        
        except Exception as e:
            self.status_label.setText("❌ Failed to load cards")
            print(f"Error loading cards: {e}")
    
    def view_card_history(self, item=None):
        """Open history dialog for selected card"""
        if item is None:
            item = self.cards_list.currentItem()
        
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a card.")
            return
        
        card_guid = item.data(Qt.ItemDataRole.UserRole)
        if not card_guid:
            QMessageBox.warning(self, "Error", "Could not get card GUID.")
            return
        
        dialog = CardHistoryDialog(self.deck_id, card_guid, self.deck_name, self)
        dialog.exec()


def show_card_history_browser(deck_id: str, deck_name: str = "", parent=None):
    """Show the card history browser for a deck"""
    dialog = DeckHistoryBrowser(deck_id, deck_name, parent or mw)
    dialog.exec()
