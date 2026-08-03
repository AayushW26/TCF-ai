import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Add Authorization header dynamically
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('tcf_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Mock fallback data for demo reliability when backend is offline
export const MOCK_TRADERS = [
  {
    id: 'trader-1',
    ca_id: 'ca-1',
    business_name: 'Shree Ganesh Traders',
    gstin: '27AADCS1234M1Z5',
    phone: '919876543210',
    email: 'contact@shreeganesh.com',
    munim_email: 'shreeganesh@munim.cloudmailin.net',
    state_code: '27',
    onboarding_state: 'ACTIVE',
    is_active: true,
  },
  {
    id: 'trader-2',
    ca_id: 'ca-1',
    business_name: 'Apex Auto Components Pvt Ltd',
    gstin: '24AAACA9876K1Z2',
    phone: '919823456789',
    email: 'billing@apexauto.in',
    munim_email: 'apexauto@munim.cloudmailin.net',
    state_code: '24',
    onboarding_state: 'ACTIVE',
    is_active: true,
  },
  {
    id: 'trader-3',
    ca_id: 'ca-1',
    business_name: 'Vardhaman Textiles',
    gstin: '07AAAFV5544P1Z9',
    phone: '919811223344',
    email: 'info@vardhamantextiles.com',
    munim_email: 'vardhaman@munim.cloudmailin.net',
    state_code: '07',
    onboarding_state: 'ACTIVE',
    is_active: true,
  }
];

export const MOCK_SUMMARY = {
  itc_summary: {
    total_itc: 485200.0,
    confirmed: 312000.0,
    at_risk: 84500.0,
    fixable_blocked: 42300.0,
    ineligible: 28400.0,
    fraud_flagged: 18000.0,
    pending: 0,
    total_invoices: 42,
    period: '2026-07'
  },
  action_count: 5,
  unresolved_actions: 4,
  supplier_count: 14,
  flagged_suppliers: 2,
  upcoming_deadlines: [
    { return_type: 'GSTR-1', period: '2026-07', due_date: '2026-08-11', description: 'GSTR-1 Monthly Return', days_remaining: 8 },
    { return_type: 'GSTR-3B', period: '2026-07', due_date: '2026-08-20', description: 'GSTR-3B Monthly Tax Return', days_remaining: 17 }
  ],
  recent_invoices: 12
};

export const MOCK_ACTIONS = [
  {
    id: 'act-1',
    trader_id: 'trader-1',
    action_type: 'FRAUD_FLAG',
    severity: 'CRITICAL',
    title: 'Fraud Alert: Benford\'s Law & Sequential Invoice Anomaly',
    description: 'Supplier Mahavir Logistics issued 4 consecutive invoices (INV-901 to INV-904) in 2 days totalling ₹1,80,000. High fraud score (78/100).',
    affected_amount: 32400.0,
    recommended_fix: 'Freeze payment & verify original physical goods receipt note before claiming ITC.',
    vendor_gstin: '27AABCM9012K1ZX',
    vendor_name: 'Mahavir Logistics & Transport',
    vendor_phone: '919898989898',
    is_resolved: false,
    created_at: '2026-08-01T10:30:00Z'
  },
  {
    id: 'act-2',
    trader_id: 'trader-1',
    action_type: 'ITC_AT_RISK',
    severity: 'HIGH',
    title: 'GSTR-2B Missing Reflection (§16(2)(c))',
    description: 'Invoice #INV-2026-441 for ₹2,45,000 from Royal Packaging is not found in GSTR-2B. Supplier GSTR-1 may be unfiled.',
    affected_amount: 44100.0,
    recommended_fix: 'Dispatch automated WhatsApp reminder to Royal Packaging asking for GSTR-1 filing proof.',
    vendor_gstin: '27AAACR4411M1ZB',
    vendor_name: 'Royal Packaging Solutions',
    vendor_phone: '919876123456',
    is_resolved: false,
    created_at: '2026-08-02T14:15:00Z'
  },
  {
    id: 'act-3',
    trader_id: 'trader-1',
    action_type: 'FIXABLE_BLOCK',
    severity: 'MEDIUM',
    title: 'Ineligible ITC Blocked under §17(5)(a) — Passenger Vehicle',
    description: 'Invoice #VH-882 contains HSN 8703 (Motor Car purchase). ITC of ₹28,400 is legally blocked under Section 17(5)(a).',
    affected_amount: 28400.0,
    recommended_fix: 'Reconcile in GSTR-3B Table 4(B)(1) as ineligible blocked credit.',
    vendor_gstin: '27AAACU1122K1Z3',
    vendor_name: 'Unnati Motors Pvt Ltd',
    vendor_phone: '919822334455',
    is_resolved: false,
    created_at: '2026-07-29T11:00:00Z'
  },
  {
    id: 'act-4',
    trader_id: 'trader-1',
    action_type: 'SUPPLIER_NON_COMPLIANT',
    severity: 'HIGH',
    title: 'Chronically Non-Compliant Supplier Flagged',
    description: 'Kothari Electronics has a compliance rating of only 40%. Filed GSTR-1 in only 2 out of 5 tracked months.',
    affected_amount: 52000.0,
    recommended_fix: 'Hold 18% GST portion of payment until vendor provides GSTR-3B filing acknowledgement.',
    vendor_gstin: '27AAACK5566J1Z1',
    vendor_name: 'Kothari Electronics & Spares',
    vendor_phone: '919833445566',
    is_resolved: false,
    created_at: '2026-07-28T09:45:00Z'
  }
];

export const MOCK_TIMELINE = [
  { period: '2026-02', confirmed: 210000, at_risk: 32000, blocked: 15000, fraud_flagged: 0, total: 257000 },
  { period: '2026-03', confirmed: 245000, at_risk: 28000, blocked: 18000, fraud_flagged: 0, total: 291000 },
  { period: '2026-04', confirmed: 280000, at_risk: 45000, blocked: 22000, fraud_flagged: 12000, total: 359000 },
  { period: '2026-05', confirmed: 295000, at_risk: 52000, blocked: 25000, fraud_flagged: 0, total: 372000 },
  { period: '2026-06', confirmed: 305000, at_risk: 61000, blocked: 31000, fraud_flagged: 15000, total: 412000 },
  { period: '2026-07', confirmed: 312000, at_risk: 84500, blocked: 42300, fraud_flagged: 18000, total: 456800 }
];

export const MOCK_SUPPLIERS = [
  {
    supplier_gstin: '27AABCM9012K1ZX',
    supplier_name: 'Mahavir Logistics & Transport',
    compliance_score: 33.3,
    total_months_tracked: 6,
    months_filed: 2,
    total_invoice_count: 8,
    total_invoice_value: 480000.0,
    average_invoice_value: 60000.0,
    is_flagged: true,
    flag_reason: 'Chronically non-compliant — GSTR-1 filed in only 2 of 6 months',
    last_invoice_date: '2026-08-01'
  },
  {
    supplier_gstin: '27AAACK5566J1Z1',
    supplier_name: 'Kothari Electronics & Spares',
    compliance_score: 40.0,
    total_months_tracked: 5,
    months_filed: 2,
    total_invoice_count: 12,
    total_invoice_value: 310000.0,
    average_invoice_value: 25833.0,
    is_flagged: true,
    flag_reason: 'Compliance rating below threshold (40%)',
    last_invoice_date: '2026-07-28'
  },
  {
    supplier_gstin: '27AAACB1122D1Z4',
    supplier_name: 'Bajaj Raw Materials Pvt Ltd',
    compliance_score: 100.0,
    total_months_tracked: 6,
    months_filed: 6,
    total_invoice_count: 24,
    total_invoice_value: 1250000.0,
    average_invoice_value: 52083.0,
    is_flagged: false,
    flag_reason: null,
    last_invoice_date: '2026-08-02'
  },
  {
    supplier_gstin: '27AAACR4411M1ZB',
    supplier_name: 'Royal Packaging Solutions',
    compliance_score: 83.3,
    total_months_tracked: 6,
    months_filed: 5,
    total_invoice_count: 15,
    total_invoice_value: 620000.0,
    average_invoice_value: 41333.0,
    is_flagged: false,
    flag_reason: null,
    last_invoice_date: '2026-08-02'
  }
];

export const MOCK_INVOICES = [
  {
    id: 'inv-101',
    trader_id: 'trader-1',
    supplier_name: 'Mahavir Logistics & Transport',
    supplier_gstin: '27AABCM9012K1ZX',
    invoice_number: 'INV-904',
    invoice_date: '2026-08-01',
    total_taxable_value: 50000.0,
    cgst: 4500.0,
    sgst: 4500.0,
    igst: 0.0,
    cess: 0.0,
    total_amount: 59000.0,
    place_of_supply: '27',
    reverse_charge: false,
    itc_status: 'FRAUD_FLAGGED',
    itc_blocked_reason: 'Fraud score 78/100 — Sequential invoice anomaly & Benford distribution flag',
    fraud_score: 78,
    extraction_confidence: 0.95,
    source: 'whatsapp',
    period: '2026-08',
    reconciliation_status: 'UNMATCHED'
  },
  {
    id: 'inv-102',
    trader_id: 'trader-1',
    supplier_name: 'Bajaj Raw Materials Pvt Ltd',
    supplier_gstin: '27AAACB1122D1Z4',
    invoice_number: 'BRM-2026-089',
    invoice_date: '2026-08-02',
    total_taxable_value: 120000.0,
    cgst: 10800.0,
    sgst: 10800.0,
    igst: 0.0,
    cess: 0.0,
    total_amount: 141600.0,
    place_of_supply: '27',
    reverse_charge: false,
    itc_status: 'CONFIRMED',
    itc_blocked_reason: null,
    fraud_score: 12,
    extraction_confidence: 0.98,
    source: 'email',
    period: '2026-08',
    reconciliation_status: 'EXACT'
  },
  {
    id: 'inv-103',
    trader_id: 'trader-1',
    supplier_name: 'Royal Packaging Solutions',
    supplier_gstin: '27AAACR4411M1ZB',
    invoice_number: 'INV-2026-441',
    invoice_date: '2026-08-02',
    total_taxable_value: 245000.0,
    cgst: 22050.0,
    sgst: 22050.0,
    igst: 0.0,
    cess: 0.0,
    total_amount: 289100.0,
    place_of_supply: '27',
    reverse_charge: false,
    itc_status: 'AT_RISK',
    itc_blocked_reason: 'Invoice missing in GSTR-2B statement (§16(2)(c))',
    fraud_score: 25,
    extraction_confidence: 0.94,
    source: 'whatsapp',
    period: '2026-08',
    reconciliation_status: 'UNMATCHED'
  },
  {
    id: 'inv-104',
    trader_id: 'trader-1',
    supplier_name: 'Unnati Motors Pvt Ltd',
    supplier_gstin: '27AAACU1122K1Z3',
    invoice_number: 'VH-882',
    invoice_date: '2026-07-29',
    total_taxable_value: 850000.0,
    cgst: 76500.0,
    sgst: 76500.0,
    igst: 0.0,
    cess: 0.0,
    total_amount: 1003000.0,
    place_of_supply: '27',
    reverse_charge: false,
    itc_status: 'INELIGIBLE',
    itc_blocked_reason: 'Blocked credit under GST §17(5)(a) — Motor Vehicles for passenger transport',
    fraud_score: 10,
    extraction_confidence: 0.96,
    source: 'upload',
    period: '2026-07',
    reconciliation_status: 'EXACT'
  }
];

// Helper functions calling real API with graceful mock fallback
export async function fetchTraders() {
  try {
    const res = await apiClient.get('/dashboard/traders');
    return res.data.length ? res.data : MOCK_TRADERS;
  } catch (err) {
    console.warn('Backend offline, using fallback traders:', err);
    return MOCK_TRADERS;
  }
}

export async function fetchSummary(traderId: string) {
  try {
    const res = await apiClient.get(`/dashboard/summary/${traderId}`);
    return res.data;
  } catch (err) {
    console.warn('Backend offline, using fallback summary:', err);
    return MOCK_SUMMARY;
  }
}

export async function fetchActions(traderId: string) {
  try {
    const res = await apiClient.get(`/dashboard/actions/${traderId}`);
    return res.data.actions || res.data;
  } catch (err) {
    console.warn('Backend offline, using fallback actions:', err);
    return MOCK_ACTIONS;
  }
}

export async function resolveAction(actionId: string, note?: string) {
  try {
    const res = await apiClient.patch(`/dashboard/actions/${actionId}/resolve`, { resolution_note: note });
    return res.data;
  } catch (err) {
    console.warn('Backend offline, simulating resolveAction:', err);
    return { status: 'resolved', action_id: actionId };
  }
}

export async function fetchTimeline(traderId: string) {
  try {
    const res = await apiClient.get(`/dashboard/itc-timeline/${traderId}`);
    return res.data;
  } catch (err) {
    console.warn('Backend offline, using fallback timeline:', err);
    return MOCK_TIMELINE;
  }
}

export async function fetchSuppliers(traderId: string) {
  try {
    const res = await apiClient.get(`/dashboard/suppliers/${traderId}`);
    return res.data;
  } catch (err) {
    console.warn('Backend offline, using fallback suppliers:', err);
    return MOCK_SUPPLIERS;
  }
}

export async function fetchInvoices(traderId: string) {
  try {
    const res = await apiClient.get(`/dashboard/invoices/${traderId}`);
    return res.data.invoices || res.data;
  } catch (err) {
    console.warn('Backend offline, using fallback invoices:', err);
    return MOCK_INVOICES;
  }
}

export async function sendVendorWarning(payload: { action_item_id: string; channel: string; vendor_phone?: string; message?: string }) {
  try {
    const res = await apiClient.post('/communications/vendor-warning', payload);
    return res.data;
  } catch (err) {
    console.warn('Backend offline, simulating vendor warning:', err);
    return { status: 'sent', channel: payload.channel, recipient: payload.vendor_phone || 'WhatsApp Vendor' };
  }
}

export async function triggerReconciliation(traderId: string) {
  try {
    const res = await apiClient.post(`/gstr2b/reconcile/${traderId}`);
    return res.data;
  } catch (err) {
    console.warn('Backend offline, simulating 3-pass reconciliation:', err);
    return {
      total_invoices: 12,
      total_gstr2b_records: 11,
      exact_matches: 8,
      fuzzy_matches: 2,
      amount_date_matches: 0,
      unmatched_invoices: 2,
      unmatched_gstr2b: 1,
      action_items_created: 2
    };
  }
}
