"""
nextcloud_plugin - Nextcloud storage plugin for OSF / GravyValet / WaterButler

This package provides the three integrated pieces of a storage-addon triplet:
- addon_imp: Foreign Addon Imp for GravyValet
- provider:  WaterButler provider for file operations (WebDAV)
- addon:     osf.io addon for user and project management
"""

from .__version__ import __version__

__all__ = ["__version__"]
