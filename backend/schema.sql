-- ============================================================
-- TCF-ai (Munim.ai) — Supabase PostgreSQL Schema
-- Run this in your Supabase SQL editor.
-- ============================================================

-- ── Extensions ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── ENUM Types ──────────────────────────────────────────────

CREATE TYPE itc_status AS ENUM (
    'CONFIRMED',
    'FIXABLE_BLOCKED',
    'AT_RISK',
    'INELIGIBLE',
    'FRAUD_FLAGGED',
    'PENDING'
);

CREATE TYPE action_type AS ENUM (
    'FRAUD_FLAG',
    'ITC_AT_RISK',
    'FIXABLE_BLOCK',
    'SUPPLIER_NON_COMPLIANT',
    'RECONCILIATION_MISMATCH',
    'MISSING_DOCUMENT'
);

CREATE TYPE action_severity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');

CREATE TYPE reconciliation_match_type AS ENUM (
    'EXACT',
    'FUZZY',
    'AMOUNT_DATE',
    'UNMATCHED'
);

CREATE TYPE onboarding_state AS ENUM (
    'INIT',
    'NAME_RECEIVED',
    'GSTIN_RECEIVED',
    'CONFIRMED',
    'ACTIVE'
);

-- ── Tables ──────────────────────────────────────────────────

-- 1. CA (Chartered Accountant) Users
CREATE TABLE ca_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    firm_name TEXT,
    phone TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Traders (managed by CAs)
CREATE TABLE traders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ca_id UUID NOT NULL REFERENCES ca_users(id) ON DELETE CASCADE,
    business_name TEXT NOT NULL,
    gstin TEXT,
    phone TEXT UNIQUE,
    email TEXT,
    munim_email TEXT UNIQUE,  -- dedicated Munim email for this trader
    state_code TEXT,
    onboarding_state onboarding_state DEFAULT 'INIT',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_traders_ca_id ON traders(ca_id);
CREATE INDEX idx_traders_phone ON traders(phone);
CREATE INDEX idx_traders_gstin ON traders(gstin);
CREATE INDEX idx_traders_munim_email ON traders(munim_email);

-- 3. Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    supplier_name TEXT,
    supplier_gstin TEXT,
    invoice_number TEXT,
    invoice_date DATE,
    total_taxable_value NUMERIC(15, 2),
    cgst NUMERIC(15, 2) DEFAULT 0,
    sgst NUMERIC(15, 2) DEFAULT 0,
    igst NUMERIC(15, 2) DEFAULT 0,
    cess NUMERIC(15, 2) DEFAULT 0,
    total_amount NUMERIC(15, 2),
    place_of_supply TEXT,
    reverse_charge BOOLEAN DEFAULT FALSE,
    itc_status itc_status DEFAULT 'PENDING',
    itc_blocked_reason TEXT,
    itc_blocked_section TEXT,
    fraud_score INTEGER DEFAULT 0,
    fraud_signals JSONB DEFAULT '[]'::jsonb,
    extraction_confidence NUMERIC(3, 2) DEFAULT 0,
    source TEXT DEFAULT 'whatsapp',  -- 'whatsapp', 'email', 'upload'
    raw_image_url TEXT,
    period TEXT,  -- e.g. '2026-07' (YYYY-MM)
    reconciliation_status reconciliation_match_type DEFAULT 'UNMATCHED',
    matched_gstr2b_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_trader_id ON invoices(trader_id);
CREATE INDEX idx_invoices_period ON invoices(trader_id, period);
CREATE INDEX idx_invoices_supplier ON invoices(supplier_gstin);
CREATE INDEX idx_invoices_recon ON invoices(supplier_gstin, invoice_number);
CREATE INDEX idx_invoices_itc_status ON invoices(itc_status);

