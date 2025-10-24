"""
Configuration module for Bank Statement Analyzer
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
JSON_DIR = DATA_DIR / "json"
VALIDATED_DIR = DATA_DIR / "validated"

# Supported banks
SUPPORTED_BANKS = {
    "scb": "ธนาคารไทยพาณิชย์",
    "tmb": "ธนาคารทหารไทยธนชาต",
    "bbl": "ธนาคารกรุงเทพ",
    "kbank": "ธนาคารกสิกรไทย",
    "ktb": "ธนาคารกรุงไทย"
}

# AI Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2048"))

# Processing Configuration
DEFAULT_ENCODING = "utf-8"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Validation Configuration
MAX_TRANSACTION_AMOUNT = 10000000  # 10 million THB
MIN_TRANSACTION_AMOUNT = 0.01
REQUIRED_FIELDS = ["date", "description", "amount"]

# Categories mapping (for auto-categorization)
CATEGORY_KEYWORDS = {
    "food": ["ร้านอาหาร", "food", "restaurant", "cafe", "starbucks", "mcdonald"],
    "shopping": ["7-eleven", "family mart", "lotus", "big c", "central", "shopee", "lazada"],
    "transport": ["bts", "mrt", "grab", "bolt", "fuel", "น้ำมัน", "ปตท"],
    "utilities": ["ไฟฟ้า", "น้ำประปา", "internet", "true", "ais", "dtac"],
    "entertainment": ["netflix", "spotify", "cinema", "โรงภาพยนตร์"],
    "health": ["โรงพยาบาล", "hospital", "clinic", "pharmacy", "ร้านยา"],
    "education": ["โรงเรียน", "school", "university", "course"],
    "transfer": ["โอนเงิน", "transfer", "promptpay"],
    "withdrawal": ["ถอนเงิน", "withdrawal", "atm"],
    "income": ["เงินเดือน", "salary", "รับโอน"]
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "app.log"

# Export settings
EXPORT_FORMATS = ["json", "csv", "excel"]
