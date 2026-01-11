import json
from datetime import timezone, datetime, timedelta, date
import re
import calendar
from pathlib import Path
from string import Template
import hashlib
import base64
import logging
from typing import Any

from core.conf import APP_NAME

logger = logging.getLogger(APP_NAME)


def convert_to_unix_timestamp(date_str, date_format="%d.%m.%Y %H:%M:%S"):
    utc_plus_5 = timezone(timedelta(hours=5))
    dt = datetime.strptime(date_str, date_format)
    dt = dt.replace(tzinfo=utc_plus_5)
    unix_timestamp = int(dt.timestamp())
    return unix_timestamp

def format_number(number: float) -> str:
    str_num = str(number)
    integer_part, *decimal_part = str_num.split('.')

    length = len(integer_part)
    groups = []
    for i in range(length, 0, -3):
        start = max(0, i - 3)
        groups.append(integer_part[start:i])
    formatted_integer = ' '.join(reversed(groups))

    if not decimal_part or decimal_part[0] == '0':
        return formatted_integer
    return f"{formatted_integer}.{decimal_part[0][:2]}"

def format_date_range(s_date, e_date):
    """Helper to format date range as a string."""
    return [f"{s_date.strftime('%d.%m.%Y')} 00:00:00", f"{e_date.strftime('%d.%m.%Y')} 23:59:59"]

def get_specific_month(period, today, format_date_range_function):
    start_of_month = date(today.year, period, 1)
    if period == 12:
        end_of_month = date(today.year, 12, 31)
    else:
        end_of_month = date(today.year, period + 1, 1) - timedelta(days=1)

    return format_date_range_function(start_of_month, end_of_month)

