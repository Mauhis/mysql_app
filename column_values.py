"""Convert user values and generate numbers according to MySQL column types."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
import re
from random import randint, random


class ColumnValues:
    def __init__(self, sql_type):
        self.sql_type = sql_type.lower()
        self.base = self.sql_type.split('(')[0].split()[0]
        self.numeric = self.base in {
            'tinyint', 'smallint', 'mediumint', 'int', 'integer', 'bigint',
            'decimal', 'numeric', 'float', 'double', 'real', 'boolean', 'bool',
        }

    def parse(self, value):
        """Convert a value, rejecting overflow and lossy decimal conversion."""
        try:
            if self.numeric:
                number = Decimal(str(value))
                if not number.is_finite():
                    raise ValueError('Numbers must be finite.')
                bits = {'tinyint': 8, 'smallint': 16, 'mediumint': 24,
                        'int': 32, 'integer': 32, 'bigint': 64}.get(self.base)
                if bits or self.base in {'boolean', 'bool'}:
                    unsigned = 'unsigned' in self.sql_type
                    low = 0 if unsigned or not bits else -(2 ** (bits - 1))
                    high = (2 ** (bits if unsigned else bits - 1) - 1) if bits else 1
                    if number != number.to_integral_value() or not low <= number <= high:
                        raise ValueError(f'Enter a whole number between {low} and {high}.')
                    return int(number)
                if self.base in {'decimal', 'numeric'}:
                    match = re.search(r'\((\d+),\s*(\d+)\)', self.sql_type)
                    precision, scale = map(int, match.groups()) if match else (10, 0)
                    with localcontext() as context:
                        context.prec = max(80, precision + 2)
                        unit = Decimal(1).scaleb(-scale)
                        limit = Decimal(10) ** (precision - scale) - unit
                        if abs(number) > limit or number != number.quantize(unit):
                            raise ValueError(f'Value must fit {self.sql_type}.')
                else:
                    limit = Decimal('3.4028234663852886e38') if self.base == 'float' else Decimal(str(float.fromhex('0x1.fffffffffffffp+1023')))
                    if abs(number) > limit:
                        raise ValueError(f'Value must fit {self.sql_type}.')
                if 'unsigned' in self.sql_type and number < 0:
                    raise ValueError('Unsigned values cannot be negative.')
                return number if self.base in {'decimal', 'numeric'} else float(number)
            if self.base == 'date':
                result = date.fromisoformat(value)
                if result.year < 1000:
                    raise ValueError('Date year must be at least 1000.')
                return result
            if self.base in {'datetime', 'timestamp'}:
                result = datetime.fromisoformat(value)
                if result.year < 1000 or result.tzinfo is not None:
                    raise ValueError('Use a date/time without a timezone, year >= 1000.')
                return result
            if self.base in {'char', 'varchar', 'tinytext', 'text', 'mediumtext', 'longtext'}:
                match = re.search(r'\((\d+)\)', self.sql_type)
                if match and len(value) > int(match[1]):
                    raise ValueError(f'Text exceeds {match[1]} characters.')
                return value
        except (InvalidOperation, TypeError, OverflowError) as error:
            raise ValueError(f'Invalid value for {self.sql_type}.') from error
        raise ValueError(f'Unsupported column type: {self.sql_type}. Leave this column omitted.')

    def generator(self, bounds):
        if not self.numeric or not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError('Numeric ranges need a minimum and maximum.')
        low, high = (self.parse(value) for value in bounds)
        if low > high:
            raise ValueError('Minimum must be less than or equal to maximum.')
        if isinstance(low, int):
            return lambda: randint(low, high)
        if isinstance(low, Decimal):
            match = re.search(r'\((\d+),\s*(\d+)\)', self.sql_type)
            scale = int(match[2]) if match else 0
            with localcontext() as context:
                context.prec = 80
                lower = int(low.scaleb(scale))
                upper = int(high.scaleb(scale))
            def generate_decimal():
                with localcontext() as context:
                    context.prec = 80
                    return Decimal(randint(lower, upper)).scaleb(-scale)
            return generate_decimal
        def generate_float():
            weight = random()
            return min(high, max(low, low * (1 - weight) + high * weight))
        return generate_float
