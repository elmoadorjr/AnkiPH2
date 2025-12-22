"""
Login Dialog for AnkiPH Addon
Modern Premium Login UI - Fixed Version
Version: 5.3.1 - Removed missing dependencies, kept good design
"""

import webbrowser
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, Qt, QFrame
)
from aqt import mw

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config
from ..constants import REGISTER_URL, FORGOT_PASSWORD_URL


# Color scheme (inline instead of importing from missing styles.py)
COLORS = {
    'bg_primary': '#1e1e1e',
    'bg_secondary': '#252525',
    'bg_tertiary': '#2d2d2d',
    'bg_hover': '#3a3a3a',
    'border': '#404040',
    'text_primary': '#e0e0e0',
    'text_secondary': '#b0b0b0',
    'text_muted': '#808080',
    'text_link': '#4a90d9',
    'btn_primary': '#4a90d9',
    'btn_primary_hover': '#5a9fe9',
}


class ClickableLabel(QLabel):
    """Clickable label (inline instead of importing from missing components.py)"""
    from aqt.qt import pyqtSignal
    clicked = pyqtSignal()
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Enable hover events
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Mouse enters the label - apply hover style"""
        self.setStyleSheet(f"""
            color: #8cc4ff;
            font-size: 12px;
            font-weight: bold;
            text-decoration: underline;
        """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Mouse leaves the label - restore normal style"""
        self.setStyleSheet(f"""
            color: {COLORS['text_link']};
            font-size: 12px;
            font-weight: bold;
        """)
        super().leaveEvent(event)


