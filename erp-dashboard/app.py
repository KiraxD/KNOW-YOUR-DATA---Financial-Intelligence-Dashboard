"""
KNOW YOUR DATA — Financial Intelligence Dashboard - Flask Backend
Fully dynamic AI-powered financial data analysis platform.
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file, session
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dateutil import parser as date_parser

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['EXPORTS_FOLDER'] = 'exports'
app.config['INSIGHTS_FOLDER'] = 'insights'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'xlsx', 'csv'}

# Enable CORS for cross-origin requests from Netlify frontend
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Column Alias Maps (auto-detection)
# ─────────────────────────────────────────────
COLUMN_ALIASES = {
    'amount':      ['amount', 'amount_raw', 'total', 'value', 'expense', 'cost',
                    'price', 'sum', 'debit', 'credit', 'net', 'gross', 'fee',
                    'charges', 'billing', 'invoice_amount', 'txn_amount'],
    'vendor':      ['vendor', 'supplier', 'merchant', 'payee', 'company',
                    'provider', 'seller', 'counterparty', 'party'],
    'description': ['description', 'note', 'notes', 'remarks', 'memo', 'details',
                    'narration', 'particulars', 'reference', 'ref', 'purpose',
                    'transaction_details', 'txn_description'],
    'date':        ['date', 'txn_date', 'transaction_date', 'trans_date',
                    'posting_date', 'value_date', 'entry_date', 'created_at',
                    'created_date', 'invoice_date', 'bill_date', 'pay_date'],
    'department':  ['department', 'dept', 'team', 'division', 'unit', 'group',
                    'cost_center', 'business_unit', 'bu', 'section', 'branch'],
    'employee':    ['employee', 'emp', 'staff', 'person', 'user', 'submitter',
                    'requestor', 'name', 'employee_name', 'emp_name'],
    'category':    ['category', 'cat', 'type', 'expense_type', 'trans_type',
                    'transaction_type', 'classification', 'class'],
}

# ─────────────────────────────────────────────
# AI Classification Rules
# ─────────────────────────────────────────────
CLASSIFICATION_RULES = [
    {
        'category': 'Cloud Infrastructure',
        'keywords': ['aws', 'amazon web services', 'azure', 'gcp', 'google cloud',
                     'ec2', 's3', 'lambda', 'cloudfront', 'rds', 'cloud hosting',
                     'digital ocean', 'linode', 'vultr', 'heroku', 'cloud storage'],
        'weight': 1.0
    },
    {
        'category': 'SaaS Subscriptions',
        'keywords': ['slack', 'notion', 'jira', 'confluence', 'github', 'gitlab',
                     'figma', 'zoom', 'salesforce', 'hubspot', 'zendesk', 'datadog',
                     'pagerduty', 'newrelic', 'sentry', 'subscription', 'license',
                     'saas', 'software', 'platform fee', 'monthly plan', 'annual plan',
                     'asana', 'monday', 'trello', 'clickup', 'linear', 'dropbox',
                     'google workspace', 'microsoft 365', 'office 365', 'adobe'],
        'weight': 1.0
    },
    {
        'category': 'Travel & Transport',
        'keywords': ['flight', 'airline', 'hotel', 'uber', 'ola', 'taxi', 'cab',
                     'train', 'railway', 'irctc', 'bus', 'travel', 'transport',
                     'boarding', 'lodging', 'accommodation', 'airbnb', 'booking.com',
                     'makemytrip', 'goibibo', 'cleartrip', 'visa', 'passport',
                     'airport', 'parking', 'toll', 'fuel', 'petrol', 'diesel'],
        'weight': 1.0
    },
    {
        'category': 'Meals & Catering',
        'keywords': ['food', 'meal', 'lunch', 'dinner', 'breakfast', 'catering',
                     'restaurant', 'cafe', 'coffee', 'snack', 'beverage', 'zomato',
                     'swiggy', 'uber eats', 'starbucks', 'canteen', 'team lunch',
                     'client dinner', 'hospitality', 'refreshment'],
        'weight': 1.0
    },
    {
        'category': 'Finance & Banking',
        'keywords': ['bank', 'finance', 'interest', 'loan', 'emi', 'insurance',
                     'premium', 'investment', 'dividend', 'tax', 'gst', 'vat',
                     'audit', 'accounting', 'payroll', 'salary', 'reimbursement',
                     'wire transfer', 'forex', 'currency', 'payment gateway',
                     'stripe', 'paypal', 'razorpay', 'clearance fee'],
        'weight': 1.0
    },
    {
        'category': 'Hardware & Equipment',
        'keywords': ['laptop', 'computer', 'server', 'hardware', 'equipment',
                     'device', 'printer', 'monitor', 'keyboard', 'mouse', 'cable',
                     'router', 'switch', 'storage', 'hard disk', 'ssd', 'ram',
                     'cpu', 'gpu', 'headphone', 'phone', 'tablet', 'ipad',
                     'purchase', 'procurement', 'asset'],
        'weight': 1.0
    },
    {
        'category': 'Personal Expense',
        'keywords': ['personal', 'grocery', 'supermarket', 'shopping', 'amazon',
                     'flipkart', 'myntra', 'clothing', 'apparel', 'shoes',
                     'pharmacy', 'medicine', 'medical', 'gym', 'fitness',
                     'entertainment', 'netflix', 'spotify', 'amazon prime',
                     'home', 'household', 'electric bill', 'water bill',
                     'rent', 'mortgage', 'dtc', 'personal care'],
        'weight': 0.9
    },
]

# ─────────────────────────────────────────────
# Vendor Normalization Map
# ─────────────────────────────────────────────
VENDOR_NORMALIZATIONS = {
    r'amazon[\s\-_]?web[\s\-_]?services?|aws': 'Amazon Web Services',
    r'google[\s\-_]?cloud|gcp': 'Google Cloud Platform',
    r'microsoft[\s\-_]?azure|azure': 'Microsoft Azure',
    r'digital[\s\-_]?ocean': 'DigitalOcean',
    r'github[\s\-_]?inc?': 'GitHub',
    r'slack[\s\-_]?tech': 'Slack',
    r'zoom[\s\-_]?video': 'Zoom',
    r'atlassian|jira|confluence': 'Atlassian',
    r'salesforce[\s\-_]?inc?': 'Salesforce',
    r'uber[\s\-_]?tech': 'Uber',
    r'zomato[\s\-_]?ltd': 'Zomato',
    r'swiggy[\s\-_]?inc?': 'Swiggy',
}

# ─────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_column(df, field):
    """Detect column name by matching against known aliases (case-insensitive)."""
    aliases = COLUMN_ALIASES.get(field, [])
    cols_lower = {c.lower().strip().replace(' ', '_'): c for c in df.columns}
    for alias in aliases:
        if alias in cols_lower:
            return cols_lower[alias]
    # Fuzzy partial match fallback
    for alias in aliases:
        for col_key, col_orig in cols_lower.items():
            if alias in col_key or col_key in alias:
                return col_orig
    return None


def clean_amount(val):
    """Extract numeric value from messy amount strings."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    # Remove known non-numeric strings
    if re.match(r'^(tbd|n\/a|na|nil|none|-)$', val_str, re.IGNORECASE):
        return None
    # Remove currency symbols and codes
    val_str = re.sub(r'[₹$€£¥₩₺₴฿₫₪₦₲₵₡₢₣₤₥₨₭₮₯₰₱₳₴₵₶₷₸₹₺₻₼₽₾]', '', val_str)
    val_str = re.sub(r'\b(USD|INR|AED|EUR|GBP|JPY|CAD|AUD|CHF|CNY|SGD|HKD|NOK|SEK|DKK|THB|MYR|IDR|PHP|KRW)\b',
                     '', val_str, flags=re.IGNORECASE)
    # Remove commas and whitespace
    val_str = val_str.replace(',', '').strip()
    # Extract numeric
    match = re.search(r'-?\d+(\.\d+)?', val_str)
    if match:
        return float(match.group())
    return None


