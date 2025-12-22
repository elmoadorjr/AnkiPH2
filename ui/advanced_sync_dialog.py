"""
Advanced Sync Dialog for AnkiPH Addon
Features: Tag sync, Suspend state sync, Media sync, Note type sync
Version: 2.1.0
"""

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, Qt,
    QGroupBox, QCheckBox, QProgressBar, QTabWidget, QWidget,
    QTextEdit
)
from aqt import mw

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config


class AdvancedSyncDialog(QDialog):
    """Dialog for advanced sync operations"""
    
    def __init__(self, deck_id: str, deck_name: str = "", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.deck_name = deck_name or f"Deck {deck_id[:8]}"
        self.sync_in_progress = False
        
        self.setWindowTitle(f"⚡ Advanced Sync - {self.deck_name}")
        self.setMinimumSize(600, 500)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup main UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title
        title = QLabel(f"⚡ Advanced Sync Options")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info
        info = QLabel(f"Deck: {self.deck_name}")
        info.setStyleSheet("color: #666; padding: 5px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        self.tags_tab = self.create_tags_tab()
        self.suspend_tab = self.create_suspend_tab()
        self.media_tab = self.create_media_tab()
        self.note_types_tab = self.create_note_types_tab()
        
        self.tabs.addTab(self.tags_tab, "🏷️ Tags")
        self.tabs.addTab(self.suspend_tab, "⏸️ Suspend")
        self.tabs.addTab(self.media_tab, "📁 Media")
        self.tabs.addTab(self.note_types_tab, "📝 Note Types")
        
        layout.addWidget(self.tabs)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("padding: 8px 20px;")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_tags_tab(self):
        """Create Tags sync tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Synchronize card tags with the server.\n"
            "Pull to get new tags, push to share your tags."
        )
        instructions.setStyleSheet("color: #666; padding: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Options
        options_group = QGroupBox("Sync Options")
        options_layout = QVBoxLayout()
        
        self.tags_pull_new = QCheckBox("Pull new tags from server")
        self.tags_pull_new.setChecked(True)
        options_layout.addWidget(self.tags_pull_new)
        
        self.tags_remove_deleted = QCheckBox("Remove locally deleted tags from server")
        options_layout.addWidget(self.tags_remove_deleted)
        
        self.tags_push_local = QCheckBox("Push local tags to server")
        options_layout.addWidget(self.tags_push_local)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Preview
        preview_group = QGroupBox("Tag Preview")
        preview_layout = QVBoxLayout()
        
        self.tags_preview = QListWidget()
        self.tags_preview.setMaximumHeight(120)
        preview_layout.addWidget(self.tags_preview)
        
        preview_btn = QPushButton("🔍 Preview Changes")
        preview_btn.clicked.connect(self.preview_tag_changes)
        preview_layout.addWidget(preview_btn)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Sync button
        sync_btn = QPushButton("🔄 Sync Tags")
        sync_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #2196F3; color: white;")
        sync_btn.clicked.connect(self.sync_tags)
        layout.addWidget(sync_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_suspend_tab(self):
        """Create Suspend state sync tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Synchronize card suspend/buried state.\n"
            "Keep your suspend preferences in sync across devices."
        )
        instructions.setStyleSheet("color: #666; padding: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Options
        options_group = QGroupBox("Sync Direction")
        options_layout = QVBoxLayout()
        
        self.suspend_pull = QCheckBox("Pull suspend state from server")
        self.suspend_pull.setChecked(True)
        options_layout.addWidget(self.suspend_pull)
        
        self.suspend_push = QCheckBox("Push local suspend state to server")
        options_layout.addWidget(self.suspend_push)
        
        self.suspend_include_buried = QCheckBox("Include buried cards")
        options_layout.addWidget(self.suspend_include_buried)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Stats
        stats_group = QGroupBox("Current Stats")
        stats_layout = QVBoxLayout()
        
        self.suspend_stats_label = QLabel("Loading...")
        stats_layout.addWidget(self.suspend_stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Load stats
        self.load_suspend_stats()
        
        # Sync button
        sync_btn = QPushButton("🔄 Sync Suspend State")
        sync_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #ff9800; color: white;")
        sync_btn.clicked.connect(self.sync_suspend_state)
        layout.addWidget(sync_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_media_tab(self):
        """Create Media sync tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Synchronize media files (images, audio, video).\n"
            "Ensure all your cards have the correct media attached."
        )
        instructions.setStyleSheet("color: #666; padding: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Options
        options_group = QGroupBox("Sync Options")
        options_layout = QVBoxLayout()
        
        self.media_download_missing = QCheckBox("Download missing media from server")
        self.media_download_missing.setChecked(True)
        options_layout.addWidget(self.media_download_missing)
        
        self.media_upload_new = QCheckBox("Upload new local media to server")
        options_layout.addWidget(self.media_upload_new)
        
        self.media_replace_existing = QCheckBox("Replace existing media with server version")
        options_layout.addWidget(self.media_replace_existing)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Status
        media_status_group = QGroupBox("Media Status")
        media_status_layout = QVBoxLayout()
        
        self.media_status_label = QLabel("Click 'Check Media' to scan")
        media_status_layout.addWidget(self.media_status_label)
        
        check_btn = QPushButton("🔍 Check Media")
        check_btn.clicked.connect(self.check_media_status)
        media_status_layout.addWidget(check_btn)
        
        media_status_group.setLayout(media_status_layout)
        layout.addWidget(media_status_group)
        
        # Sync button
        sync_btn = QPushButton("🔄 Sync Media")
        sync_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #9c27b0; color: white;")
        sync_btn.clicked.connect(self.sync_media)
        layout.addWidget(sync_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_note_types_tab(self):
        """Create Note Types sync tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Synchronize note type templates and styling.\n"
            "Keep card layouts consistent with the deck publisher."
        )
        instructions.setStyleSheet("color: #666; padding: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Warning
        warning = QLabel(
            "⚠️ Warning: Syncing note types will overwrite local template changes."
        )
        warning.setStyleSheet("color: #ff5722; padding: 5px; font-weight: bold;")
        layout.addWidget(warning)
        
        # Options
        options_group = QGroupBox("Sync Options")
        options_layout = QVBoxLayout()
        
        self.note_types_templates = QCheckBox("Sync card templates (front/back)")
        self.note_types_templates.setChecked(True)
        options_layout.addWidget(self.note_types_templates)
        
        self.note_types_styling = QCheckBox("Sync CSS styling")
        self.note_types_styling.setChecked(True)
        options_layout.addWidget(self.note_types_styling)
        
        self.note_types_fields = QCheckBox("Sync field definitions")
        options_layout.addWidget(self.note_types_fields)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Note type list
        types_group = QGroupBox("Note Types in Deck")
        types_layout = QVBoxLayout()
        
        self.note_types_list = QListWidget()
        self.note_types_list.setMaximumHeight(100)
        types_layout.addWidget(self.note_types_list)
        
        types_group.setLayout(types_layout)
        layout.addWidget(types_group)
        
        # Load note types
        self.load_note_types()
        
        # Sync button
        sync_btn = QPushButton("🔄 Sync Note Types")
        sync_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #4CAF50; color: white;")
        sync_btn.clicked.connect(self.sync_note_types)
        layout.addWidget(sync_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    # === TAG SYNC ===
    
    def preview_tag_changes(self):
        """Preview tag changes before sync"""
        self.tags_preview.clear()
        self.status_label.setText("⏳ Loading tags...")
        
        try:
            # Get local tags for this deck
            downloaded_decks = config.get_downloaded_decks()
            deck_info = downloaded_decks.get(self.deck_id, {})
            anki_deck_id = deck_info.get('anki_deck_id')
            
            if not anki_deck_id or not mw.col:
                self.status_label.setText("❌ Deck not found")
                return
            
            # Get cards in deck
            card_ids = mw.col.decks.cids(int(anki_deck_id), children=True)
            
            # Collect all tags
            local_tags = set()
            for cid in card_ids[:500]:  # Limit for performance
                try:
                    card = mw.col.get_card(cid)
                    note = card.note()
                    for tag in note.tags:
                        local_tags.add(tag)
                except:
                    continue
            
            # Display tags
            for tag in sorted(local_tags):
                item = QListWidgetItem(f"🏷️ {tag}")
                self.tags_preview.addItem(item)
            
            self.status_label.setText(f"✓ Found {len(local_tags)} tags")
            
        except Exception as e:
            self.status_label.setText("❌ Failed to load tags")
            print(f"Error loading tags: {e}")
    
    def sync_tags(self):
        """Sync tags with server"""
        if self.sync_in_progress:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.sync_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("⏳ Syncing tags...")
        
        try:
            action = "pull"  # Default to pull
            if self.tags_pull_new.isChecked() and self.tags_push_local.isChecked():
                # Both checked - need two calls or use 'pull' (server truth)
                action = "pull"
            elif self.tags_push_local.isChecked():
                action = "push"
            
            result = api.sync_tags(
                deck_id=self.deck_id,
                action=action
            )
            
            if result.get('success'):
                added = result.get('tags_added', 0)
                removed = result.get('tags_removed', 0)
                self.status_label.setText(f"✓ Tags synced: +{added}, -{removed}")
                QMessageBox.information(
                    self, "Sync Complete",
                    f"Tag sync completed!\n\nAdded: {added}\nRemoved: {removed}"
                )
            else:
                self.status_label.setText("❌ Sync failed")
                QMessageBox.warning(self, "Sync Failed", result.get('message', 'Unknown error'))
        
        except AnkiPHAPIError as e:
            self.status_label.setText(f"❌ {str(e)}")
            QMessageBox.critical(self, "API Error", str(e))
        
        except Exception as e:
            self.status_label.setText("❌ Sync failed")
            QMessageBox.critical(self, "Error", str(e))
        
        finally:
            self.sync_in_progress = False
            self.progress_bar.setVisible(False)
    
    # === SUSPEND STATE SYNC ===
    
    def load_suspend_stats(self):
        """Load suspend state statistics"""
        try:
            downloaded_decks = config.get_downloaded_decks()
            deck_info = downloaded_decks.get(self.deck_id, {})
            anki_deck_id = deck_info.get('anki_deck_id')
            
            if not anki_deck_id or not mw.col:
                self.suspend_stats_label.setText("Deck not found")
                return
            
            card_ids = mw.col.decks.cids(int(anki_deck_id), children=True)
            
            suspended = 0
            buried = 0
            for cid in card_ids:
                card = mw.col.get_card(cid)
                if card.queue == -1:
                    suspended += 1
                elif card.queue == -2:
                    buried += 1
            
            self.suspend_stats_label.setText(
                f"Total cards: {len(card_ids)}\n"
                f"Suspended: {suspended}\n"
                f"Buried: {buried}"
            )
        except Exception as e:
            self.suspend_stats_label.setText(f"Error: {e}")
    
    def sync_suspend_state(self):
        """Sync suspend state with server"""
        if self.sync_in_progress:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.sync_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("⏳ Syncing suspend state...")
        
        try:
            action = "pull"  # Default to pull
            if self.suspend_pull.isChecked() and self.suspend_push.isChecked():
                action = "pull"
            elif self.suspend_push.isChecked():
                action = "push"
            
            result = api.sync_suspend_state(
                deck_id=self.deck_id,
                action=action
                # Note: include_buried would need backend support
            )
            
            if result.get('success'):
                updated = result.get('cards_updated', 0)
                self.status_label.setText(f"✓ Updated {updated} cards")
                self.load_suspend_stats()
                QMessageBox.information(self, "Sync Complete", f"Updated {updated} cards")
            else:
                self.status_label.setText("❌ Sync failed")
                QMessageBox.warning(self, "Sync Failed", result.get('message', 'Unknown error'))
        
        except AnkiPHAPIError as e:
            self.status_label.setText(f"❌ {str(e)}")
            QMessageBox.critical(self, "API Error", str(e))
        
        except Exception as e:
            self.status_label.setText("❌ Sync failed")
            QMessageBox.critical(self, "Error", str(e))
        
        finally:
            self.sync_in_progress = False
            self.progress_bar.setVisible(False)
    
    # === MEDIA SYNC ===
    
    def check_media_status(self):
        """Check media status for deck"""
        self.media_status_label.setText("⏳ Scanning media...")
        
        try:
            downloaded_decks = config.get_downloaded_decks()
            deck_info = downloaded_decks.get(self.deck_id, {})
            anki_deck_id = deck_info.get('anki_deck_id')
            
            if not anki_deck_id or not mw.col:
                self.media_status_label.setText("Deck not found")
                return
            
            # Get cards and check for media references
            card_ids = mw.col.decks.cids(int(anki_deck_id), children=True)
            
            media_refs = set()
            import re
            media_pattern = re.compile(r'\[sound:([^\]]+)\]|src=["\']([^"\']+)["\']')
            
            for cid in card_ids[:100]:  # Sample
                try:
                    card = mw.col.get_card(cid)
                    note = card.note()
                    for field in note.fields:
                        matches = media_pattern.findall(field)
                        for match in matches:
                            ref = match[0] or match[1]
                            if ref:
                                media_refs.add(ref)
                except:
                    continue
            
            self.media_status_label.setText(
                f"Cards scanned: {min(len(card_ids), 100)}\n"
                f"Media references: {len(media_refs)}"
            )
            
        except Exception as e:
            self.media_status_label.setText(f"Error: {e}")
    
    def sync_media(self):
        """Sync media with server"""
        if self.sync_in_progress:
            return
        
        token = config.get_access_token()
        if not token:
            QMessageBox.warning(self, "Not Logged In", "Please login first.")
            return
        
        set_access_token(token)
        self.sync_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("⏳ Syncing media...")
        
        try:
            # Media sync uses action parameter
            action = "list"
            if self.media_download_missing.isChecked():
                action = "download"
            elif self.media_upload_new.isChecked():
                action = "upload"
            
            result = api.sync_media(
                deck_id=self.deck_id,
                action=action
            )
            
            if result.get('success'):
                downloaded = result.get('files_downloaded', 0)
                uploaded = result.get('files_uploaded', 0)
                self.status_label.setText(f"✓ Downloaded: {downloaded}, Uploaded: {uploaded}")
                QMessageBox.information(
                    self, "Sync Complete",
                    f"Media sync completed!\n\nDownloaded: {downloaded}\nUploaded: {uploaded}"
                )
            else:
                self.status_label.setText("❌ Sync failed")
                QMessageBox.warning(self, "Sync Failed", result.get('message', 'Unknown error'))
        
        except AnkiPHAPIError as e:
            self.status_label.setText(f"❌ {str(e)}")
            QMessageBox.critical(self, "API Error", str(e))
        
        except Exception as e:
            self.status_label.setText("❌ Sync failed")
            QMessageBox.critical(self, "Error", str(e))
        
        finally:
            self.sync_in_progress = False
            self.progress_bar.setVisible(False)
    
    # === NOTE TYPE SYNC ===
    
    def load_note_types(self):
        """Load note types used in deck"""
        self.note_types_list.clear()
        
        try:
            downloaded_decks = config.get_downloaded_decks()
            deck_info = downloaded_decks.get(self.deck_id, {})
            anki_deck_id = deck_info.get('anki_deck_id')
            
            if not anki_deck_id or not mw.col:
                return
            
            card_ids = mw.col.decks.cids(int(anki_deck_id), children=True)
            
            note_types = set()
            for cid in card_ids[:100]:  # Sample
                try:
                    card = mw.col.get_card(cid)
                    note = card.note()
                    model = note.note_type()
                    note_types.add(model['name'])
                except:
                    continue
            
            for nt in sorted(note_types):
                item = QListWidgetItem(f"📝 {nt}")
                self.note_types_list.addItem(item)
                
        except Exception as e:
            print(f"Error loading note types: {e}")
    
    def sync_note_types(self):
        """Sync note types with server"""
        if self.sync_in_progress:
            return
        
        # Confirm destructive action
        reply = QMessageBox.warning(
            self, "Confirm Sync",
            "This will overwrite local note type changes.\n\n"
            "Are you sure you want to continue?",
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
        self.sync_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("⏳ Syncing note types...")
        
        try:
            # Note type sync uses action parameter
            result = api.sync_note_types(
                deck_id=self.deck_id,
                action="get"  # Pull note types from server
            )
            
            if result.get('success'):
                updated = result.get('types_updated', 0)
                self.status_label.setText(f"✓ Updated {updated} note types")
                self.load_note_types()
                QMessageBox.information(self, "Sync Complete", f"Updated {updated} note types")
            else:
                self.status_label.setText("❌ Sync failed")
                QMessageBox.warning(self, "Sync Failed", result.get('message', 'Unknown error'))
        
        except AnkiPHAPIError as e:
            self.status_label.setText(f"❌ {str(e)}")
            QMessageBox.critical(self, "API Error", str(e))
        
        except Exception as e:
            self.status_label.setText("❌ Sync failed")
            QMessageBox.critical(self, "Error", str(e))
        
        finally:
            self.sync_in_progress = False
            self.progress_bar.setVisible(False)


def show_advanced_sync_dialog(deck_id: str, deck_name: str = "", parent=None):
    """Show the advanced sync dialog"""
    dialog = AdvancedSyncDialog(deck_id, deck_name, parent or mw)
    dialog.exec()
