"""
Central constants for AnkiPH Addon
Single source of truth for version, URLs, and configuration
Version: 3.3.0 - Subscription-only model
"""

# Addon Info
ADDON_NAME = "AnkiPH"
ADDON_VERSION = "3.3.0"

# Base URLs - Use primary domain for all features
BASE_URL = "https://nottorney.com"

# Page URLs (derived from BASE_URL for consistency)
HOMEPAGE_URL = BASE_URL
REGISTER_URL = f"{BASE_URL}/register"
FORGOT_PASSWORD_URL = f"{BASE_URL}/forgot-password"
TERMS_URL = f"{BASE_URL}/terms"
PRIVACY_URL = f"{BASE_URL}/privacy"
PLANS_URL = f"{BASE_URL}/pricing"
DOCS_URL = f"{BASE_URL}/docs"
HELP_URL = f"{BASE_URL}/help"
CHANGELOG_URL = f"{BASE_URL}/changelog"
COMMUNITY_URL = f"{BASE_URL}/community"

# Subscription URLs (v3.3 - subscription-only model)
COLLECTION_URL = f"{BASE_URL}/collection"
PREMIUM_URL = f"{BASE_URL}/settings?tab=subscription"
SUBSCRIBE_URL = PREMIUM_URL  # Alias for subscription page