def detect_currency(val):
    """Detect currency symbol or code from a value string."""
    if pd.isna(val):
        return 'Unknown'
    val_str = str(val).strip()
    currency_map = {
        '₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY',
        'USD': 'USD', 'INR': 'INR', 'AED': 'AED', 'EUR': 'EUR',
        'GBP': 'GBP', 'JPY': 'JPY', 'CAD': 'CAD', 'AUD': 'AUD',
    }
    for sym, code in currency_map.items():
        if sym in val_str:
            return code
    return 'Unknown'


def standardize_date(val):
    """Normalize dates to YYYY-MM-DD format."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('nan', 'none', 'nat', 'n/a', ''):
        return None
    # Handle Unix timestamps (numeric)
    if re.match(r'^\d{9,13}$', val_str):
        ts = int(val_str)
        if ts > 1e10:  # milliseconds
            ts //= 1000
        try:
            return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        except Exception:
            return None
    # Try dateutil parser
    try:
        parsed = date_parser.parse(val_str, dayfirst=False)
        return parsed.strftime('%Y-%m-%d')
    except Exception:
        pass
    # Try common formats manually
    formats = [
        '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
        '%d.%m.%Y', '%Y/%m/%d', '%d %b %Y', '%b %d, %Y',
        '%d %B %Y', '%B %d, %Y', '%d-%b-%Y', '%d %b, %Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).strftime('%Y-%m-%d')
        except Exception:
            continue
    return None


def normalize_vendor(name):
    """Apply vendor normalization rules."""
    if pd.isna(name) or not str(name).strip():
        return name
    name_clean = str(name).strip()
    name_lower = name_clean.lower()
    for pattern, normalized in VENDOR_NORMALIZATIONS.items():
        if re.search(pattern, name_lower, re.IGNORECASE):
            return normalized
    # Basic title-casing
    return name_clean.title()


def classify_transaction(vendor, description, category_hint=None):
    """Keyword-based AI classification. Returns (category, confidence, reasoning)."""
    text = ' '.join(filter(None, [
        str(vendor) if pd.notna(vendor) else '',
        str(description) if pd.notna(description) else '',
        str(category_hint) if pd.notna(category_hint) else '',
    ])).lower()

    if not text.strip():
        return 'Miscellaneous', 0.3, 'No text available for classification'

    scores = {}
    for rule in CLASSIFICATION_RULES:
        matched = [kw for kw in rule['keywords'] if kw in text]
        if matched:
            raw_score = min(
                1.0, (len(matched) / max(len(rule['keywords']) * 0.3, 1)) * rule['weight'])
            score = round(min(raw_score + 0.4, 0.99), 2)
            scores[rule['category']] = (score, matched)

    if not scores:
        return 'Miscellaneous', 0.35, 'No matching keywords found'

    best_cat = max(scores, key=lambda c: scores[c][0])
    best_score, matched_kws = scores[best_cat]
    reasoning = f"Matched keywords: {', '.join(matched_kws[:3])}"
    return best_cat, best_score, reasoning


def assess_risk(row, amount_col, vendor_col, desc_col, date_col, is_duplicate):
    """Assign risk severity and flags to a transaction row."""
    flags = []
    severity = 'INFO'

    amount = row.get('_clean_amount')
    vendor = row.get(vendor_col) if vendor_col else None
    desc = row.get(desc_col) if desc_col else None
    category = row.get('_category', '')

    # Missing fields
    if pd.isna(vendor) or str(vendor).strip() == '':
        flags.append('Missing Vendor')
        severity = max_severity(severity, 'WARNING')
    if amount is None or pd.isna(amount):
        flags.append('Invalid Amount')
        severity = max_severity(severity, 'WARNING')
    if date_col and (pd.isna(row.get('_clean_date')) or not row.get('_clean_date')):
        flags.append('Missing Date')
        severity = max_severity(severity, 'WARNING')

    # Duplicate
    if is_duplicate:
        flags.append('Duplicate Transaction')
        severity = max_severity(severity, 'CRITICAL')

    # Personal expense
    if category == 'Personal Expense':
        flags.append('Personal Expense')
        severity = max_severity(severity, 'WARNING')

    # Suspicious description
    if desc and re.search(r'\b(personal|cash|misc|na|test|dummy|unknown)\b', str(desc), re.IGNORECASE):
        flags.append('Suspicious Description')
        severity = max_severity(severity, 'WARNING')

    # Very large amount
    if amount and amount > 500000:
        flags.append('High Value Transaction')
        severity = max_severity(severity, 'WARNING')

    # Low confidence
    if row.get('_confidence', 1.0) < 0.5:
        flags.append('Low AI Confidence')

    return severity, flags


def max_severity(current, new):
    order = {'INFO': 0, 'WARNING': 1, 'CRITICAL': 2}
    return new if order.get(new, 0) > order.get(current, 0) else current


def detect_duplicates(df, vendor_col, amount_col, date_col):
    """Return set of indices that are duplicates."""
    dup_indices = set()
    subset_cols = []
    if vendor_col and vendor_col in df.columns:
        subset_cols.append(vendor_col)
    if '_clean_amount' in df.columns:
        subset_cols.append('_clean_amount')
    if '_clean_date' in df.columns:
        subset_cols.append('_clean_date')
    if len(subset_cols) >= 2:
        dup_mask = df.duplicated(subset=subset_cols, keep='first')
        dup_indices = set(df.index[dup_mask].tolist())
    return dup_indices


def generate_insights(df, kpis, col_map):
    """Generate dynamic business insights from the processed dataset."""
    insights = []
    total = kpis['total_transactions']
    if total == 0:
        return [{'type': 'INFO', 'message': 'No transactions found in the uploaded file.'}]

    # Category distribution insights
    if '_category' in df.columns:
        cat_counts = df['_category'].value_counts()
        top_cat = cat_counts.index[0] if len(cat_counts) > 0 else None
        top_pct = round(cat_counts.iloc[0] / total * 100, 1) if top_cat else 0
        if top_cat:
            insights.append({'type': 'INFO',
                             'message': f"{top_pct}% of transactions are classified as '{top_cat}'."})

        saas_cloud = cat_counts.get(
            'SaaS Subscriptions', 0) + cat_counts.get('Cloud Infrastructure', 0)
        if saas_cloud > 0:
            pct = round(saas_cloud / total * 100, 1)
            insights.append({'type': 'INFO',
                             'message': f"{pct}% of transactions are SaaS/Cloud related — indicating high technology dependency."})

        personal = cat_counts.get('Personal Expense', 0)
        if personal > 0:
            pct = round(personal / total * 100, 1)
            insights.append({'type': 'WARNING',
                             'message': f"{personal} potential personal expenses detected ({pct}% of total). Review required."})

    # Duplicate insights
    dup_exp = kpis.get('duplicate_exposure', 0)
    if dup_exp > 0:
        insights.append({'type': 'CRITICAL',
                         'message': f"Duplicate transaction exposure: {format_amount(dup_exp)}. Immediate review recommended."})

    # Missing data
    missing_vendors = kpis.get('missing_vendors', 0)
    if missing_vendors > 0:
        insights.append({'type': 'WARNING',
                         'message': f"{missing_vendors} transactions have missing vendor information — data quality issue."})

    invalid_amounts = kpis.get('invalid_amounts', 0)
    if invalid_amounts > 0:
        insights.append({'type': 'WARNING',
                         'message': f"{invalid_amounts} rows contain invalid or unrecognizable amount values."})

    # Vendor concentration
    vendor_col = col_map.get('vendor')
    if vendor_col and vendor_col in df.columns and '_clean_amount' in df.columns:
        vendor_spend = df.groupby(vendor_col)['_clean_amount'].sum(
        ).dropna().sort_values(ascending=False)
        if len(vendor_spend) > 0:
            top_vendor = vendor_spend.index[0]
            top_pct = round(
                vendor_spend.iloc[0] / vendor_spend.sum() * 100, 1) if vendor_spend.sum() > 0 else 0
            if top_pct > 40:
                insights.append({'type': 'WARNING',
                                 'message': f"High vendor concentration: '{top_vendor}' accounts for {top_pct}% of total spend."})

    # AI confidence insight
    if '_confidence' in df.columns:
        avg_conf = df['_confidence'].mean()
        low_conf_count = (df['_confidence'] < 0.5).sum()
        if avg_conf < 0.6:
            insights.append({'type': 'WARNING',
                             'message': f"Average AI classification confidence is {round(avg_conf*100,1)}%. Weak description quality may be reducing accuracy."})
        if low_conf_count > 0:
            insights.append({'type': 'INFO',
                             'message': f"{low_conf_count} transactions have low AI confidence (<50%) and may be misclassified."})

    # Department insights
    dept_col = col_map.get('department')
    if dept_col and dept_col in df.columns and '_clean_amount' in df.columns:
        dept_spend = df.groupby(dept_col)['_clean_amount'].sum(
        ).dropna().sort_values(ascending=False)
        if len(dept_spend) > 1:
            top_dept = dept_spend.index[0]
            top_dept_pct = round(
                dept_spend.iloc[0] / dept_spend.sum() * 100, 1) if dept_spend.sum() > 0 else 0
            insights.append({'type': 'INFO',
                             'message': f"Highest spending department: '{top_dept}' ({top_dept_pct}% of departmental spend)."})

    # Critical issues
    critical_count = kpis.get('critical_count', 0)
    if critical_count > 0:
        insights.append({'type': 'CRITICAL',
                         'message': f"{critical_count} CRITICAL issues flagged — duplicate or high-risk transactions require immediate attention."})

    if not insights:
        insights.append(
            {'type': 'INFO', 'message': 'Dataset processed successfully. No major anomalies detected.'})

    return insights


def format_amount(val):
    """Format a numeric amount to readable string."""
    try:
        v = float(val)
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"{v:,.0f}"
        return f"{v:.2f}"
    except Exception:
        return str(val)


# ─────────────────────────────────────────────
# Core Processing Pipeline
# ─────────────────────────────────────────────
def process_dataset(filepath):
    """
    Main pipeline: load → detect columns → clean → classify → risk → insights.
    Returns a dict with all dashboard data.
    """
    ext = filepath.rsplit('.', 1)[-1].lower()

    # 1. Load file
    if ext == 'csv':
        try:
            df = pd.read_csv(filepath, encoding='utf-8', dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='latin-1', dtype=str)
    else:
        df = pd.read_excel(filepath, dtype=str)

    df.columns = [str(c).strip() for c in df.columns]
    original_count = len(df)

    if df.empty:
        raise ValueError("Uploaded file is empty.")

    # 2. Detect columns
    col_map = {}
    for field in COLUMN_ALIASES:
        detected = detect_column(df, field)
        if detected:
            col_map[field] = detected

    amount_col = col_map.get('amount')
    vendor_col = col_map.get('vendor')
    desc_col = col_map.get('description')
    date_col = col_map.get('date')
    dept_col = col_map.get('department')
    emp_col = col_map.get('employee')
    cat_hint_col = col_map.get('category')

    logger.info(f"Detected columns: {col_map}")

    # 3. Detect currencies (before cleaning)
    currencies = {}
    if amount_col:
        for val in df[amount_col].dropna().unique()[:100]:
            c = detect_currency(val)
            currencies[c] = currencies.get(c, 0) + 1
    dominant_currency = max(
        currencies, key=currencies.get) if currencies else 'Unknown'

    # 4. Clean amounts
    if amount_col:
        df['_clean_amount'] = df[amount_col].apply(clean_amount)
    else:
        # Try to find any numeric-looking column
        for col in df.columns:
            sample = df[col].dropna().head(20)
            numeric_count = sum(1 for v in sample if re.search(r'\d', str(v)))
            if numeric_count > len(sample) * 0.5:
                df['_clean_amount'] = df[col].apply(clean_amount)
                amount_col = col
                col_map['amount'] = col
                break
        else:
            df['_clean_amount'] = None

    # 5. Clean dates
    if date_col:
        df['_clean_date'] = df[date_col].apply(standardize_date)
    else:
        df['_clean_date'] = None

    # 6. Normalize vendors
    if vendor_col:
        df['_norm_vendor'] = df[vendor_col].apply(normalize_vendor)
    else:
        df['_norm_vendor'] = None

    # 7. Detect duplicates
    dup_indices = detect_duplicates(df, vendor_col, amount_col, date_col)

    # 8. Classify each transaction
    categories = []
    confidences = []
    reasonings = []
    for _, row in df.iterrows():
        vendor = row.get(vendor_col) if vendor_col else None
        desc = row.get(desc_col) if desc_col else None
        cat_hint = row.get(cat_hint_col) if cat_hint_col else None
        cat, conf, reason = classify_transaction(vendor, desc, cat_hint)
        categories.append(cat)
        confidences.append(conf)
        reasonings.append(reason)

    df['_category'] = categories
    df['_confidence'] = confidences
    df['_reasoning'] = reasonings

    # 9. Risk assessment
    severities = []
    flags_list = []
    for idx, row in df.iterrows():
        is_dup = idx in dup_indices
        sev, flags = assess_risk(
            row, amount_col, vendor_col, desc_col, date_col, is_dup)
        severities.append(sev)
        flags_list.append(flags)

    df['_severity'] = severities
    df['_flags'] = ['; '.join(f) if f else '' for f in flags_list]

    # ─── KPI Calculations ───
    total = len(df)
    invalid_amounts = int(df['_clean_amount'].isna(
    ).sum()) if '_clean_amount' in df.columns else 0
    missing_vendors = int(df[vendor_col].isna().sum() | (
        df[vendor_col] == '').sum()) if vendor_col else 0
    duplicate_count = len(dup_indices)
    dup_exposure = float(df.loc[list(dup_indices), '_clean_amount'].sum(
    )) if dup_indices and '_clean_amount' in df.columns else 0.0

    personal_mask = df['_category'] == 'Personal Expense'
    personal_exposure = float(df.loc[personal_mask, '_clean_amount'].sum(
    )) if '_clean_amount' in df.columns else 0.0

    saas_cloud_mask = df['_category'].isin(
        ['SaaS Subscriptions', 'Cloud Infrastructure'])
    saas_spend = float(df.loc[saas_cloud_mask, '_clean_amount'].sum(
    )) if '_clean_amount' in df.columns else 0.0

    critical_count = int((df['_severity'] == 'CRITICAL').sum())
    warning_count = int((df['_severity'] == 'WARNING').sum())
    flagged_rows = int((df['_flags'] != '').sum())
    cleaned_records = total - invalid_amounts

    total_spend = float(df['_clean_amount'].dropna().sum()
                        ) if '_clean_amount' in df.columns else 0.0

    kpis = {
        'total_transactions': total,
        'cleaned_records': cleaned_records,
        'duplicate_exposure': round(dup_exposure, 2),
        'duplicate_count': duplicate_count,
        'personal_exposure': round(personal_exposure, 2),
        'saas_spend': round(saas_spend, 2),
        'critical_count': critical_count,
        'warning_count': warning_count,
        'flagged_rows': flagged_rows,
        'invalid_amounts': invalid_amounts,
        'missing_vendors': missing_vendors,
        'total_spend': round(total_spend, 2),
        'currency': dominant_currency,
        'detected_columns': col_map,
        'original_count': original_count,
    }

    # ─── Chart Data ───
    # Category distribution
    cat_dist = df['_category'].value_counts().to_dict()

    # Risk severity
    sev_dist = df['_severity'].value_counts().to_dict()

    # Department spend
    dept_spend = {}
    if dept_col and dept_col in df.columns and '_clean_amount' in df.columns:
        dept_spend = (df.groupby(dept_col)['_clean_amount']
                      .sum().dropna()
                      .sort_values(ascending=False)
                      .head(10)
                      .round(2).to_dict())

    # Confidence buckets
    conf_buckets = {'Very High (>90%)': 0, 'High (70-90%)': 0,
                    'Medium (50-70%)': 0, 'Low (<50%)': 0}
    for c in df['_confidence']:
        if c >= 0.9:
            conf_buckets['Very High (>90%)'] += 1
        elif c >= 0.7:
            conf_buckets['High (70-90%)'] += 1
        elif c >= 0.5:
            conf_buckets['Medium (50-70%)'] += 1
        else:
            conf_buckets['Low (<50%)'] += 1

    # Vendor spend concentration (top 10)
    vendor_spend_data = {}
    if vendor_col and vendor_col in df.columns and '_clean_amount' in df.columns:
        vendor_spend_data = (df.groupby(vendor_col)['_clean_amount']
                               .sum().dropna()
                               .sort_values(ascending=False)
                               .head(10)
                               .round(2).to_dict())

    # Duplicate analysis (top duplicate pairs)
    dup_analysis = {}
    if dup_indices and '_clean_amount' in df.columns:
        dup_df = df.loc[list(dup_indices)]
        if vendor_col and vendor_col in dup_df.columns:
            dup_analysis = (dup_df.groupby(vendor_col)['_clean_amount']
                            .sum().dropna()
                            .sort_values(ascending=False)
                            .head(8)
                            .round(2).to_dict())

    chart_data = {
        'category_distribution': cat_dist,
        'risk_severity': sev_dist,
        'department_spend': dept_spend,
        'confidence_distribution': conf_buckets,
        'vendor_spend': vendor_spend_data,
        'duplicate_analysis': dup_analysis,
    }

    # ─── Transaction Rows for Table ───
    rows = []
    for idx, row in df.iterrows():
        rows.append({
            'vendor': str(row.get(vendor_col, '') or row.get('_norm_vendor', '') or '—') if vendor_col else '—',
            'category': row['_category'],
            'amount': row['_clean_amount'] if pd.notna(row.get('_clean_amount')) else None,
            'amount_raw': str(row.get(amount_col, '')) if amount_col else '',
            'department': str(row.get(dept_col, '') or '') if dept_col else '',
            'date': row.get('_clean_date') or '',
            'description': str(row.get(desc_col, '') or '') if desc_col else '',
            'confidence': round(float(row['_confidence']), 2),
            'severity': row['_severity'],
            'flags': row['_flags'],
            'reasoning': row['_reasoning'],
            'is_duplicate': idx in dup_indices,
        })

    # ─── AI Insights ───
    insights = generate_insights(df, kpis, col_map)

    # ─── Save cleaned export ───
    export_id = str(uuid.uuid4())[:8]
    export_cols = [c for c in df.columns if not c.startswith('_')]
    export_df = df[export_cols].copy()

    # Add cleaned columns
    if '_clean_amount' in df.columns:
        export_df['cleaned_amount'] = df['_clean_amount']
    if '_clean_date' in df.columns:
        export_df['standardized_date'] = df['_clean_date']
    if '_norm_vendor' in df.columns:
        export_df['normalized_vendor'] = df['_norm_vendor']
    export_df['ai_category'] = df['_category']
    export_df['confidence_score'] = df['_confidence']
    export_df['risk_severity'] = df['_severity']
    export_df['flags'] = df['_flags']

    csv_path = os.path.join(
        app.config['EXPORTS_FOLDER'], f'cleaned_{export_id}.csv')
    xlsx_path = os.path.join(
        app.config['EXPORTS_FOLDER'], f'cleaned_{export_id}.xlsx')
    export_df.to_csv(csv_path, index=False)
    export_df.to_excel(xlsx_path, index=False, engine='xlsxwriter')

    # ─── JSON Report ───
    report = {
        'generated_at': datetime.now().isoformat(),
        'export_id': export_id,
        'kpis': kpis,
        'insights': insights,
        'chart_data': chart_data,
        'total_rows': total,
    }
    report_path = os.path.join(
        app.config['INSIGHTS_FOLDER'], f'report_{export_id}.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    return {
        'kpis': kpis,
        'insights': insights,
        'chart_data': chart_data,
        'transactions': rows,
        'export_id': export_id,
        'csv_path': csv_path,
        'xlsx_path': xlsx_path,
        'report_path': report_path,
    }


# ─────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────
_session_data = {}  # In-memory store for dashboard data (keyed by session_id)


@app.route('/')
def index():
    """Serve the main dashboard HTML."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and trigger processing pipeline."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .xlsx and .csv files are supported'}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    try:
        result = process_dataset(upload_path)
        # Store in memory with a session key
        sid = str(uuid.uuid4())
        _session_data[sid] = result
        return jsonify({'success': True, 'session_id': sid,
                        'filename': filename, 'rows': result['kpis']['total_transactions']})
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard-data')
def dashboard_data():
    """Return all dashboard data for a given session."""
    sid = request.args.get('session_id')
    if not sid or sid not in _session_data:
        return jsonify({'error': 'Session not found. Please upload a file first.'}), 404

    data = _session_data[sid]

    # Sanitize for JSON serialization
    def sanitize(obj):
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        return obj

    def deep_sanitize(obj):
        if isinstance(obj, dict):
            return {k: deep_sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [deep_sanitize(i) for i in obj]
        return sanitize(obj)

    return jsonify(deep_sanitize({
        'kpis': data['kpis'],
        'insights': data['insights'],
        'chart_data': data['chart_data'],
        'transactions': data['transactions'],
        'export_id': data['export_id'],
    }))


@app.route('/download-cleaned')
def download_cleaned():
    """Download the cleaned file (CSV or XLSX)."""
    export_id = request.args.get('export_id')
    fmt = request.args.get('format', 'csv')
    if not export_id:
        return jsonify({'error': 'Missing export_id'}), 400

    if fmt == 'xlsx':
        path = os.path.join(
            app.config['EXPORTS_FOLDER'], f'cleaned_{export_id}.xlsx')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        path = os.path.join(
            app.config['EXPORTS_FOLDER'], f'cleaned_{export_id}.csv')
        mimetype = 'text/csv'

    if not os.path.exists(path):
        return jsonify({'error': 'Export file not found'}), 404

    return send_file(path, mimetype=mimetype, as_attachment=True,
                     download_name=f'cleaned_export_{export_id}.{fmt}')


@app.route('/download-report')
def download_report():
    """Download the full JSON insights report."""
    export_id = request.args.get('export_id')
    fmt = request.args.get('format', 'json')
    if not export_id:
        return jsonify({'error': 'Missing export_id'}), 400

    report_path = os.path.join(
        app.config['INSIGHTS_FOLDER'], f'report_{export_id}.json')
    if not os.path.exists(report_path):
        return jsonify({'error': 'Report not found'}), 404

    return send_file(report_path, mimetype='application/json', as_attachment=True,
                     download_name=f'audit_report_{export_id}.json')


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == '__main__':
    for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER'],
                   app.config['EXPORTS_FOLDER'], app.config['INSIGHTS_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    # Local development
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
else:
    # Production (gunicorn)
    for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER'],
                   app.config['EXPORTS_FOLDER'], app.config['INSIGHTS_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
