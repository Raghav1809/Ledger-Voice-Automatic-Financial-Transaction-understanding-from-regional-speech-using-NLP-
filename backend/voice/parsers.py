import re
import os
import json
import calendar
from datetime import datetime, timedelta, date
from django.utils import timezone


# ---------------------------------------------------------------------------
# Sales Item Parser
# ---------------------------------------------------------------------------

# Common unit aliases → canonical unit string
UNIT_MAP = {
    'kg': 'kg', 'kgs': 'kg', 'kilo': 'kg', 'kilos': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'g': 'g', 'gm': 'g', 'gms': 'g', 'gram': 'g', 'grams': 'g',
    'l': 'litre', 'ltr': 'litre', 'liter': 'litre', 'liters': 'litre', 'litre': 'litre', 'litres': 'litre',
    'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml', 'milliliters': 'ml', 'millilitres': 'ml',
    'piece': 'pcs', 'pieces': 'pcs', 'pcs': 'pcs', 'pc': 'pcs', 'unit': 'pcs', 'units': 'pcs',
    'dozen': 'dozen', 'doz': 'dozen', 'dozens': 'dozen',
    'box': 'box', 'boxes': 'box', 'packet': 'packet', 'packets': 'packet',
    'bag': 'bag', 'bags': 'bag', 'bundle': 'bundle', 'bundles': 'bundle',
    'meter': 'mtr', 'meters': 'mtr', 'metre': 'mtr', 'metres': 'mtr', 'mtr': 'mtr', 'ft': 'ft', 'feet': 'ft',
}

UNIT_PATTERN = '|'.join(sorted(UNIT_MAP.keys(), key=len, reverse=True))

WORD_TO_NUM = {
    'one': 1.0, 'two': 2.0, 'three': 3.0, 'four': 4.0, 'five': 5.0,
    'six': 6.0, 'seven': 7.0, 'eight': 8.0, 'nine': 9.0, 'ten': 10.0,
    'half': 0.5, 'quarter': 0.25
}

QTY_EXPR = (
    r'(?:\d+\s+and\s+(?:a\s+)?half|'
    r'(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+(?:a\s+)?half|'
    r'\d+/\d+|'
    r'\d+(?:\.\d+)?|'
    r'one|two|three|four|five|six|seven|eight|nine|ten|half|quarter)'
)


def parse_quantity_val(qty_str):
    """Convert numeric, fraction (1/2), or spoken quantity string ('one and half', 'half') to float."""
    if not qty_str:
        return 1.0
    qty_str = qty_str.strip().lower()

    # Compound spoken phrases: "one and half", "one and a half", "1 and half", "2 and a half", etc.
    m_compound = re.match(r'^(?P<whole>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+(?:a\s+)?half$', qty_str)
    if m_compound:
        w = m_compound.group('whole')
        whole_val = float(w) if w.isdigit() else WORD_TO_NUM.get(w, 1.0)
        return whole_val + 0.5

    m_compound_q = re.match(r'^(?P<whole>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+(?:a\s+)?quarter$', qty_str)
    if m_compound_q:
        w = m_compound_q.group('whole')
        whole_val = float(w) if w.isdigit() else WORD_TO_NUM.get(w, 1.0)
        return whole_val + 0.25

    # Fractions: 1/2, 1/4, 3/4, 2/3, etc.
    if '/' in qty_str:
        try:
            num, den = qty_str.split('/')
            return round(float(num) / float(den), 4)
        except (ValueError, ZeroDivisionError):
            pass

    # Spoken single words: "half", "quarter", "one", "two", etc.
    if qty_str in WORD_TO_NUM:
        return WORD_TO_NUM[qty_str]

    # Standard floats / ints
    try:
        return float(qty_str)
    except ValueError:
        return 1.0


# Sales trigger keywords
SALES_KEYWORDS = [
    'sold', 'sell', 'sale', 'sales', 'selling', 'kg for', 'litre for', 'liter for',
    'pieces for', 'pcs for', 'gram for', 'gm for', 'per kg', 'per ltr', 'for rupees',
    'items list', 'item list', 'items', 'order list', 'bill',
]