-- 4. Invoice Line Items
CREATE TABLE invoice_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT,
    hsn_code TEXT,
    quantity NUMERIC(10, 3),
    rate NUMERIC(15, 2),
    taxable_value NUMERIC(15, 2),
    cgst_rate NUMERIC(5, 2) DEFAULT 0,
    sgst_rate NUMERIC(5, 2) DEFAULT 0,
    igst_rate NUMERIC(5, 2) DEFAULT 0,
    cgst NUMERIC(15, 2) DEFAULT 0,
    sgst NUMERIC(15, 2) DEFAULT 0,
    igst NUMERIC(15, 2) DEFAULT 0,
    cess NUMERIC(15, 2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX idx_line_items_hsn ON invoice_line_items(hsn_code);

-- 5. GSTR-2B Records (uploaded by CA)
CREATE TABLE gstr2b_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    period TEXT NOT NULL,  -- 'YYYY-MM'
    supplier_gstin TEXT NOT NULL,
    supplier_name TEXT,
    invoice_number TEXT,
    invoice_date DATE,
    invoice_value NUMERIC(15, 2),
    taxable_value NUMERIC(15, 2),
    igst NUMERIC(15, 2) DEFAULT 0,
    cgst NUMERIC(15, 2) DEFAULT 0,
    sgst NUMERIC(15, 2) DEFAULT 0,
    cess NUMERIC(15, 2) DEFAULT 0,
    place_of_supply TEXT,
    reverse_charge BOOLEAN DEFAULT FALSE,
    itc_available BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gstr2b_trader_period ON gstr2b_records(trader_id, period);
CREATE INDEX idx_gstr2b_supplier ON gstr2b_records(supplier_gstin, invoice_number);

-- 6. Reconciliation Results
CREATE TABLE reconciliation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    gstr2b_id UUID REFERENCES gstr2b_records(id) ON DELETE SET NULL,
    match_type reconciliation_match_type NOT NULL,
    match_confidence NUMERIC(5, 2),
    amount_difference NUMERIC(15, 2),
    date_difference INTEGER,  -- days
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recon_trader_period ON reconciliation_results(trader_id, period);

-- 7. Action Items (prioritized action queue)
CREATE TABLE action_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    action_type action_type NOT NULL,
    severity action_severity NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    affected_amount NUMERIC(15, 2) DEFAULT 0,
    recommended_fix TEXT,
    vendor_gstin TEXT,
    vendor_name TEXT,
    vendor_phone TEXT,
    vendor_email TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES ca_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_trader ON action_items(trader_id, is_resolved);
CREATE INDEX idx_actions_severity ON action_items(severity);

-- 8. Supplier Profiles (health tracking)
CREATE TABLE supplier_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    supplier_gstin TEXT NOT NULL,
    supplier_name TEXT,
    trade_name TEXT,
    registration_date DATE,
    business_type TEXT,
    state_code TEXT,
    total_months_tracked INTEGER DEFAULT 0,
    months_filed INTEGER DEFAULT 0,
    compliance_score NUMERIC(5, 2) DEFAULT 100,
    total_invoice_count INTEGER DEFAULT 0,
    total_invoice_value NUMERIC(15, 2) DEFAULT 0,
    average_invoice_value NUMERIC(15, 2) DEFAULT 0,
    last_invoice_date DATE,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trader_id, supplier_gstin)
);

CREATE INDEX idx_suppliers_trader ON supplier_profiles(trader_id);
CREATE INDEX idx_suppliers_gstin ON supplier_profiles(supplier_gstin);
CREATE INDEX idx_suppliers_flagged ON supplier_profiles(trader_id, is_flagged);

-- 9. Conversations (WhatsApp state machine)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone TEXT UNIQUE NOT NULL,
    trader_id UUID REFERENCES traders(id) ON DELETE SET NULL,
    current_state onboarding_state DEFAULT 'INIT',
    context JSONB DEFAULT '{}'::jsonb,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_phone ON conversations(phone);

-- 10. Compliance Deadlines
CREATE TABLE compliance_deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    return_type TEXT NOT NULL,  -- 'GSTR-1', 'GSTR-2B', 'GSTR-3B', 'GSTR-9'
    period TEXT NOT NULL,       -- 'YYYY-MM'
    due_date DATE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deadlines_period ON compliance_deadlines(period);
CREATE INDEX idx_deadlines_due ON compliance_deadlines(due_date);

-- 11. Reports (generated PDFs)
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id UUID NOT NULL REFERENCES traders(id) ON DELETE CASCADE,
    ca_id UUID NOT NULL REFERENCES ca_users(id),
    period TEXT NOT NULL,
    report_type TEXT DEFAULT 'compliance',
    file_path TEXT,  -- Supabase Storage path
    file_url TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_trader ON reports(trader_id, period);

-- ── Row Level Security ──────────────────────────────────────

ALTER TABLE ca_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE traders ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE gstr2b_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Service role key bypasses RLS, so these policies are for
-- future direct-client access via anon key if needed.

-- CA can see only their own record
CREATE POLICY "ca_own" ON ca_users
    FOR ALL USING (id = auth.uid());

-- CA can see only their own traders
CREATE POLICY "ca_traders" ON traders
    FOR ALL USING (ca_id = auth.uid());

-- CA can see invoices for their traders
CREATE POLICY "ca_invoices" ON invoices
    FOR ALL USING (
        trader_id IN (SELECT id FROM traders WHERE ca_id = auth.uid())
    );

