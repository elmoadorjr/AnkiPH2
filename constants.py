"""
Central constants for AnkiPH Addon
Single source of truth for version, URLs, and configuration
Version: 3.3.0 - Subscription-only model
"""

from typing import Final

# =============================================================================
# ADDON METADATA
# =============================================================================

ADDON_NAME: Final[str] = "AnkiPH"
ADDON_VERSION: Final[str] = "3.3.0"

# =============================================================================
# URL CONFIGURATION
# =============================================================================

# Base URL - Use primary domain for all features
BASE_URL: Final[str] = "https://ankiph.lovable.app"

# Public Pages
HOMEPAGE_URL: Final[str] = BASE_URL
REGISTER_URL: Final[str] = f"{BASE_URL}/auth"
FORGOT_PASSWORD_URL: Final[str] = f"{BASE_URL}/auth"
TERMS_URL: Final[str] = f"{BASE_URL}/terms"
PRIVACY_URL: Final[str] = f"{BASE_URL}/privacy"
PLANS_URL: Final[str] = f"{BASE_URL}/subscription"
DOCS_URL: Final[str] = f"{BASE_URL}/ankiph"
HELP_URL: Final[str] = f"{BASE_URL}/help"
CHANGELOG_URL: Final[str] = f"{BASE_URL}/help"
COMMUNITY_URL: Final[str] = f"{BASE_URL}/help"

# Subscription URLs (v3.3 - subscription-only model)
COLLECTION_URL: Final[str] = f"{BASE_URL}/collection"
PREMIUM_URL: Final[str] = f"{BASE_URL}/subscription"
SUBSCRIBE_URL: Final[str] = PREMIUM_URL  # Alias

# =============================================================================
# API CONFIGURATION
# =============================================================================

# API Base URL
API_BASE_URL: Final[str] = "https://ladvckxztcleljbiomcf.supabase.co/functions/v1"

# Database Limits
SQLITE_MAX_VARIABLES: Final[int] = 999  # SQLite query placeholder limit

# Batch Sizing (for API requests)
# Balance between network efficiency and server load
API_BATCH_SIZE: Final[int] = 1000      # Default/initial batch size
API_MAX_BATCH_SIZE: Final[int] = 2000  # Maximum (adaptive batching ceiling)
API_MIN_BATCH_SIZE: Final[int] = 200   # Minimum (adaptive batching floor)

# =============================================================================
# TIMING CONFIGURATION
# =============================================================================

# Request Timeouts (seconds)
SYNC_TIMEOUT_SECONDS: Final[int] = 30      # Standard API operations
DOWNLOAD_TIMEOUT_SECONDS: Final[int] = 120 # Large downloads/imports

# Adaptive Batching Targets
# Batch size adjusts to keep requests within this duration range
TARGET_REQUEST_DURATION_MIN: Final[float] = 2.0  # Speed up if faster
TARGET_REQUEST_DURATION_MAX: Final[float] = 5.0  # Slow down if slower

# Retry Behavior
DEFAULT_MAX_RETRIES: Final[int] = 3  # Maximum retry attempts

# =============================================================================
# SECURITY
# =============================================================================

# Token Validation
MIN_TOKEN_LENGTH: Final[int] = 20  # Minimum valid JWT token length

# =============================================================================
# STUDY STATISTICS
# =============================================================================

# Anki Card Types
RETENTION_DAYS_LOOKBACK: Final[int] = 30
LEARNING_CARD_TYPE: Final[int] = 1
REVIEW_CARD_TYPE: Final[int] = 2
RELEARNING_CARD_TYPE: Final[int] = 3

# =============================================================================
# SUPPORT & CONTACT
# =============================================================================

SUPPORT_EMAIL: Final[str] = "nottorney@gmail.com"
FEEDBACK_URL: Final[str] = f"{BASE_URL}/help"

# =============================================================================
# VALIDATION (fails fast on import if misconfigured)
# =============================================================================

assert API_MIN_BATCH_SIZE < API_BATCH_SIZE < API_MAX_BATCH_SIZE, \
    "Batch sizes must be: MIN < DEFAULT < MAX"

assert TARGET_REQUEST_DURATION_MIN < TARGET_REQUEST_DURATION_MAX, \
    "Target duration MIN must be less than MAX"

assert SYNC_TIMEOUT_SECONDS < DOWNLOAD_TIMEOUT_SECONDS, \
    "Download timeout should exceed sync timeout"

assert DEFAULT_MAX_RETRIES > 0, "Must allow at least one retry"

assert MIN_TOKEN_LENGTH >= 10, "Token validation too permissive"