# Prefix phrases that signal a multi-item sales transcript.
SALES_PREFIX_PATTERNS = re.compile(
    r'^\s*(?:items\s+list|item\s+list|order\s+list|bill\s+list|list\s+of\s+items?)\s*[:\-,]?\s*',
    re.IGNORECASE,
)


def strip_sales_prefix(text):
    """Remove leading trigger phrases like 'items list' so item parsing starts clean."""
    return SALES_PREFIX_PATTERNS.sub('', text).strip()


def is_sales_transcript(text):
    """Returns True if the transcript looks like an item/sales transaction."""
    lower = text.lower()
    # Check explicit sales keywords
    if any(k in lower for k in SALES_KEYWORDS):
        return True
    # Check unit pattern presence — strong sign of item-based input
    if re.search(r'\d+\s*(?:' + UNIT_PATTERN + r')\b', lower, re.IGNORECASE):
        return True
    return False


def parse_single_item_segment(segment):
    """
    Parse one item segment like:
      "Sold 1/2 kilograms of sugar for ₹100"
      "Sold one and a half kilograms of sugar for ₹100"
      "Sugar 20kg 100" / "5kg wheat 50" / "rice 2.5 kg for 40"
    Returns dict {name, qty, unit, price, total} or None.
    """
    segment = segment.strip().rstrip('.')
    if not segment:
        return None

    # Strip leading trigger/action verbs from segment
    segment = re.sub(r'^(?:sold|sell|sale|buying|bought|buy)\s+', '', segment, flags=re.IGNORECASE).strip()

    # Pattern A: QTY + UNIT + optional("of") + NAME + PRICE
    # e.g., "1/2 kilograms of sugar for ₹100", "one and a half kg sugar for 100", "500 grams of sugar for 40"
    pat_a = re.compile(
        r'^(?P<qty>' + QTY_EXPR + r')\s*(?P<unit>' + UNIT_PATTERN + r')\s+(?:of\s+)?(?P<name>[a-zA-Z][a-zA-Z0-9\s]{0,30}?)\s+(?:for\s+)?(?:rs\.?|rupees?|inr|\u20b9|\$)?\s*(?P<price>\d+(?:\.\d{1,2})?)(?:\s*(?:rs\.?|rupees?|inr|\u20b9|\$))?$',
        re.IGNORECASE
    )

    # Pattern B: NAME + QTY + UNIT + PRICE
    # e.g., "sugar 1/2 kg for 100", "rice 2.5 kg for 40"
    pat_b = re.compile(
        r'^(?P<name>[a-zA-Z][a-zA-Z0-9\s]{0,30}?)\s+(?P<qty>' + QTY_EXPR + r')\s*(?P<unit>' + UNIT_PATTERN + r')\s+(?:for\s+)?(?:rs\.?|rupees?|inr|\u20b9|\$)?\s*(?P<price>\d+(?:\.\d{1,2})?)(?:\s*(?:rs\.?|rupees?|inr|\u20b9|\$))?$',
        re.IGNORECASE
    )

    # Pattern C: NAME + PRICE only (no quantity/unit)
    # e.g., "sugar for 100", "salt 50 rupees"
    pat_c = re.compile(
        r'^(?P<name>[a-zA-Z][a-zA-Z0-9\s]{0,30}?)\s+(?:for\s+)?(?:rs\.?|rupees?|inr|\u20b9|\$)?\s*(?P<price>\d+(?:\.\d{1,2})?)(?:\s*(?:rs\.?|rupees?|inr|\u20b9|\$))?$',
        re.IGNORECASE
    )

    # Pattern D: QTY + UNIT + optional("of") + NAME (NO PRICE)
    # e.g., "2 kg sugar", "500 grams of rice", "one and a half kg wheat"
    pat_d = re.compile(
        r'^(?P<qty>' + QTY_EXPR + r')\s*(?P<unit>' + UNIT_PATTERN + r')\s+(?:of\s+)?(?P<name>[a-zA-Z][a-zA-Z0-9\s]{0,30}?)$',
        re.IGNORECASE
    )

    # Pattern E: NAME + QTY + UNIT (NO PRICE)
    # e.g., "sugar 2 kg", "rice 500 grams"
    pat_e = re.compile(
        r'^(?P<name>[a-zA-Z][a-zA-Z0-9\s]{0,30}?)\s+(?P<qty>' + QTY_EXPR + r')\s*(?P<unit>' + UNIT_PATTERN + r')$',
        re.IGNORECASE
    )

    # has_qty: whether the pattern captures qty; has_price: whether the pattern captures price
    for pat, has_qty, has_price in [
        (pat_a, True, True),
        (pat_b, True, True),
        (pat_c, False, True),
        (pat_d, True, False),
        (pat_e, True, False),
    ]:
        m = pat.match(segment.strip())
        if m:
            g = m.groupdict()
            raw_unit = g.get('unit', '').lower().strip()
            canonical_unit = UNIT_MAP.get(raw_unit, raw_unit) if raw_unit else 'pcs'
            qty = parse_quantity_val(g.get('qty')) if has_qty else 1.0
            total = float(g['price']) if has_price else 0.0
            raw_name = g['name'].strip()
            # Clean leading fillers from item name (e.g. "of", "and")
            clean_name = re.sub(r'^(?:of|and|then|also)\s+', '', raw_name, flags=re.IGNORECASE).strip().title()
            if not clean_name:
                continue
            if has_price and total == 0:
                continue
            unit_price = round(total / qty, 2) if (qty > 0 and total > 0) else total
            return {
                'name': clean_name,
                'qty': qty,
                'unit': canonical_unit,
                'price': unit_price,
                'total': total
            }
    return None