class LoginDialog(QDialog):
    """Modern Premium Login Dialog for AnkiPH"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in to AnkiPH")
        self.setFixedSize(380, 420)
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup the modern login UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        main_layout.setSpacing(0)
        
        # Branding Header
        brand_container = QVBoxLayout()
        brand_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_container.setSpacing(4)
        
        # App title
        title_label = QLabel("AnkiPH")
        title_label.setObjectName("brandTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_container.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Sign in to your account")
        subtitle_label.setObjectName("brandSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_container.addWidget(subtitle_label)
        
        main_layout.addLayout(brand_container)
        main_layout.addSpacing(28)
        
        # Email/Username Input
        email_container = QVBoxLayout()
        email_container.setSpacing(6)
        
        email_label = QLabel("Username or Email")
        email_label.setObjectName("inputLabel")
        email_container.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setObjectName("styledInput")
        self.email_input.setPlaceholderText("Enter your username or email")
        self.email_input.setMinimumHeight(40)
        email_container.addWidget(self.email_input)
        
        main_layout.addLayout(email_container)
        main_layout.addSpacing(16)
        
        # Password Input
        password_container = QVBoxLayout()
        password_container.setSpacing(6)
        
        password_label = QLabel("Password")
        password_label.setObjectName("inputLabel")
        password_container.addWidget(password_label)
        
        # Password row with input and toggle
        password_row = QHBoxLayout()
        password_row.setSpacing(8)
        
        self.password_input = QLineEdit()
        self.password_input.setObjectName("styledInput")
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(40)
        self.password_input.returnPressed.connect(self.login)
        password_row.addWidget(self.password_input, 1)
        
        # Show/Hide toggle button
        self.toggle_btn = QPushButton("Show")
        self.toggle_btn.setObjectName("showBtn")
        self.toggle_btn.setFixedHeight(40)
        self.toggle_btn.setMinimumWidth(55)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_password_visibility)
        password_row.addWidget(self.toggle_btn)
        
        password_container.addLayout(password_row)
        main_layout.addLayout(password_container)
        
        main_layout.addSpacing(24)
        
        # Sign In Button
        self.signin_btn = QPushButton("Sign In")
        self.signin_btn.setObjectName("primaryBtn")
        self.signin_btn.setMinimumHeight(44)
        self.signin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.signin_btn.clicked.connect(self.login)
        main_layout.addWidget(self.signin_btn)
        
        main_layout.addSpacing(20)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        main_layout.addWidget(divider)
        
        main_layout.addSpacing(16)
        
        # Register link
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_layout.setSpacing(4)
        
        register_text = QLabel("Don't have an account?")
        register_text.setObjectName("mutedText")
        register_layout.addWidget(register_text)
        
        register_link = ClickableLabel("Register now")
        register_link.setObjectName("linkLabel")
        # Initialize with base style
        register_link.setStyleSheet(f"""
            color: {COLORS['text_link']};
            font-size: 12px;
            font-weight: bold;
        """)
        register_link.clicked.connect(lambda: webbrowser.open(REGISTER_URL))
        register_layout.addWidget(register_link)
        
        main_layout.addLayout(register_layout)
        main_layout.addSpacing(8)
        
        # Forgot password link
        forgot_layout = QHBoxLayout()
        forgot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        forgot_link = ClickableLabel("Forgot password?")
        forgot_link.setObjectName("linkLabel")
        # Initialize with base style
        forgot_link.setStyleSheet(f"""
            color: {COLORS['text_link']};
            font-size: 12px;
            font-weight: bold;
        """)
        forgot_link.clicked.connect(lambda: webbrowser.open(FORGOT_PASSWORD_URL))
        forgot_layout.addWidget(forgot_link)
        
        main_layout.addLayout(forgot_layout)
        main_layout.addStretch()
    
    def apply_styles(self):
        """Apply modern styling"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_secondary']};
            }}
            
            QLabel#brandTitle {{
                font-size: 26px;
                font-weight: bold;
                color: {COLORS['text_primary']};
            }}
            
            QLabel#brandSubtitle {{
                font-size: 13px;
                color: {COLORS['text_muted']};
            }}
            
            QLabel#inputLabel {{
                font-size: 12px;
                font-weight: bold;
                color: {COLORS['text_secondary']};
            }}
            
            QLineEdit#styledInput {{
                background-color: {COLORS['bg_primary']};
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            
            QLineEdit#styledInput:focus {{
                border-color: {COLORS['btn_primary']};
            }}
            
            QLineEdit#styledInput::placeholder {{
                color: {COLORS['text_muted']};
            }}
            
            QPushButton#showBtn {{
                background-color: {COLORS['bg_tertiary']};
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_secondary']};
                font-size: 11px;
                font-weight: bold;
                padding: 0 12px;
            }}
            
            QPushButton#showBtn:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['text_muted']};
                color: {COLORS['text_primary']};
            }}
            
            QPushButton#showBtn:checked {{
                background-color: {COLORS['btn_primary']};
                border-color: {COLORS['btn_primary']};
                color: white;
            }}
            
            QPushButton#primaryBtn {{
                background-color: {COLORS['btn_primary']};
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                color: white;
            }}
            
            QPushButton#primaryBtn:hover {{
                background-color: {COLORS['btn_primary_hover']};
            }}
            
            QPushButton#primaryBtn:pressed {{
                background-color: #3a80c9;
            }}
            
            QPushButton#primaryBtn:disabled {{
                background-color: {COLORS['bg_tertiary']};
                color: {COLORS['text_muted']};
            }}
            
            QFrame#divider {{
                background-color: {COLORS['border']};
                max-height: 1px;
                border: none;
            }}
            
            QLabel#mutedText {{
                font-size: 12px;
                color: {COLORS['text_muted']};
            }}
            
            QLabel#linkLabel {{
                font-size: 12px;
                color: {COLORS['text_link']};
                font-weight: bold;
            }}
            
            QLabel#linkLabel:hover {{
                color: #8cc4ff;
            }}
        """)
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.toggle_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Show")
    
    def login(self):
        """Perform login"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            from aqt.qt import QMessageBox
            QMessageBox.warning(self, "Missing Information", "Please enter both email and password.")
            return
        
        try:
            # Disable inputs during login
            self.email_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.signin_btn.setEnabled(False)
            self.signin_btn.setText("Signing in...")
            
            # Force UI update
            from aqt.qt import QApplication
            QApplication.processEvents()
            
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
                    
                    # Just accept - let main dialog show success message
                    self.accept()
                else:
                    raise Exception("No access token received from server")
            else:
                from aqt.qt import QMessageBox
                QMessageBox.warning(self, "Login Failed", result.get('message', 'Login failed. Please check your credentials.'))
        
        except AnkiPHAPIError as e:
            from aqt.qt import QMessageBox
            QMessageBox.critical(self, "Error", str(e))
        except Exception as e:
            from aqt.qt import QMessageBox
            QMessageBox.critical(self, "Error", f"Login failed: {e}")
        finally:
            self.email_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.signin_btn.setEnabled(True)
            self.signin_btn.setText("Sign In")
    
    def get_login_result(self):
        """Return whether login was successful"""
        return self.result() == QDialog.DialogCode.Accepted


def show_login_dialog(parent=None) -> bool:
    """
    Show the login dialog and return True if login was successful.
    
    Args:
        parent: Parent widget
    
    Returns:
        True if user logged in successfully, False otherwise
    """
    dialog = LoginDialog(parent or mw)
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted