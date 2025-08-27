"""
Router Manager version information
"""

__version__ = "1.2.0"
__title__ = "Router Manager"
__description__ = "Web-based router management system for RHEL and Rocky Linux with nftables firewall management"
__author__ = "Router Manager Team"
__license__ = "MIT"
__url__ = "https://github.com/jskoetsier/router-manager"

VERSION = __version__
TITLE = __title__


def get_version():
    """Return the version string."""
    return __version__


def get_version_info():
    """Return version information as a dictionary."""
    return {
        "version": __version__,
        "title": __title__,
        "description": __description__,
        "author": __author__,
        "license": __license__,
        "url": __url__,
    }