def parse_sales_items_rule_based(transcript):
    """
    Parse one or multiple items from a voice transcript.
    Strips leading sales prefixes/verbs, then splits on commas/semicolons/and-conjunctions.
    Returns list of item dicts, or empty list.
    """
    cleaned = strip_sales_prefix(transcript)
    cleaned = re.sub(r'^(?:sold|sell|sale|buying|bought|buy)\s+', '', cleaned, flags=re.IGNORECASE).strip()

    # Protect quantity phrases containing "and" (e.g. "one and half", "one and a half", "1 and half")
    qty_and_pattern = re.compile(r'\b(?P<num>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+(?:a\s+)?(?P<frac>half|quarter)\b', re.IGNORECASE)
    masked = qty_and_pattern.sub(lambda m: m.group(0).replace(' and ', ' __AND__ ').replace(' AND ', ' __AND__ '), cleaned)

    # Normalize "and" between items: "sugar 5kg 50 and wheat 10kg 80"
    text = re.sub(r'\band\b', ',', masked, flags=re.IGNORECASE)
    text = text.replace('__AND__', 'and')
    segments = re.split(r'[,;]', text)

    items = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        item = parse_single_item_segment(seg)
        if item:
            items.append(item)

    return items


MONTH_MAP = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9, 'sepetember': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12
}


def calculate_due_date(text, today=None):
    """
    Parse a given transcript text for due dates.
    Supports:
    - Specific dates: "1 september", "september 1st", "1st of september", "15th dec"
    - Relative months: "in a month", "in 2 months", "3 month"
    - Relative weeks: "next week", "in a week", "2 weeks"
    - Relative days: "tomorrow", "next day", "in 5 days", "within 3 days"
    """
    if not text:
        return None
    if today is None:
        today = timezone.now().date()
        
    text = text.lower()
    
    # Correct common typos or speech-to-text mistakes in dates/words
    text = re.sub(r'\btomarrow\b', 'tomorrow', text)
    text = re.sub(r'\btommorow\b', 'tomorrow', text)
    text = re.sub(r'\bsepetember\b', 'september', text)
    
    # 1. Specific dates like "1 september", "september 1st", "1st of september"
    month_names_pattern = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    
    # Match "September 1" or "September 1st" or "September the 1st"
    m_d_pattern = re.compile(rf'\b{month_names_pattern}\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?\b', re.IGNORECASE)
    
    # Match "1 September" or "1st September" or "1st of September"
    d_m_pattern = re.compile(rf'\b(\d+)(?:st|nd|rd|th)?\s+(?:of\s+)?{month_names_pattern}\b', re.IGNORECASE)
    
    m_d_match = m_d_pattern.search(text)
    d_m_match = d_m_pattern.search(text)
    
    if m_d_match or d_m_match:
        if m_d_match:
            month_str = m_d_match.group(1)
            day_str = m_d_match.group(2)
        else:
            day_str = d_m_match.group(1)
            month_str = d_m_match.group(2)
            
        month_val = MONTH_MAP.get(month_str.lower())
        day_val = int(day_str)
        
        if month_val and 1 <= day_val <= 31:
            try:
                # Construct date for current year
                target_date = date(year=today.year, month=month_val, day=day_val)
                # If the date has already passed for the current year, set to next year
                if target_date < today:
                    target_date = date(year=today.year + 1, month=month_val, day=day_val)
                return target_date.strftime('%Y-%m-%d')
            except ValueError:
                # Invalid date (e.g. 31st Feb)
                pass

    # 2. Relative months: "in 2 months", "in a month", "2 months", "next month", "3 month"
    # Matches "in X months", "pay in X months", "X months", "X month"
    months_match = re.search(r'\b(?:after|in|within|return in|pay in|next)?\s*(\d+)\s*months?\b', text)
    # Matches "in a month", "return in a month", "pay in a month"
    a_month_match = re.search(r'\b(?:after|in|within|return in|pay in)\s+a\s+month\b', text)
    # Matches "next month"
    next_month_match = re.search(r'\bnext\s+month\b', text)
    
    if months_match:
        months_to_add = int(months_match.group(1))
        month = today.month - 1 + months_to_add
        year = today.year + month // 12
        month = month % 12 + 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime('%Y-%m-%d')
    elif a_month_match or next_month_match:
        months_to_add = 1
        month = today.month - 1 + months_to_add
        year = today.year + month // 12
        month = month % 12 + 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime('%Y-%m-%d')
        
    # 3. Relative weeks: "next week", "in a week", "2 weeks", etc.
    # Matches "in X weeks", "X weeks"
    weeks_match = re.search(r'\b(?:after|in|within|return in|pay in|next)?\s*(\d+)\s*weeks?\b', text)
    # Matches "in a week", "pay in a week"
    a_week_match = re.search(r'\b(?:after|in|within|return in|pay in)\s+a\s+week\b', text)
    # Matches "next week"
    next_week_match = re.search(r'\bnext\s+week\b', text)
    
    if weeks_match:
        weeks_to_add = int(weeks_match.group(1))
        return (today + timedelta(weeks=weeks_to_add)).strftime('%Y-%m-%d')
    elif a_week_match or next_week_match:
        return (today + timedelta(weeks=1)).strftime('%Y-%m-%d')

    # 4. Relative days: "next day", "tomorrow", "in 5 days", etc.
    tomorrow_match = re.search(r'\b(?:tomorrow|tomarrow|tommorow)\b', text)
    next_day_match = re.search(r'\bnext\s+day\b', text)
    a_day_match = re.search(r'\b(?:after|in|within|return in|pay in)\s+a\s+day\b', text)
    days_match = re.search(r'\b(?:after|in|within|return in|pay in|next|on)?\s*(?:the\s*)?(?:next\s*)?(\d+)(?:st|nd|rd|th)?\s*days?\b', text)
    
    if tomorrow_match or next_day_match or a_day_match:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif days_match:
        return (today + timedelta(days=int(days_match.group(1)))).strftime('%Y-%m-%d')
        
    return None


# ---------------------------------------------------------------------------
# Standard (Non-Sales) Rule-Based Parser
# ---------------------------------------------------------------------------

