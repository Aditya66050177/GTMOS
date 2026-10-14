from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_market = Column(JSON, nullable=True)
    geography = Column(JSON, nullable=True)
    price_range = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    icp_profiles = relationship("ICPProfile", back_populates="product", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="product", cascade="all, delete-orphan")


class ICPProfile(Base):
    __tablename__ = "icp_profiles"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    industries = Column(JSON, nullable=True)
    company_size_min = Column(Integer, nullable=True)
    company_size_max = Column(Integer, nullable=True)
    geographies = Column(JSON, nullable=True)
    buyer_roles = Column(JSON, nullable=True)
    pain_points = Column(JSON, nullable=True)
    technologies = Column(JSON, nullable=True)
    buying_triggers = Column(JSON, nullable=True)
    exclusions = Column(JSON, nullable=True)

    product = relationship("Product", back_populates="icp_profiles")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    country = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    technology_stack = Column(JSON, nullable=True)
    funding = Column(String, nullable=True)
    support_team_size = Column(Integer, nullable=True)
    stage = Column(String, default="Research")
    created_at = Column(DateTime, default=datetime.utcnow)

    signals = relationship("Signal", back_populates="account", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="account", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="account", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="account", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="account", cascade="all, delete-orphan")


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    signal_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    strength = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)

    account = relationship("Account", back_populates="signals")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    icp_fit = Column(Float, nullable=True)
    company_fit = Column(Float, nullable=True)
    technology_fit = Column(Float, nullable=True)
    intent_score = Column(Float, nullable=True)
    geography_score = Column(Float, nullable=True)
    total_score = Column(Float, nullable=True)
    tier = Column(String, nullable=True)
    reasoning = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="scores")
    product = relationship("Product", back_populates="scores")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    email = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)

    account = relationship("Account", back_populates="contacts")
    activities = relationship("Activity", back_populates="contact")
    drafts = relationship("Draft", back_populates="contact")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    activity_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    activity_metadata = Column("metadata", JSON, nullable=True)

    account = relationship("Account", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    stage = Column(String, nullable=True)
    deal_value = Column(Float, nullable=True)
    probability = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="opportunities")


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    body = Column(Text, nullable=True)
    original_body = Column(Text, nullable=True)
    status = Column(String, default="pending")
    evidence_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="drafts")
    contact = relationship("Contact", back_populates="drafts")
