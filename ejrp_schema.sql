-- EJRP: EVE Jump Route Planner
-- Supabase schema — run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS ejrp_routes (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(300) NOT NULL,
    ship_name           VARCHAR(100) NOT NULL,
    ship_class          VARCHAR(50),
    origin_system       VARCHAR(200) NOT NULL,
    destination_system  VARCHAR(200) NOT NULL,
    jdc_level           INTEGER DEFAULT 5 CHECK (jdc_level BETWEEN 0 AND 5),
    jdfe_level          INTEGER DEFAULT 5 CHECK (jdfe_level BETWEEN 0 AND 5),
    total_jumps         INTEGER DEFAULT 0,
    total_distance_ly   NUMERIC(10,4) DEFAULT 0,
    total_fuel          INTEGER DEFAULT 0,
    fuel_type           VARCHAR(60),
    fuel_cost_isk       NUMERIC(20,2) DEFAULT 0,
    fuel_price_isk      NUMERIC(12,2) DEFAULT 0,
    status              VARCHAR(30) DEFAULT 'saved',
    tags                TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ejrp_routes_ship ON ejrp_routes(ship_name);
CREATE INDEX IF NOT EXISTS idx_ejrp_routes_status ON ejrp_routes(status);
CREATE INDEX IF NOT EXISTS idx_ejrp_routes_created ON ejrp_routes(created_at DESC);

CREATE TABLE IF NOT EXISTS ejrp_route_steps (
    id              SERIAL PRIMARY KEY,
    route_id        INTEGER NOT NULL REFERENCES ejrp_routes(id) ON DELETE CASCADE,
    step_number     INTEGER NOT NULL,
    from_system     VARCHAR(200) NOT NULL,
    to_system       VARCHAR(200) NOT NULL,
    distance_ly     NUMERIC(10,4) NOT NULL,
    fuel_used       INTEGER NOT NULL,
    cost_isk        NUMERIC(20,2) DEFAULT 0,
    within_range    BOOLEAN DEFAULT TRUE,
    jump_type       VARCHAR(30) DEFAULT 'jump',
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ejrp_steps_route ON ejrp_route_steps(route_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ejrp_steps_order ON ejrp_route_steps(route_id, step_number);

CREATE TABLE IF NOT EXISTS ejrp_fuel_prices (
    id              SERIAL PRIMARY KEY,
    fuel_type       VARCHAR(60) NOT NULL UNIQUE,
    price_per_unit  NUMERIC(12,2) NOT NULL DEFAULT 0,
    source          VARCHAR(100) DEFAULT 'manual',
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ejrp_jump_log (
    id              SERIAL PRIMARY KEY,
    route_id        INTEGER REFERENCES ejrp_routes(id) ON DELETE SET NULL,
    route_name      VARCHAR(300),
    ship_name       VARCHAR(100),
    from_system     VARCHAR(200) NOT NULL,
    to_system       VARCHAR(200) NOT NULL,
    total_jumps     INTEGER DEFAULT 0,
    total_distance_ly NUMERIC(10,4) DEFAULT 0,
    total_fuel      INTEGER DEFAULT 0,
    total_cost_isk  NUMERIC(20,2) DEFAULT 0,
    pilot_name      VARCHAR(200),
    executed_at     TIMESTAMPTZ DEFAULT NOW(),
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_ejrp_log_route ON ejrp_jump_log(route_id);
CREATE INDEX IF NOT EXISTS idx_ejrp_log_executed ON ejrp_jump_log(executed_at DESC);

INSERT INTO ejrp_fuel_prices (fuel_type, price_per_unit, source)
VALUES
    ('Oxygen Isotopes',   500.00, 'jita'),
    ('Hydrogen Isotopes', 500.00, 'jita'),
    ('Nitrogen Isotopes', 500.00, 'jita'),
    ('Helium Isotopes',   500.00, 'jita')
ON CONFLICT (fuel_type) DO NOTHING;
