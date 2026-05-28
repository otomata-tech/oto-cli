"""HTTP client vers `mcp.oto.ninja` — façade unique pour le CLI."""
from .client import NinjaClient, NinjaError

__all__ = ["NinjaClient", "NinjaError"]