-- CA can see line items for their traders' invoices
CREATE POLICY "ca_line_items" ON invoice_line_items
    FOR ALL USING (
        invoice_id IN (
            SELECT i.id FROM invoices i
            JOIN traders t ON i.trader_id = t.id
            WHERE t.ca_id = auth.uid()
        )
    );

-- CA can see GSTR-2B records for their traders
CREATE POLICY "ca_gstr2b" ON gstr2b_records
    FOR ALL USING (
        trader_id IN (SELECT id FROM traders WHERE ca_id = auth.uid())
    );

-- CA can see reconciliation results for their traders
CREATE POLICY "ca_recon" ON reconciliation_results
    FOR ALL USING (
        trader_id IN (SELECT id FROM traders WHERE ca_id = auth.uid())
    );

-- CA can see action items for their traders
CREATE POLICY "ca_actions" ON action_items
    FOR ALL USING (
        trader_id IN (SELECT id FROM traders WHERE ca_id = auth.uid())
    );

-- CA can see supplier profiles for their traders
CREATE POLICY "ca_suppliers" ON supplier_profiles
    FOR ALL USING (
        trader_id IN (SELECT id FROM traders WHERE ca_id = auth.uid())
    );

-- Conversations are accessible by service role only (no anon policy)
CREATE POLICY "service_only_conversations" ON conversations
    FOR ALL USING (FALSE);

-- Reports accessible by owning CA
CREATE POLICY "ca_reports" ON reports
    FOR ALL USING (ca_id = auth.uid());

-- ── Updated-at trigger ──────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ca_users_updated
    BEFORE UPDATE ON ca_users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_traders_updated
    BEFORE UPDATE ON traders FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_invoices_updated
    BEFORE UPDATE ON invoices FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_suppliers_updated
    BEFORE UPDATE ON supplier_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_conversations_updated
    BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Seed: Compliance Deadlines (FY 2026–27) ─────────────────

INSERT INTO compliance_deadlines (return_type, period, due_date, description) VALUES
    ('GSTR-1',  '2026-04', '2026-05-11', 'GSTR-1 for April 2026'),
    ('GSTR-3B', '2026-04', '2026-05-20', 'GSTR-3B for April 2026'),
    ('GSTR-1',  '2026-05', '2026-06-11', 'GSTR-1 for May 2026'),
    ('GSTR-3B', '2026-05', '2026-06-20', 'GSTR-3B for May 2026'),
    ('GSTR-1',  '2026-06', '2026-07-11', 'GSTR-1 for June 2026'),
    ('GSTR-3B', '2026-06', '2026-07-20', 'GSTR-3B for June 2026'),
    ('GSTR-1',  '2026-07', '2026-08-11', 'GSTR-1 for July 2026'),
    ('GSTR-3B', '2026-07', '2026-08-20', 'GSTR-3B for July 2026'),
    ('GSTR-1',  '2026-08', '2026-09-11', 'GSTR-1 for August 2026'),
    ('GSTR-3B', '2026-08', '2026-09-20', 'GSTR-3B for August 2026'),
    ('GSTR-1',  '2026-09', '2026-10-11', 'GSTR-1 for September 2026'),
    ('GSTR-3B', '2026-09', '2026-10-20', 'GSTR-3B for September 2026'),
    ('GSTR-1',  '2026-10', '2026-11-11', 'GSTR-1 for October 2026'),
    ('GSTR-3B', '2026-10', '2026-11-20', 'GSTR-3B for October 2026'),
    ('GSTR-1',  '2026-11', '2026-12-11', 'GSTR-1 for November 2026'),
    ('GSTR-3B', '2026-11', '2026-12-20', 'GSTR-3B for November 2026'),
    ('GSTR-1',  '2026-12', '2027-01-11', 'GSTR-1 for December 2026'),
    ('GSTR-3B', '2026-12', '2027-01-20', 'GSTR-3B for December 2026'),
    ('GSTR-1',  '2027-01', '2027-02-11', 'GSTR-1 for January 2027'),
    ('GSTR-3B', '2027-01', '2027-02-20', 'GSTR-3B for January 2027'),
    ('GSTR-1',  '2027-02', '2027-03-11', 'GSTR-1 for February 2027'),
    ('GSTR-3B', '2027-02', '2027-03-20', 'GSTR-3B for February 2027'),
    ('GSTR-1',  '2027-03', '2027-04-11', 'GSTR-1 for March 2027'),
    ('GSTR-3B', '2027-03', '2027-04-20', 'GSTR-3B for March 2027'),
    ('GSTR-9',  '2026-27', '2027-12-31', 'Annual Return for FY 2026–27');
