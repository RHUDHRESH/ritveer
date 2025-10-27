"""
KARIGAR Database Models - SQLAlchemy ORM
Complete schema for artisan platform with all relationships
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text,
    ForeignKey, Enum, JSON, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
import enum

Base = declarative_base()


class ArtisanStatus(str, enum.Enum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class OrderStatus(str, enum.Enum):
    INQUIRY = "inquiry"
    QUOTE_SENT = "quote_sent"
    ACCEPTED = "accepted"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Artisan(Base):
    """Core artisan profile"""
    __tablename__ = "artisans"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    location = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Craft Details
    craft_type = Column(String(100), nullable=False)  # Potter, Weaver, etc.
    specialization = Column(String(255), nullable=True)
    experience_years = Column(Integer, nullable=True)
    skill_level = Column(String(50), nullable=True)  # beginner, intermediate, expert

    # Business Info
    status = Column(Enum(ArtisanStatus), default=ArtisanStatus.ONBOARDING)
    bio = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)

    # Metrics
    total_orders = Column(Integer, default=0)
    completed_orders = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    average_rating = Column(Float, default=0.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)

    # Relationships
    materials = relationship("MaterialInventory", back_populates="artisan", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="artisan", cascade="all, delete-orphan")
    quotes = relationship("SupplierQuote", back_populates="artisan", cascade="all, delete-orphan")
    micro_stores = relationship("MicroStore", back_populates="artisan", cascade="all, delete-orphan")
    ledger_entries = relationship("Ledger", back_populates="artisan", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_artisan_location', 'location'),
        Index('idx_artisan_craft_type', 'craft_type'),
        Index('idx_artisan_status', 'status'),
    )


class MaterialInventory(Base):
    """Materials/supplies for artisans"""
    __tablename__ = "material_inventory"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)

    material_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)  # kg, meters, pieces, etc.
    unit_cost = Column(Float, nullable=False)
    supplier_id = Column(String(36), nullable=True)

    reorder_level = Column(Float, nullable=True)
    last_ordered = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    artisan = relationship("Artisan", back_populates="materials")

    __table_args__ = (
        Index('idx_material_artisan', 'artisan_id'),
        Index('idx_material_category', 'category'),
    )


class SupplierQuote(Base):
    """Supplier quotes for materials"""
    __tablename__ = "supplier_quotes"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)

    material_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    supplier_name = Column(String(255), nullable=False)
    supplier_location = Column(String(255), nullable=True)
    supplier_phone = Column(String(20), nullable=True)
    supplier_website = Column(String(255), nullable=True)

    quoted_price = Column(Float, nullable=False)
    min_order_quantity = Column(Float, nullable=True)
    delivery_days = Column(Integer, nullable=True)

    quote_data = Column(JSON, nullable=True)  # Store full supplier data

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    artisan = relationship("Artisan", back_populates="quotes")

    __table_args__ = (
        Index('idx_quote_artisan', 'artisan_id'),
        Index('idx_quote_supplier', 'supplier_name'),
    )


class Order(Base):
    """Customer orders"""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)

    # Customer Info
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    delivery_location = Column(String(255), nullable=False)

    # Order Details
    description = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.INQUIRY)

    # Pricing
    estimated_cost = Column(Float, nullable=True)
    quoted_price = Column(Float, nullable=True)
    final_price = Column(Float, nullable=True)

    # Timeline
    order_date = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    order_data = Column(JSON, nullable=True)

    artisan = relationship("Artisan", back_populates="orders")
    ledger_entries = relationship("Ledger", foreign_keys="Ledger.order_id")

    __table_args__ = (
        Index('idx_order_artisan', 'artisan_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_date', 'order_date'),
    )


class MicroStore(Base):
    """Artisan's personal online store/catalog"""
    __tablename__ = "micro_stores"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)

    store_name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Store Stats
    products_count = Column(Integer, default=0)
    total_sales = Column(Float, default=0.0)
    total_customers = Column(Integer, default=0)

    # Store Config
    store_active = Column(Boolean, default=True)
    store_data = Column(JSON, nullable=True)  # Additional metadata

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    artisan = relationship("Artisan", back_populates="micro_stores")

    __table_args__ = (
        Index('idx_store_artisan', 'artisan_id'),
        Index('idx_store_slug', 'slug'),
    )


class Ledger(Base):
    """Financial ledger - income tracking"""
    __tablename__ = "ledger"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=True)

    # Transaction Type
    transaction_type = Column(String(50), nullable=False)  # income, expense, payment
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")

    # Payment Status
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_date = Column(DateTime, nullable=True)

    # Details
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)  # material, labor, overhead, shipping, etc.

    # Metadata
    entry_date = Column(DateTime, default=datetime.utcnow)
    month = Column(String(7), nullable=False)  # YYYY-MM format for monthly reports
    notes = Column(Text, nullable=True)

    artisan = relationship("Artisan", back_populates="ledger_entries")

    __table_args__ = (
        Index('idx_ledger_artisan', 'artisan_id'),
        Index('idx_ledger_month', 'month'),
        Index('idx_ledger_type', 'transaction_type'),
    )


class ThinkingMemory(Base):
    """Vector memory for AI reasoning - ChromaDB bridging"""
    __tablename__ = "thinking_memory"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), nullable=True)  # Link to artisan if context-specific

    # Memory Content
    memory_type = Column(String(100), nullable=False)  # observation, insight, pattern, rule
    content = Column(Text, nullable=False)

    # Embedding & Vector Info
    embedding_id = Column(String(255), nullable=True)  # ChromaDB ID
    source_agent = Column(String(100), nullable=False)  # Which agent created this

    # Metadata
    confidence = Column(Float, default=0.0)  # 0-1 confidence score
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_memory_type', 'memory_type'),
        Index('idx_memory_agent', 'source_agent'),
        Index('idx_memory_artisan', 'artisan_id'),
    )


class AgentContext(Base):
    """Stores agent state and ongoing analysis"""
    __tablename__ = "agent_context"

    id = Column(String(36), primary_key=True)
    artisan_id = Column(String(36), ForeignKey('artisans.id'), nullable=False)

    # Context Data
    session_id = Column(String(255), unique=True, nullable=False)
    context_data = Column(JSON, nullable=False)  # Full state

    # Agent Trail
    agents_involved = Column(JSON, default=list)  # List of agents that have touched this
    current_agent = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), default="active")  # active, completed, paused

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_context_session', 'session_id'),
        Index('idx_context_artisan', 'artisan_id'),
    )


# Database Initialization Functions
def init_db(database_url: str = "sqlite:///./karigar.db"):
    """Initialize database and create all tables"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def drop_all(database_url: str = "sqlite:///./karigar.db"):
    """Drop all tables (use with caution!)"""
    engine = create_engine(database_url)
    Base.metadata.drop_all(engine)


def get_session(database_url: str = "sqlite:///./karigar.db"):
    """Get database session"""
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