def parse_with_rules(transcript):
    """
    Rule-based fallback parser for English speech transcriptions.
    Extracts: customer_name, amount, transaction_type, due_date, notes, status, date
    """
    text = transcript.strip().lower()

    # Correct common phonetic misrecognitions
    text = re.sub(r'\bgod\b', 'got', text)
    text = re.sub(r'\bgoro\b', 'borrow', text)
    text = re.sub(r'\bboro\b', 'borrow', text)
    text = re.sub(r'\bbot\b', 'bought', text)

    # 1. Extract Amount
    amount = 0.0
    amount_match = re.search(r'(?:rs\.?|rupees|usd|\$)?\s*(\d+(?:\.\d{1,2})?)\s*(?:rs\.?|rupees|usd|\$)?', text)
    if amount_match:
        try:
            amount = float(amount_match.group(1))
        except ValueError:
            amount = 0.0

    # 2. Extract Transaction Type
    transaction_type = 'credit'
    if any(k in text for k in ['paid me', 'paid', 'payment', 'received', 'got back', 'got', 'returned payment', 'returned me', 'returned', 'cleared']):
        transaction_type = 'payment'
    elif any(k in text for k in ['borrowed', 'loaned', 'gave', 'took', 'will pay', 'will give', 'due']):
        transaction_type = 'credit'
    elif any(k in text for k in ['sold', 'sale', 'sales', 'order']):
        transaction_type = 'sales'
    elif any(k in text for k in ['spent', 'expense', 'bought', 'purchase', 'cost']):
        transaction_type = 'expense'

    # 3. Extract Due Date
    today = timezone.now().date()
    due_date = calculate_due_date(text, today)

    # 4. Extract Customer Name
    name = "Unknown Customer"
    name_prefix_match = re.search(r'^([a-zA-Z]+)\s+(?:borrowed|paid|gave|took|bought|sold|has)', text, re.IGNORECASE)
    name_to_from_match = re.search(r'(?:to|from|for|by)\s+([a-zA-Z]+)', text, re.IGNORECASE)
    if name_prefix_match:
        name = name_prefix_match.group(1).capitalize()
    elif name_to_from_match:
        name = name_to_from_match.group(1).capitalize()
    else:
        stop_words = {
            'borrowed', 'paid', 'gave', 'took', 'rupees', 'rs', 'dollars', 'and', 'will',
            'return', 'after', 'days', 'in', 'me', 'to', 'from', 'a', 'the', 'for',
            'spent', 'sold', 'bought'
        }
        tokens = [w for w in re.findall(r'[a-zA-Z]+', transcript) if w.lower() not in stop_words and len(w) > 1]
        if tokens:
            name = tokens[0].capitalize()

    return {
        "customer_name": name,
        "amount": amount,
        "transaction_type": transaction_type,
        "due_date": due_date,
        "notes": text.capitalize(),  # Use corrected text
        "date": today.strftime('%Y-%m-%d'),
        "status": "completed" if transaction_type == "payment" else "pending",
        "parser_used": "rule-based"
    }


# ---------------------------------------------------------------------------
# spaCy NLP Parser
# ---------------------------------------------------------------------------

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


def autocorrect_transcript(text):
    """Correct common phonetic misrecognitions from speech-to-text."""
    corrections = {
        r'\bgod\b': 'got',
        r'\bgoro\b': 'borrow',
        r'\bboro\b': 'borrow',
        r'\bbot\b': 'bought',
        r'\bgave me\b': 'paid me',
    }
    corrected = text
    for pattern, replacement in corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected


def extract_due_date(doc):
    """Extract relative due dates like tomorrow, next week, or in X days."""
    today = timezone.now().date()
    text = doc.text.lower()
    
    # Try custom parsing first
    parsed_date = calculate_due_date(text, today)
    if parsed_date:
        return parsed_date
        
    # Check DATE entities using spaCy as fallback
    for ent in doc.ents:
        if ent.label_ == "DATE":
            ent_text = ent.text.lower()
            parsed_ent_date = calculate_due_date(ent_text, today)
            if parsed_ent_date:
                return parsed_ent_date
                
    return None


def detect_is_sales(doc):
    """Detect if the transcript is a sales/item transaction."""
    text_lower = doc.text.lower()
    # 1. Prefix matches
    if re.search(r'^\s*(?:items\s+list|item\s+list|order\s+list|bill\s+list|list\s+of\s+items?)\b', text_lower):
        return True
    # 2. Verb matches: if the main action is selling
    sales_verbs = {"sell", "sold", "sale"}
    if any(token.lemma_.lower() in sales_verbs for token in doc):
        return True
    # 3. Unit presence with quantity: e.g. "5 kg sugar"
    for token in doc:
        if token.text.lower() in UNIT_MAP:
            # Check if there is a number nearby
            for child in token.head.children:
                if child.pos_ == "NUM":
                    return True
            if token.i > 0 and doc[token.i - 1].pos_ == "NUM":
                return True
    return False


def parse_item_segment_with_spacy(nlp_model, segment):
    """Parse one item segment (e.g. '2kg sugar for 100') using POS and rules."""
    segment = segment.strip()
    if not segment:
        return None
        
    seg_doc = nlp_model(segment)
    
    numbers = []  # list of (token_index, value)
    unit_token = None
    unit_val = None
    
    for token in seg_doc:
        text_lower = token.text.lower()
        if text_lower in UNIT_MAP:
            unit_token = token
            unit_val = UNIT_MAP[text_lower]
        elif token.pos_ == "NUM" or token.like_num:
            try:
                clean_val = token.text.replace(",", "").replace("$", "").replace("₹", "")
                numbers.append((token.i, float(clean_val)))
            except ValueError:
                pass
                
    if not numbers:
        return None
        
    qty = 1.0
    price = 0.0
    qty_token_idx = None
    price_token_idx = None
    
    # If we found a unit, the number closest to it is likely the quantity
    if unit_token is not None:
        min_dist = 999
        closest_num = None
        for idx, val in numbers:
            dist = abs(idx - unit_token.i)
            if dist < min_dist:
                min_dist = dist
                closest_num = (idx, val)
        if closest_num:
            qty = closest_num[1]
            qty_token_idx = closest_num[0]
            
    # Find the price (monetary amount)
    remaining_numbers = [(idx, val) for idx, val in numbers if idx != qty_token_idx]
    
    if remaining_numbers:
        # Prioritize number near currency symbols/words
        price_candidate = None
        for idx, val in remaining_numbers:
            if idx > 0 and seg_doc[idx - 1].text.lower() in {"for", "at", "rs", "rupees", "rupee", "₹", "$"}:
                price_candidate = (idx, val)
                break
        if not price_candidate:
            price_candidate = remaining_numbers[-1]
            
        price = price_candidate[1]
        price_token_idx = price_candidate[0]
    elif len(numbers) == 1:
        # Only one number in the segment, treat as price/total rather than quantity
        price = numbers[0][1]
        price_token_idx = numbers[0][0]
        qty = 1.0
        unit_val = 'pcs'
        
    if price == 0:
        return None
        
    # Noun tokens for the name (exclude numbers, units, connectors)
    name_tokens = []
    ignore_indices = {qty_token_idx, price_token_idx}
    if unit_token:
        ignore_indices.add(unit_token.i)
        
    ignore_words = {"for", "at", "and", "rs", "rupees", "rupee", "inr", "₹", "$", ",", ";"}
    
    for token in seg_doc:
        if token.i in ignore_indices:
            continue
        if token.text.lower() in ignore_words:
            continue
        if token.pos_ in {"PUNCT", "SYM", "SPACE"}:
            continue
        name_tokens.append(token.text)
        
    name = " ".join(name_tokens).strip().title()
    if not name:
        return None
        
    total = price
    unit_price = round(total / qty, 2) if qty > 0 else total
    
    return {
        'name': name,
        'qty': qty,
        'unit': unit_val or 'pcs',
        'price': unit_price,
        'total': total
    }


