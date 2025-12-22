from aqt.qt import *
from aqt import mw

class ModernProgressDialog(QDialog):
    """
    A modern, dark-themed progress dialog for AnkiPH.
    """
    def __init__(self, parent=None, title="Working...", label="Please wait..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(450)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        self.setup_ui(title, label)
        self.apply_styles()
        
    def setup_ui(self, title_text, label_text):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Loading Icon (Spinner placeholder or Emoji)
        self.icon_label = QLabel("⬇️")
        self.icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(self.icon_label)
        
        # Text Container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0;")
        text_layout.addWidget(self.title_label)
        
        self.status_label = QLabel(label_text)
        self.status_label.setStyleSheet("font-size: 13px; color: #AAAAAA;")
        text_layout.addWidget(self.status_label)
        
        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate by default
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        # Footer / Details (Optional)
        self.details_label = QLabel("")
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.details_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self.details_label)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border-radius: 10px;
                border: 1px solid #3d3d3d;
            }
            QProgressBar {
                background-color: #1e1e1e;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #4a90d9;
                border-radius: 4px;
            }
        """)

    def update_progress(self, current, total, status_text=None):
        """Update the progress bar and label."""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.details_label.setText(f"{current} / {total}")
        else:
            self.progress_bar.setRange(0, 0) # Indeterminate
            self.details_label.setText(f"{current} items")
            
        if status_text:
            self.status_label.setText(status_text)
            
    def closeEvent(self, event):
        # Prevent closing by user unless we allow it (e.g. cancel button implementation)
        # For now, ignore close attempts to prevent corrupt state
        event.ignore()

    def force_close(self):
        """Allow closing programmatically"""
        super().closeEvent(QCloseEvent())
