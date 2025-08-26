"""
Router Manager version information
"""

__version__ = "1.0.0"
__title__ = "Router Manager"
__description__ = "Web-based router management system for RHEL and Rocky Linux"
__author__ = "Router Manager Team"
__license__ = "MIT"
__url__ = "https://github.com/your-org/router-manager"

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