def parse_with_spacy(transcript):
    """
    Parses English voice transcript using spaCy NLP.
    Returns structured JSON-compatible dictionary.
    """
    nlp_model = get_nlp()
    corrected_text = autocorrect_transcript(transcript)
    doc = nlp_model(corrected_text)
    
    is_sales = detect_is_sales(doc)
    today_str = timezone.now().date().strftime('%Y-%m-%d')
    
    if is_sales:
        items = parse_sales_items_rule_based(corrected_text)
                
        if items:
            total_amount = round(sum(item['total'] for item in items), 2)
            return {
                "is_sales": True,
                "customer_name": None,
                "amount": total_amount,
                "transaction_type": "sales",
                "due_date": None,
                "notes": corrected_text,
                "date": today_str,
                "status": "completed",
                "items": items,
                "parser_used": "spacy-nlp"
            }
            
    # Extract standard fields
    customer_name = None
    # 1. PERSON Entity
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            customer_name = ent.text.strip().title()
            break
            
    # 2. Prepositional phrase fallback (e.g. "to Rahul", "from Amit")
    if not customer_name:
        for token in doc:
            if token.text.lower() in ["to", "from", "for", "by"]:
                for child in token.children:
                    if child.dep_ == "pobj" and child.pos_ in ["PROPN", "NOUN", "X"]:
                        customer_name = child.text.strip().title()
                        break
                if customer_name:
                    break
                next_idx = token.i + 1
                if next_idx < len(doc):
                    next_token = doc[next_idx]
                    if next_token.pos_ in ["PROPN", "NOUN", "X"] or next_token.text[0].isupper():
                        customer_name = next_token.text.strip().title()
                        break
                        
    # 3. Subject fallback (e.g. "Deepak paid me")
    if not customer_name:
        for token in doc:
            if token.dep_ == "nsubj" and token.pos_ in ["PROPN", "NOUN"] and token.text.lower() not in ["i", "he", "she", "they", "we", "who", "it", "you"]:
                customer_name = token.text.strip().title()
                break
                
    # Extract Amount
    amount = 0.0
    time_units = {"day", "days", "week", "weeks", "month", "months", "year", "years", "st", "nd", "rd", "th"}
    currency_indicators = {"rs", "rupees", "rupee", "usd", "dollars", "dollar", "inr", "₹", "$"}
    amount_candidates = []
    
    for token in doc:
        if token.pos_ == "NUM" or token.like_num:
            is_date_num = False
            head = token.head
            if head and head.text.lower() in time_units:
                is_date_num = True
            if token.i + 1 < len(doc):
                next_tok = doc[token.i + 1]
                if next_tok.text.lower() in time_units:
                    is_date_num = True
                    
            if not is_date_num:
                try:
                    clean_val = token.text.replace(",", "").replace("$", "").replace("₹", "")
                    amount_candidates.append((token.i, float(clean_val)))
                except ValueError:
                    pass
                    
    if amount_candidates:
        best_amount = None
        for idx, val in amount_candidates:
            if idx > 0 and doc[idx - 1].text.lower() in currency_indicators:
                best_amount = val
                break
            if idx + 1 < len(doc) and doc[idx + 1].text.lower() in currency_indicators:
                best_amount = val
                break
        if best_amount is None:
            best_amount = amount_candidates[0][1]
        amount = best_amount
        
    # Extract Transaction Type
    transaction_type = "credit"
    lemmas = [token.lemma_.lower() for token in doc]
    
    payment_verbs = {"pay", "receive", "got", "get", "clear", "return", "collect", "settle"}
    credit_verbs = {"borrow", "lend", "give", "take", "owe", "due", "credit"}
    sales_verbs = {"sell", "sold", "sale", "order", "bill"}
    expense_verbs = {"spend", "expense", "buy", "purchase", "cost"}
    
    if any(l in payment_verbs for l in lemmas):
        transaction_type = "payment"
    elif any(l in credit_verbs for l in lemmas):
        transaction_type = "credit"
    elif any(l in sales_verbs for l in lemmas):
        transaction_type = "sales"
    elif any(l in expense_verbs for l in lemmas):
        transaction_type = "expense"
        
    due_date = extract_due_date(doc)
    
    return {
        "is_sales": False,
        "customer_name": customer_name or "General",
        "amount": amount,
        "transaction_type": transaction_type,
        "due_date": due_date,
        "notes": corrected_text,
        "date": today_str,
        "status": "completed" if transaction_type == "payment" else "pending",
        "items": None,
        "parser_used": "spacy-nlp"
    }


