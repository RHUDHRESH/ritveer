
-- Enable PostGIS extension if available
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- Core system tables
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    state JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    state JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Business domain tables
CREATE TABLE IF NOT EXISTS artisans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    location POINT,  -- PostGIS point for geographic coordinates
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    specialties TEXT[],  -- Array of artisan specialties
    rating DECIMAL(3, 2) CHECK (rating >= 0 AND rating <= 5),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,  -- Additional artisan information
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    location POINT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    product_categories TEXT[],  -- Array of product categories
    min_order_amount DECIMAL(10, 2),
    max_order_amount DECIMAL(10, 2),
    rating DECIMAL(3, 2) CHECK (rating >= 0 AND rating <= 5),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    artisan_id INTEGER REFERENCES artisans(id) ON DELETE CASCADE,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    order_number VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) CHECK (status IN ('pending', 'confirmed', 'in_progress', 'shipped', 'delivered', 'cancelled')),
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    order_items JSONB,  -- Array of order line items
    shipping_address JSONB,
    billing_address JSONB,
    notes TEXT,
    estimated_delivery DATE,
    actual_delivery DATE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_state (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    state_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, session_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);

-- Artisans indexes
CREATE INDEX IF NOT EXISTS idx_artisans_email ON artisans(email);
CREATE INDEX IF NOT EXISTS idx_artisans_location ON artisans USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_artisans_specialties ON artisans USING GIN (specialties);
CREATE INDEX IF NOT EXISTS idx_artisans_rating ON artisans(rating);
CREATE INDEX IF NOT EXISTS idx_artisans_active ON artisans(is_active);

-- Suppliers indexes
CREATE INDEX IF NOT EXISTS idx_suppliers_email ON suppliers(email);
CREATE INDEX IF NOT EXISTS idx_suppliers_location ON suppliers USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_suppliers_categories ON suppliers USING GIN (product_categories);
CREATE INDEX IF NOT EXISTS idx_suppliers_rating ON suppliers(rating);
CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers(is_active);

-- Orders indexes
CREATE INDEX IF NOT EXISTS idx_orders_artisan ON orders(artisan_id);
CREATE INDEX IF NOT EXISTS idx_orders_supplier ON orders(supplier_id);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_delivery ON orders(estimated_delivery);

-- Agent state indexes
CREATE INDEX IF NOT EXISTS idx_agent_state_agent ON agent_state(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_state_session ON agent_state(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_state_active ON agent_state(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_state_expires ON agent_state(expires_at);
