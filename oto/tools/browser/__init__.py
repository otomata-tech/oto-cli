"""
Browser automation tools.

BrowserClient comes from o-browser package.
Domain-specific clients (LinkedIn, Crunchbase...) live here.
"""

try:
    from o_browser import BrowserClient
except ImportError:
    BrowserClient = None

# Site adapters are o-browser plugins (separate distributions, entry-point group
# "o_browser.sites"). VivaTech ships as `o-browser-vivatech`; discovered dynamically.
try:
    from o_browser import load_site
    VivaTechClient = load_site("vivatech")
except Exception:
    VivaTechClient = None

from .linkedin import LinkedInClient  # noqa: linkedin/ subpackage
from .crunchbase import CrunchbaseClient
from .pappers import PappersClient
from .g2 import G2Client
from .indeed import IndeedClient
from .google import GoogleSearchClient
from .sncf import SNCFClient

__all__ = [
    "BrowserClient",
    "VivaTechClient",
    "LinkedInClient",
    "CrunchbaseClient",
    "PappersClient",
    "G2Client",
    "IndeedClient",
    "GoogleSearchClient",
    "SNCFClient",
]
