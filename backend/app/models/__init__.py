"""SQLAlchemy ORM models for InfraGuard.

Tables:
  users, districts, infrastructure_types, reports, images,
  verifications, priority_scores, notifications, admin_actions
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# ----- Roles & enums (string columns for portability) -----
ROLE_CITIZEN = "citizen"
ROLE_ADMIN = "admin"
ROLE_OFFICIAL = "official"

STATUS_REPORTED = "Reported"
STATUS_VERIFIED = "Verified"
STATUS_REJECTED = "Rejected"
STATUS_ASSIGNED = "Assigned"
STATUS_IN_PROGRESS = "In Progress"
STATUS_RESOLVED = "Resolved"

SEVERITY_LOW = "Low"
SEVERITY_MODERATE = "Moderate"
SEVERITY_HIGH = "High"
SEVERITY_CRITICAL = "Critical"


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=ROLE_CITIZEN, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    admin_actions = relationship("AdminAction", back_populates="admin")


class District(Base, TimestampMixin):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=True, index=True)
    state = Column(String(100), nullable=True)
    population = Column(Integer, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    geom = Column(Text, nullable=True)
    centroid = Column(Text, nullable=True)


class InfrastructureType(Base, TimestampMixin):
    __tablename__ = "infrastructure_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    code = Column(String(20), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    default_priority_weight = Column(Float, default=5.0, nullable=False)
    icon = Column(String(50), nullable=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_code = Column(String(30), unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    infrastructure_type_id = Column(
        Integer,
        ForeignKey("infrastructure_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    address = Column(String(500), nullable=True)

    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    geom = Column(Text, nullable=True, index=True)

    # AI-derived
    ai_severity = Column(String(20), nullable=True, index=True)
    ai_confidence = Column(Float, nullable=True)
    ai_damage_type = Column(String(100), nullable=True)
    ai_features = Column(Text, nullable=True)  # JSON serialized

    # Admin override / final severity
    final_severity = Column(String(20), nullable=True, index=True)

    status = Column(String(30), default=STATUS_REPORTED, nullable=False, index=True)
    credibility_score = Column(Float, default=0.0, nullable=False)

    verification_count = Column(Integer, default=0, nullable=False)
    upvote_count = Column(Integer, default=0, nullable=False)
    downvote_count = Column(Integer, default=0, nullable=False)

    assigned_team = Column(String(150), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reports")
    district = relationship("District")
    infrastructure_type = relationship("InfrastructureType")
    images = relationship("Image", back_populates="report", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="report", cascade="all, delete-orphan")
    priority_scores = relationship("PriorityScore", back_populates="report", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="report")
    admin_actions = relationship("AdminAction", back_populates="report")

    __table_args__ = (
        CheckConstraint(
            f"status IN ('{STATUS_REPORTED}','{STATUS_VERIFIED}','{STATUS_REJECTED}',"
            f"'{STATUS_ASSIGNED}','{STATUS_IN_PROGRESS}','{STATUS_RESOLVED}')",
            name="ck_reports_status",
        ),
        CheckConstraint(
            f"ai_severity IS NULL OR ai_severity IN "
            f"('{SEVERITY_LOW}','{SEVERITY_MODERATE}','{SEVERITY_HIGH}','{SEVERITY_CRITICAL}')",
            name="ck_reports_ai_severity",
        ),
        Index("ix_reports_status_severity", "status", "ai_severity"),
        Index("ix_reports_district_status", "district_id", "status"),
    )


class Image(Base, TimestampMixin):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    caption = Column(String(255), nullable=True)

    report = relationship("Report", back_populates="images")


class Verification(Base, TimestampMixin):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    severity_vote = Column(String(20), nullable=True)
    comment = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=True, nullable=False)
    image_path = Column(String(500), nullable=True)

    report = relationship("Report", back_populates="verifications")
    user = relationship("User", back_populates="verifications")

    __table_args__ = (
        UniqueConstraint("report_id", "user_id", name="uq_verifications_report_user"),
        CheckConstraint(
            f"severity_vote IS NULL OR severity_vote IN "
            f"('{SEVERITY_LOW}','{SEVERITY_MODERATE}','{SEVERITY_HIGH}','{SEVERITY_CRITICAL}')",
            name="ck_verifications_severity_vote",
        ),
    )


class PriorityScore(Base, TimestampMixin):
    __tablename__ = "priority_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False, index=True)
    rank = Column(Integer, nullable=True, index=True)

    # Component scores (transparent / explainable)
    severity_component = Column(Float, default=0.0, nullable=False)
    verification_component = Column(Float, default=0.0, nullable=False)
    population_component = Column(Float, default=0.0, nullable=False)
    road_importance_component = Column(Float, default=0.0, nullable=False)
    hospital_proximity_component = Column(Float, default=0.0, nullable=False)
    school_proximity_component = Column(Float, default=0.0, nullable=False)
    utility_importance_component = Column(Float, default=0.0, nullable=False)
    time_urgency_component = Column(Float, default=0.0, nullable=False)
    verification_status_component = Column(Float, default=0.0, nullable=False)

    recommended_response_time = Column(String(50), nullable=True)
    resource_urgency = Column(String(30), nullable=True)

    report = relationship("Report", back_populates="priority_scores")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="info", nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)

    user = relationship("User", back_populates="notifications")
    report = relationship("Report", back_populates="notifications")


class AdminAction(Base, TimestampMixin):
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    report_id = Column(        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    admin = relationship("User", back_populates="admin_actions")
    report = relationship("Report", back_populates="admin_actions")
