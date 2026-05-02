"""SQLAlchemy 모델 패키지.

모든 모델 클래스를 여기서 import하여 ``Base.metadata``에 등록.
라우터/스크립트가 ``from app.models.X import Y``를 호출할 때 ``app.models`` 패키지가
먼저 import되며, 그 시점에 모든 모델이 mapper에 등록되므로 cross-table FK가 깨지지 않음.
"""
from app.models.base import Base
from app.models.plan import Plan
from app.models.profile import Profile
from app.models.site import Site, SiteType
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

__all__ = [
    "Base",
    "Plan",
    "Profile",
    "Site",
    "SiteType",
    "Subscription",
    "SubscriptionStatus",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceRole",
]
