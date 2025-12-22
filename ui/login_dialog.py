"""
Login Dialog for AnkiPH Addon
AnkiHub-style login UI with modern dark theme
Version: 3.1.0
"""

import webbrowser
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, Qt, QFont, QFrame
)
from aqt import mw

from ..api_client import api, set_access_token, AnkiPHAPIError
from ..config import config
from ..constants import REGISTER_URL, FORGOT_PASSWORD_URL


class LoginDialog(QDialog):
    """AnkiHub-style Login Dialog for AnkiPH"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in to AnkiPH")
        self.setFixedWidth(500)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.apply_dark_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme styling to match AnkiHub"""
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QLabel#title_label {
                font-size: 14px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #4a90d9;
            }
            QLineEdit::placeholder {
                color: #888888;
            }
            QPushButton#show_btn {
                background-color: #555555;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 12px;
                min-height: 20px;
            }
            QPushButton#show_btn:hover {
                background-color: #666666;
            }
            QPushButton#signin_btn {
                background-color: #555555;
                border: none;
                border-radius: 4px;
                padding: 10px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-height: 24px;
            }
            QPushButton#signin_btn:hover {
                background-color: #666666;
            }
            QPushButton#signin_btn:pressed {
                background-color: #444444;
            }
            QLabel#link_label {
                color: #6bb3f8;
                font-size: 12px;
            }
            QLabel#link_label:hover {
                color: #8cc8ff;
                text-decoration: underline;
            }
        """)
    
    def setup_ui(self):
        """Setup the login UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 25)
        layout.setSpacing(15)
        
        # Username/Email row
        email_layout = QHBoxLayout()
        email_label = QLabel("Username or E-mail:")
        email_label.setObjectName("title_label")
        email_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("")
        email_layout.addWidget(self.email_input, 1)
        layout.addLayout(email_layout)
        
        # Password row with Show button
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        password_label.setObjectName("title_label")
        password_label.setFixedWidth(email_label.sizeHint().width())
        password_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.login)
        password_layout.addWidget(self.password_input, 1)
        
        self.show_password_btn = QPushButton("Show")
        self.show_password_btn.setObjectName("show_btn")
        self.show_password_btn.setCheckable(True)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)
        
        layout.addLayout(password_layout)
        
        # Spacing before sign in button
        layout.addSpacing(5)
        
        # Sign in button
        self.signin_btn = QPushButton("Sign in")
        self.signin_btn.setObjectName("signin_btn")
        self.signin_btn.clicked.connect(self.login)
        layout.addWidget(self.signin_btn)
        
        # Spacing
        layout.addSpacing(10)
        
        # Register link
        register_layout = QHBoxLayout()
        register_text = QLabel("Don't have an AnkiPH account?")
        register_text.setStyleSheet("color: #cccccc; font-size: 12px;")
        register_layout.addWidget(register_text)
        
        register_link = ClickableLabel("Register now")
        register_link.setObjectName("link_label")
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.clicked.connect(lambda: webbrowser.open(REGISTER_URL))
        register_layout.addWidget(register_link)
        
        register_layout.addStretch()
        layout.addLayout(register_layout)
        
        # Forgot password link
        forgot_link = ClickableLabel("Forgot password?")
        forgot_link.setObjectName("link_label")
        forgot_link.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_link.clicked.connect(lambda: webbrowser.open(FORGOT_PASSWORD_URL))
        layout.addWidget(forgot_link)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.show_password_btn.isChecked():
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password_btn.setText("Hide")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password_btn.setText("Show")
    
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
                    
                    from aqt.qt import QMessageBox
                    QMessageBox.information(self, "Success", "Login successful!")
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
            self.signin_btn.setText("Sign in")
    
    def get_login_result(self):
        """Return whether login was successful"""
        return self.result() == QDialog.DialogCode.Accepted


class ClickableLabel(QLabel):
    """Label that can be clicked"""
    
    from aqt.qt import pyqtSignal
    clicked = pyqtSignal()
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


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
