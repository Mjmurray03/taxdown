"""
API routes package.

Contains all route definitions organized by domain.
"""

from . import properties
from . import analysis
from . import appeals
from . import reports
from . import portfolios

__all__ = ["properties", "analysis", "appeals", "reports", "portfolios"]