def extract_and_clean_phone(text):
    """
    Search for a phone number in the text, extract it, and return the cleaned text
    (without the phone number part) along with the phone number string.
    """
    if not text:
        return text, None

    phone = None
    
    # 1. Look for keyword patterns: "mobile 9876543210", "phone number 98765-43210", etc.
    keyword_pattern = re.compile(
        r'\b(?:phone\s*number|mobile\s*number|whatsapp\s*number|number|mobile|phone|contact|whatsapp)\s*(?:is\s*)?(\+?\d[\d\s-]{8,14}\d)\b',
        re.IGNORECASE
    )
    
    match = keyword_pattern.search(text)
    if match:
        raw_phone = match.group(1)
        full_match = match.group(0)
        text = text.replace(full_match, "")
        phone = re.sub(r'[\s-]', '', raw_phone)
    else:
        # 2. Fallback: Search for any standalone 10-14 digit sequence (with optional leading +)
        # We look for a sequence of 10 to 14 digits, which may have spaces/dashes between digits
        standalone_pattern = re.compile(r'\b(\+?\d[\d\s-]{8,12}\d)\b')
        for match in standalone_pattern.finditer(text):
            raw_phone = match.group(1)
            digits_only = re.sub(r'[\s-]', '', raw_phone)
            # Check if digits only length is between 10 and 13 (including country code)
            if 10 <= len(digits_only.replace('+', '')) <= 13:
                phone = digits_only
                full_match = match.group(0)
                text = text.replace(full_match, "")
                break
                
    # Clean up multiple spaces left by removal
    text = re.sub(r'\s+', ' ', text).strip()
    return text, phone


# ---------------------------------------------------------------------------
# Primary Entry Point
# ---------------------------------------------------------------------------

def parse_speech_transcript(transcript):
    """
    Primary Entry Point: Attempts spaCy-based parsing first, falls back to rule-based.
    Automatically detects sales/item transactions and adds items list to response.
    """
    if not transcript or not transcript.strip():
        return {
            "customer_name": "General",
            "customer_phone": None,
            "amount": 0.0,
            "transaction_type": "credit",
            "due_date": None,
            "notes": "",
            "date": timezone.now().date().strftime('%Y-%m-%d'),
            "status": "pending",
            "items": None,
            "parser_used": "none"
        }

    # 1. Extract and clean phone number from transcript
    cleaned_transcript, customer_phone = extract_and_clean_phone(transcript)

    result = None
    # Try spaCy NLP parsing first
    try:
        result = parse_with_spacy(cleaned_transcript)
    except Exception as spacy_err:
        pass  # Fall through to rule-based fallback

    if not result:
        # Rule-based fallback
        corrected_text = autocorrect_transcript(cleaned_transcript)
        if is_sales_transcript(corrected_text):
            items = parse_sales_items_rule_based(corrected_text)
            if items:
                total = round(sum(item['total'] for item in items), 2)
                today = timezone.now().date().strftime('%Y-%m-%d')
                result = {
                    "customer_name": None,
                    "amount": total,
                    "transaction_type": "sales",
                    "due_date": None,
                    "notes": corrected_text,
                    "date": today,
                    "status": "completed",
                    "items": items,
                    "is_sales": True,
                    "parser_used": "rule-based-sales"
                }

        if not result:
            # Standard rule-based fallback for credit/payment etc.
            result = parse_with_rules(corrected_text)
            result['items'] = None
            result['is_sales'] = False
            result['parser_used'] = "rule-based-fallback"

    # Inject the extracted customer_phone into the result
    result['customer_phone'] = customer_phone
    return result
