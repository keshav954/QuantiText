"""
Models package — import all models here so Alembic can discover them.
Every new model file MUST be imported below for autogenerate to work.
"""

from app.models.alert import Alert  # noqa: F401
from app.models.analytics import Anomaly, DailySales, Forecast  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base  # noqa: F401

# ── Chat & Feedback models (Gap 1 + Gap 2) ───────────────
from app.models.chat_session import ChatMessage, ChatSession  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.feedback import CustomerFeedback  # noqa: F401
from app.models.inventory import Inventory  # noqa: F401
from app.models.order import Order, OrderItem  # noqa: F401

# ── Entity models ────────────────────────────────────────
from app.models.org import Org  # noqa: F401
from app.models.product import Category, Product  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.user import User  # noqa: F401
