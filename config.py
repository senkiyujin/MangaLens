"""
MangaLens — Configuration & Constants
All tuneable values live here. Never scatter these through core logic.
"""

TRANSLATION_PROVIDER: str = "gemini"

# ─────────────────────────────────────────────
# Gemini Model Configuration
# ─────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-flash-lite-latest"

# Keychain / credential storage
# ─────────────────────────────────────────────
KEYRING_SERVICE: str = "MangaLens"
KEYRING_USERNAME: str = "api_key"

# ─────────────────────────────────────────────
# Overlay border (always-on-top frame)
# ─────────────────────────────────────────────
BORDER_COLOR: str = "#B8860B"   # Dark golden yellow — visible on any background
BORDER_WIDTH: int = 3           # px, thin so it doesn't distract

# ─────────────────────────────────────────────
# Lasso drawing visuals
# ─────────────────────────────────────────────
LASSO_LINE_COLOR: str = "#FFD700"   # Bright gold while drawing
LASSO_LINE_WIDTH: int = 2
LASSO_FILL_COLOR: str = "#FFD70022" # Very subtle fill (RGBA hex; Tkinter uses stipple fallback)
LASSO_DOT_RADIUS: int = 4           # Starting-point indicator dot

# ─────────────────────────────────────────────
# Panel Bulma Aracı visuals
# ─────────────────────────────────────────────
PANEL_COLOR: str = "#9400D3"        # Deep purple/violet
PANEL_LINE_WIDTH: int = 3
PANEL_MIN_SIZE: int = 100

# ─────────────────────────────────────────────
# Translation tooltip (floating label)
# ─────────────────────────────────────────────
TOOLTIP_BG: str = "#1A1A1A"               # Near-black (alpha via TOOLTIP_ALPHA below)
TOOLTIP_FG: str = "#F5F5F5"            # Off-white text
TOOLTIP_FONT_FAMILY: str = "Segoe UI"
TOOLTIP_FONT_SIZE: int = 11
TOOLTIP_FONT_WEIGHT: str = "normal"
TOOLTIP_PADDING_X: int = 10
TOOLTIP_PADDING_Y: int = 6
TOOLTIP_CORNER_RADIUS: int = 6         # Rounded via canvas trick
TOOLTIP_ALPHA: float = 0.92            # Window-level alpha
TOOLTIP_OFFSET_X: int = 18             # px to the right of cursor
TOOLTIP_OFFSET_Y: int = 12            # px below cursor
TOOLTIP_MAX_CHARS: int = 120           # Wrap beyond this width in chars

# ─────────────────────────────────────────────
# App identity
# ─────────────────────────────────────────────
APP_NAME: str = "MangaLens"
APP_VERSION: str = "3.0.0"
TRAY_TOOLTIP: str = f"{APP_NAME} v{APP_VERSION} (Gemini AI) — Ctrl basılı tut + sürükle"

# ─────────────────────────────────────────────
# Interaction thresholds
# ─────────────────────────────────────────────
MIN_LASSO_DRAG_PX: int = 8
MIN_CAPTURE_AREA_PX: int = 400
