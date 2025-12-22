"""
Card Suggestion Dialog for AnkiPH Addon
Features: Submit card improvement suggestions to deck maintainers
Version: 2.1.0
"""

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, Qt,
    QGroupBox, QTextEdit, QComboBox, QLineEdit,
    QFormLayout
)
from aqt import mw

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config


class SuggestionDialog(QDialog):
    """Dialog for submitting card improvement suggestions"""
    
    def __init__(self, deck_id: str, card_guid: str, deck_name: str = "", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.card_guid = card_guid
        self.deck_name = deck_name or f"Deck {deck_id[:8]}"
        self.current_fields = {}
        
        self.setWindowTitle(f"💡 Suggest Improvement")
        self.setMinimumSize(550, 500)
        self.setup_ui()
        self.load_card_fields()
    
    def setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel(f"💡 Submit Card Suggestion")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info
        info = QLabel(
            "Suggest an improvement to this card. Your suggestion will be reviewed\n"
            "by the deck maintainer and may be included in a future update."
        )
        info.setStyleSheet("color: #666; padding: 5px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Card info
        card_group = QGroupBox("Card Information")
        card_layout = QFormLayout()
        
        self.deck_label = QLabel(self.deck_name)
        card_layout.addRow("Deck:", self.deck_label)
        
        self.guid_label = QLabel(self.card_guid[:16] + "...")
        card_layout.addRow("Card GUID:", self.guid_label)
        
        card_group.setLayout(card_layout)
        layout.addWidget(card_group)
        
        # Field selection
        field_group = QGroupBox("Field to Edit")
        field_layout = QVBoxLayout()
        
        self.field_combo = QComboBox()
        self.field_combo.currentIndexChanged.connect(self.on_field_selected)
        field_layout.addWidget(self.field_combo)
        
        # Current value (read-only)
        current_label = QLabel("Current Value:")
        current_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        field_layout.addWidget(current_label)
        
        self.current_value_text = QTextEdit()
        self.current_value_text.setReadOnly(True)
        self.current_value_text.setMaximumHeight(80)
        self.current_value_text.setStyleSheet("background-color: #f5f5f5;")
        field_layout.addWidget(self.current_value_text)
        
        field_group.setLayout(field_layout)
        layout.addWidget(field_group)
        
        # Suggestion input
        suggestion_group = QGroupBox("Your Suggestion")
        suggestion_layout = QVBoxLayout()
        
        suggested_label = QLabel("Suggested Value:")
        suggested_label.setStyleSheet("font-weight: bold;")
        suggestion_layout.addWidget(suggested_label)
        
        self.suggested_value_text = QTextEdit()
        self.suggested_value_text.setPlaceholderText("Enter your suggested improvement here...")
        self.suggested_value_text.setMaximumHeight(100)
        suggestion_layout.addWidget(self.suggested_value_text)
        
        reason_label = QLabel("Reason (Optional):")
        reason_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        suggestion_layout.addWidget(reason_label)
        
        self.reason_text = QLineEdit()
        self.reason_text.setPlaceholderText("Why is this change needed? (e.g., typo fix, outdated info)")
        suggestion_layout.addWidget(self.reason_text)
        
        suggestion_group.setLayout(suggestion_layout)
        layout.addWidget(suggestion_group)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        submit_btn = QPushButton("📤 Submit Suggestion")
        submit_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #4CAF50; color: white;")
        submit_btn.clicked.connect(self.submit_suggestion)
        button_layout.addWidget(submit_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 10px;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_card_fields(self):
        """Load card fields from Anki"""
        self.field_combo.clear()
        self.current_fields = {}
        
        # Get Anki deck ID
        downloaded_decks = config.get_downloaded_decks()
        deck_info = downloaded_decks.get(self.deck_id, {})
        anki_deck_id = deck_info.get('anki_deck_id')
        
        if not anki_deck_id or not mw.col:
            self.status_label.setText("❌ Deck not found locally")
            return
        
        try:
            # Find the card by GUID
            note_id = mw.col.db.scalar(
                "SELECT id FROM notes WHERE guid = ?", self.card_guid
            )
            
            if not note_id:
                self.status_label.setText("❌ Card not found locally")
                return
            
            note = mw.col.get_note(note_id)
            
            # Get field names and values
            model = note.note_type()
            field_names = [f['name'] for f in model['flds']]
            
            for i, field_name in enumerate(field_names):
                self.current_fields[field_name] = note.fields[i] if i < len(note.fields) else ""
                self.field_combo.addItem(field_name)
            
            self.status_label.setText(f"✓ Loaded {len(field_names)} fields")
            
            # Select first field
            if field_names:
                self.on_field_selected(0)
                
        except Exception as e:
            self.status_label.setText("❌ Failed to load card")
            print(f"Error loading card fields: {e}")
    
    def on_field_selected(self, index):
        """Handle field selection"""
        field_name = self.field_combo.currentText()
        if field_name in self.current_fields:
            current_value = self.current_fields[field_name]
            # Strip HTML for display
            import re
            clean_value = re.sub(r'<[^>]+>', '', current_value)
            self.current_value_text.setText(clean_value)
    
    def submit_suggestion(self):
        """Submit the suggestion to server"""
        field_name = self.field_combo.currentText()
        if not field_name:
            QMessageBox.warning(self, "No Field", "Please select a field to edit.")
            return
        
        suggested_value = self.suggested_value_text.toPlainText().strip()
        if not suggested_value:
            QMessageBox.warning(self, "Empty Suggestion", "Please enter a suggested value.")
            return
        
        current_value = self.current_fields.get(field_name, "")
        reason = self.reason_text.text().strip() or None
        
        # Confirm submission
        reply = QMessageBox.question(
            self, "Confirm Submission",
            f"Submit suggestion for field '{field_name}'?\n\n"
            f"This will be sent to the deck maintainer for review.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.status_label.setText("⏳ Submitting suggestion...")
        
        try:
            result = api.submit_suggestion(
                deck_id=self.deck_id,
                card_guid=self.card_guid,
                field_name=field_name,
                current_value=current_value,
                suggested_value=suggested_value,
                reason=reason
            )
            
            if result.get('success'):
                suggestion_id = result.get('suggestion_id', 'Unknown')
                self.status_label.setText("✓ Suggestion submitted!")
                
                QMessageBox.information(
                    self, "Suggestion Submitted",
                    f"Your suggestion has been submitted successfully!\n\n"
                    f"Suggestion ID: {suggestion_id}\n\n"
                    "The deck maintainer will review your suggestion."
                )
                
                self.accept()
            else:
                error_msg = result.get('message', 'Submission failed')
                self.status_label.setText(f"❌ {error_msg}")
                QMessageBox.warning(self, "Submission Failed", error_msg)
        
        except AnkiPHAPIError as e:
            error_msg = str(e)
            if e.status_code == 401:
                error_msg = "Session expired"
                config.clear_tokens()
            self.status_label.setText(f"❌ {error_msg}")
            QMessageBox.critical(self, "API Error", error_msg)
        
        except Exception as e:
            self.status_label.setText("❌ Submission failed")
            QMessageBox.critical(self, "Error", f"Failed to submit suggestion:\n{str(e)}")


class CardSuggestionBrowser(QDialog):
    """Browser to select a card and submit suggestion"""
    
    def __init__(self, deck_id: str, deck_name: str = "", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.deck_name = deck_name or f"Deck {deck_id[:8]}"
        
        self.setWindowTitle(f"💡 Suggest Card Improvement - {self.deck_name}")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.load_cards()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"💡 Select a Card to Suggest Improvement")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            f"Deck: {self.deck_name}\n\n"
            "Select a card to submit a suggestion for improvement."
        )
        instructions.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(instructions)
        
        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search cards...")
        self.search_input.textChanged.connect(self.filter_cards)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Card list
        self.cards_list = QListWidget()
        self.cards_list.setStyleSheet("QListWidget::item { padding: 10px; }")
        self.cards_list.itemDoubleClicked.connect(self.open_suggestion_dialog)
        layout.addWidget(self.cards_list)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        suggest_btn = QPushButton("💡 Suggest Improvement")
        suggest_btn.setStyleSheet("padding: 8px; font-weight: bold;")
        suggest_btn.clicked.connect(self.open_suggestion_dialog)
        btn_layout.addWidget(suggest_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_cards(self):
        """Load cards from deck"""
        self.cards_list.clear()
        self.all_items = []
        
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
                    self.all_items.append((display_text, guid, item))
                    
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
    
    def filter_cards(self):
        """Filter cards based on search"""
        query = self.search_input.text().lower()
        
        for display_text, guid, item in self.all_items:
            matches = query in display_text.lower() or query in guid.lower()
            item.setHidden(not matches)
    
    def open_suggestion_dialog(self, item=None):
        """Open suggestion dialog for selected card"""
        if item is None:
            item = self.cards_list.currentItem()
        
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a card.")
            return
        
        card_guid = item.data(Qt.ItemDataRole.UserRole)
        if not card_guid:
            QMessageBox.warning(self, "Error", "Could not get card GUID.")
            return
        
        dialog = SuggestionDialog(self.deck_id, card_guid, self.deck_name, self)
        dialog.exec()


def show_suggestion_browser(deck_id: str, deck_name: str = "", parent=None):
    """Show the card suggestion browser for a deck"""
    dialog = CardSuggestionBrowser(deck_id, deck_name, parent or mw)
    dialog.exec()