def get_date_range(periods_dict: dict):
    today = date.today()

    yesterday = today - timedelta(days=1)

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    end_of_last_week = today - timedelta(days=today.weekday() + 1)
    start_of_last_week = end_of_last_week - timedelta(days=6)

    start_of_month = date(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = date(today.year, 12, 31)
    else:
        end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

    first_of_current_month = date(today.year, today.month, 1)
    last_of_last_month = first_of_current_month - timedelta(days=1)
    first_of_last_month = date(last_of_last_month.year, last_of_last_month.month, 1)
    current_month = datetime.now().month
    start_of_year = datetime(datetime.now().year, 1, 1)

    months_list = [
        (1, periods_dict[1]),  # January
        (2, periods_dict[2]),  # February
        (3, periods_dict[3]),  # March
        (4, periods_dict[4]),  # April
        (5, periods_dict[5]),  # May
        (6, periods_dict[6]),  # June
        (7, periods_dict[7]),  # July
        (8, periods_dict[8]),  # August
        (9, periods_dict[9]),  # September
        (10, periods_dict[10]),  # October
        (11, periods_dict[11]),  # November
        (12, periods_dict[12])  # December
    ]

    period_dict = {
        "often_used_periods": {
            "today": [format_date_range(today, today), periods_dict["today"]],
            "yesterday": [format_date_range(yesterday, yesterday), periods_dict["yesterday"]],
            "current_week": [format_date_range(start_of_week, end_of_week), periods_dict["current_week"]],
            "last_week": [format_date_range(start_of_last_week, end_of_last_week), periods_dict["last_week"]],
            "current_month": [format_date_range(start_of_month, end_of_month), periods_dict["current_month"]],
            "last_month": [format_date_range(first_of_last_month, last_of_last_month), periods_dict["last_month"]],
            "current_year": [format_date_range(start_of_year, today), periods_dict["current_year"]]
        },
        "months": {
            month[1]: [get_specific_month(
                    month[0],
                    today=today,
                    format_date_range_function=format_date_range
                ), month[1]] for month in months_list if month[0] <= current_month
        }
    }

    return period_dict

def parse_flexible_date(date_str, is_end: bool = True):
    """
    Parse various date formats and return standardized datetime string.
    Returns date in 'YYYY-MM-DD HH:MM' format or False if invalid.
    If part of time not provided returns current date
    If is_end = True it sets time as 23:59, otherwise sets time as 00:00
    Valid formats:
    - Day only: '23' -> '23.12.2024 23:59'
    - Day.Month: '23.12' -> '23.12.2025 23:59'
    - Day.Month.Year: '23.12.2024' -> '23.12.2025 23:59'
    - Full datetime: '23.12.2024 23:00' -> '23.12.24 23:00'
    """
    try:
        # Remove leading zeros and extra spaces
        date_str = str(date_str).strip()

        # Get current date components for defaults
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Check for invalid characters
        if not re.match(r'^[\d\s.:]+$', date_str):
            return False

        # Split date and time if time is provided
        date_parts = date_str.split(' ')
        time_str = "23:59" if is_end else "00:00"  # Default time
        default_hour, default_minute = time_str.split(':')
        if len(date_parts) > 1:
            date_str = date_parts[0]
            time_str = date_parts[1]
            default_hour, default_minute = time_str.split(':')

            # Validate time format
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                return False

            if int(default_hour) > 23 or int(default_minute) > 59:
                return False

        # Split date components
        parts = date_str.split('.')

        # Validate each part is a number and within valid ranges
        for part in parts:
            if not part.isdigit() or int(part) > 9999:
                return False


        if len(parts) == 1:  # Only day provided
            day = int(parts[0])
            if day < 1 or day > 31:
                return False
            date_obj = datetime(current_year, current_month, day, int(default_hour), int(default_minute))

        elif len(parts) == 2:  # Day and month provided
            day, month = map(int, parts)
            if month < 1 or month > 12 or day < 1 or day > 31:
                return False
            date_obj = datetime(current_year, month, day, int(default_hour), int(default_minute))

        elif len(parts) == 3:  # Full date provided
            day, month, year = map(int, parts)
            if month < 1 or month > 12 or day < 1 or day > 31:
                return False

            # Handle two-digit year
            if year < 100:
                year += 2000

            if year < 1900 or year > 9999:
                return False


            date_obj = datetime(year, month, day, int(default_hour), int(default_minute))


        else:
            return False

        # Validate the date is real (handles invalid dates like 31.02.2024)
        try:
            date_obj.strftime('%d.%m.%Y %H:%M:%S')
        except ValueError:
            return False

        return date_obj.strftime('%d.%m.%Y %H:%M:%S')

    except (ValueError, TypeError):
        return False

def check_user_period(u_input):
    if u_input.count("-") > 1: return False
    if "-" in u_input:
        start_date, end_date = u_input.split('-')
        checked_start_date = parse_flexible_date(start_date, is_end=False)
        checked_end_date = parse_flexible_date(end_date)
        if checked_start_date and checked_end_date: return checked_start_date, checked_end_date
    else:
        start_date = parse_flexible_date(u_input, is_end=False)
        end_date = parse_flexible_date(u_input, is_end=True)
        if start_date and end_date: return start_date, end_date


def unix_to_formatted_string(unix_timestamp, shift_hours: int = 0):
    date_obj = datetime.fromtimestamp(unix_timestamp)
    desired_timezone = timezone(timedelta(hours=shift_hours))
    changed_time = date_obj.astimezone(desired_timezone)
    return changed_time.strftime('%d.%m.%Y %H:%M:%S')


def get_last_year_period():
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    now_timestamp = int(now.timestamp())
    year_ago_timestamp = int(one_year_ago.timestamp())
    return year_ago_timestamp, now_timestamp


def get_end_of_month():
    today_date = datetime.now()

    # Get the last day of the month
    last_day = calendar.monthrange(today_date.year, today_date.month)[1]

    # Create datetime object for the last day of the month
    end_of_month = datetime(today_date.year, today_date.month, last_day)

    # Format as DD.MM.YYYY
    return end_of_month.strftime("%d.%m.%Y")


# Method 2: Using plain text template file
def load_template_from_txt(template_file="debt_notification_template.txt"):
    """Load template from text file"""
    default_template = """<b>Уведомление о необходимости возврата долга</b>

Уважаемый(ая) ${partner_name},

Настоящим уведомляем Вас о наличии задолженности перед ${firm_name} в размере ${total_debt_amount} ${currency_name}.

В соответствии с условиями нашего договора срок оплаты истёк. Просим Вас погасить задолженность.

С уважением,
${boss_name} / Директор
Компания: ${firm_name}
Тел: ${firm_phone}
Дата и время: ${datetime}"""

    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Create default template file
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(default_template)
        return default_template


def format_message_from_txt(template_content, **kwargs):
    """Format message using text template"""
    template = Template(template_content)
    return template.safe_substitute(**kwargs)

def generate_hash_string(input_string):
    hash_object = hashlib.sha256(input_string.encode('utf-8'))
    return hash_object.hexdigest()

def read_hashed_data(filename="license.bin"):
    try:
        with open(filename, 'rb') as file:
            encoded_hash = file.read()

        hash_bytes = base64.b64decode(encoded_hash)

        hash_hex = hash_bytes.hex()

        logger.info(f"Hash read from {filename}")
        return hash_hex

    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        return None
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return None

def write_json_file(
        data: Any,
        file_path: str = "partner_operations.json",
        indent: int = 4,
        ensure_ascii: bool = False,
        create_dirs: bool = True
) -> bool:
    """
    Write Python object to JSON file with error handling.

    Args:
        data: Python object to write (dict, list, etc.)
        file_path: Path to the output JSON file
        indent: Number of spaces for indentation (None for compact)
        ensure_ascii: If False, non-ASCII characters are preserved
        create_dirs: If True, create parent directories if they don't exist

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert to Path object for easier manipulation
        path = Path(file_path)

        # Create parent directories if needed
        if create_dirs and path.parent != Path('.'):
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path.parent}")

        # Write to file with atomic operation (write to temp, then rename)
        temp_path = path.with_suffix('.tmp')

        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

        # Atomic rename (replaces existing file)
        temp_path.replace(path)

        logger.info(f"Successfully wrote JSON to: {file_path}")
        return True

    except TypeError as e:
        logger.error(f"Data is not JSON serializable: {e}")
        return False

    except PermissionError as e:
        logger.error(f"Permission denied writing to {file_path}: {e}")
        return False

    except OSError as e:
        logger.error(f"OS error writing to {file_path}: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error writing JSON to {file_path}: {e}")
        return False
