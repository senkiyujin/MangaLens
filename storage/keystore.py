"""
storage/keystore.py — API key storage via Windows Credential Manager.

Uses the `keyring` library which on Windows delegates to Windows Credential
Manager (DPAPI-encrypted).  The key is never written to a plaintext file and
never appears in logs.
"""

from __future__ import annotations

import keyring
import keyring.errors
from config import KEYRING_SERVICE, KEYRING_USERNAME


def save_api_key(provider: str, api_key: str) -> None:
    """Persist the API key for a specific provider to Windows Credential Manager."""
    username = f"{KEYRING_USERNAME}_{provider.lower()}"
    keyring.set_password(KEYRING_SERVICE, username, api_key)


def load_api_key(provider: str) -> str | None:
    """
    Retrieve the stored API key for a specific provider.
    Returns None if no key has been saved yet.
    """
    try:
        username = f"{KEYRING_USERNAME}_{provider.lower()}"
        return keyring.get_password(KEYRING_SERVICE, username)
    except keyring.errors.KeyringError:
        return None


def delete_api_key(provider: str) -> None:
    """Remove the stored key for a specific provider."""
    try:
        username = f"{KEYRING_USERNAME}_{provider.lower()}"
        keyring.delete_password(KEYRING_SERVICE, username)
    except keyring.errors.PasswordDeleteError:
        pass


def has_api_key(provider: str) -> bool:
    """Return True if a key for the provider is stored."""
    return load_api_key(provider) is not None


_ACTIVE_PROVIDER_KEY = "active_ai_provider"

def save_active_provider(provider: str) -> None:
    """Store the user's preferred AI provider."""
    keyring.set_password(KEYRING_SERVICE, _ACTIVE_PROVIDER_KEY, provider.strip())

def load_active_provider() -> str:
    """Load the user's preferred AI provider. Default to 'gemini'."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _ACTIVE_PROVIDER_KEY)
        return val if val else "gemini"
    except keyring.errors.KeyringError:
        return "gemini"



_MANGA_TITLE_KEY = "manga_title"
_LANGUAGE_KEY = "language_pref"

def save_language(lang: str) -> None:
    """Save the language preference (e.g., 'en', 'tr')."""
    keyring.set_password(KEYRING_SERVICE, _LANGUAGE_KEY, lang)

def load_language() -> str:
    """Load the language preference. Defaults to 'en'."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _LANGUAGE_KEY)
        if val:
            return val
    except keyring.errors.KeyringError:
        pass
    return "en"


def save_manga_title(title: str) -> None:
    """Store optional Manga Title context."""
    keyring.set_password(KEYRING_SERVICE, _MANGA_TITLE_KEY, title.strip())


def load_manga_title() -> str | None:
    """Load stored Manga Title context."""
    try:
        return keyring.get_password(KEYRING_SERVICE, _MANGA_TITLE_KEY)
    except keyring.errors.KeyringError:
        return None


def delete_manga_title() -> None:
    """Delete stored Manga Title context."""
    try:
        keyring.delete_password(KEYRING_SERVICE, _MANGA_TITLE_KEY)
    except keyring.errors.PasswordDeleteError:
        pass


_PANEL_MODE_KEY = "panel_mode_active"
_PANEL_BOUNDS_KEY = "panel_bounds"


def save_panel_mode(is_active: bool) -> None:
    """Save whether the panel finding tool is active."""
    val = "1" if is_active else "0"
    keyring.set_password(KEYRING_SERVICE, _PANEL_MODE_KEY, val)


def load_panel_mode() -> bool:
    """Load whether the panel finding tool is active."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _PANEL_MODE_KEY)
        if val is None:
            return True # Default to True
        return val == "1"
    except keyring.errors.KeyringError:
        return True


def save_panel_bounds(bounds: tuple[int, int, int, int]) -> None:
    """Save panel finding tool coordinates (x, y, w, h)."""
    val = ",".join(map(str, bounds))
    keyring.set_password(KEYRING_SERVICE, _PANEL_BOUNDS_KEY, val)


def load_panel_bounds() -> tuple[int, int, int, int] | None:
    """Load panel finding tool coordinates (x, y, w, h)."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _PANEL_BOUNDS_KEY)
        if val:
            parts = [int(p) for p in val.split(",")]
            if len(parts) == 4:
                return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        pass
    return None

_THEME_MODE_KEY = "theme_mode_dark"

def save_theme_mode(is_dark: bool) -> None:
    """Save the theme mode preference."""
    val = "1" if is_dark else "0"
    keyring.set_password(KEYRING_SERVICE, _THEME_MODE_KEY, val)

def load_theme_mode() -> bool:
    """Load theme mode preference, default to True (Dark Mode)."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _THEME_MODE_KEY)
        if val is not None:
            return val == "1"
    except keyring.errors.KeyringError:
        pass
    return True


_TARGET_LANG_KEY = "target_translation_language"

def save_target_lang(lang: str) -> None:
    """Save the target translation language preference."""
    keyring.set_password(KEYRING_SERVICE, _TARGET_LANG_KEY, lang.strip())


def load_target_lang() -> str:
    """Load the target translation language. Defaults to 'Türkçe'."""
    try:
        val = keyring.get_password(KEYRING_SERVICE, _TARGET_LANG_KEY)
        if val:
            return val
    except keyring.errors.KeyringError:
        pass
    return "Türkçe"
