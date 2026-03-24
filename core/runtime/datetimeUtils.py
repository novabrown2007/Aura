"""Datetime formatting helpers for Aura runtime modules."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional, Tuple


class DateTimeUtils:
    """
    Convert between Aura's preferred datetime formats and storage formats.

    Preferred Aura formats:
    - datetime: `HH:MM DD/MM/YYYY`
    - date: `DD/MM/YYYY`
    - time: `HH:MM`

    Storage formats:
    - datetime: `YYYY-MM-DD HH:MM:SS`
    - date: `YYYY-MM-DD`
    - time: `HH:MM:SS`
    """

    PREFERRED_DATETIME_FORMAT = "%H:%M %d/%m/%Y"
    PREFERRED_DATE_FORMAT = "%d/%m/%Y"
    PREFERRED_TIME_FORMAT = "%H:%M"

    STORAGE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    STORAGE_DATE_FORMAT = "%Y-%m-%d"
    STORAGE_TIME_FORMAT = "%H:%M:%S"

    @classmethod
    def toPreferredDateTime(cls, value: str) -> str:
        """
        Convert a supported datetime string into Aura's preferred datetime format.
        """

        parsed_datetime, value_type = cls._parseFlexibleValue(value)
        if value_type != "datetime":
            raise ValueError("A full datetime value is required.")
        return parsed_datetime.strftime(cls.PREFERRED_DATETIME_FORMAT)

    @classmethod
    def toPreferredDate(cls, value: str) -> str:
        """
        Convert a supported date or datetime string into Aura's preferred date format.
        """

        parsed_datetime, _value_type = cls._parseFlexibleValue(value)
        return parsed_datetime.strftime(cls.PREFERRED_DATE_FORMAT)

    @classmethod
    def toPreferredTime(cls, value: str) -> str:
        """
        Convert a supported time or datetime string into Aura's preferred time format.
        """

        parsed_datetime, _value_type = cls._parseFlexibleValue(value)
        return parsed_datetime.strftime(cls.PREFERRED_TIME_FORMAT)

    @classmethod
    def toStorageDateTime(
        cls,
        value: str,
        default_date: Optional[str] = None,
        default_time: Optional[str] = None,
    ) -> str:
        """
        Convert a supported input into Aura's storage datetime format.

        Date-only values default to `00:00:00` unless `default_time` is supplied.
        Time-only values require `default_date` or fall back to today's local date.
        """

        parsed_datetime, value_type = cls._parseFlexibleValue(
            value,
            default_date=default_date,
            default_time=default_time,
        )

        if value_type == "date" and default_time is None:
            parsed_datetime = datetime.combine(parsed_datetime.date(), time(0, 0, 0))

        return parsed_datetime.strftime(cls.STORAGE_DATETIME_FORMAT)

    @classmethod
    def toStorageDate(cls, value: str) -> str:
        """
        Convert a supported date or datetime string into Aura's storage date format.
        """

        parsed_datetime, _value_type = cls._parseFlexibleValue(value)
        return parsed_datetime.strftime(cls.STORAGE_DATE_FORMAT)

    @classmethod
    def toStorageTime(cls, value: str) -> str:
        """
        Convert a supported time or datetime string into Aura's storage time format.
        """

        parsed_datetime, _value_type = cls._parseFlexibleValue(value)
        return parsed_datetime.strftime(cls.STORAGE_TIME_FORMAT)

    @classmethod
    def combineDateAndTime(cls, date_value: str, time_value: str) -> str:
        """
        Combine separate date and time inputs into a storage datetime string.
        """

        normalized_date = cls.toStorageDate(date_value)
        normalized_time = cls.toStorageTime(time_value)
        return f"{normalized_date} {normalized_time}"

    @classmethod
    def splitDateTime(cls, value: str) -> dict:
        """
        Split a supported datetime string into both preferred and storage parts.
        """

        parsed_datetime, value_type = cls._parseFlexibleValue(value)
        result = {
            "type": value_type,
            "preferred_date": parsed_datetime.strftime(cls.PREFERRED_DATE_FORMAT),
            "preferred_time": parsed_datetime.strftime(cls.PREFERRED_TIME_FORMAT),
            "storage_date": parsed_datetime.strftime(cls.STORAGE_DATE_FORMAT),
            "storage_time": parsed_datetime.strftime(cls.STORAGE_TIME_FORMAT),
        }
        if value_type == "datetime":
            result["preferred_datetime"] = parsed_datetime.strftime(cls.PREFERRED_DATETIME_FORMAT)
            result["storage_datetime"] = parsed_datetime.strftime(cls.STORAGE_DATETIME_FORMAT)
        return result

    @classmethod
    def _parseFlexibleValue(
        cls,
        value: str,
        default_date: Optional[str] = None,
        default_time: Optional[str] = None,
    ) -> Tuple[datetime, str]:
        """
        Parse a date, time, or datetime string into a datetime and detected type.
        """

        raw_value = str(value).strip()
        if raw_value == "":
            raise ValueError("A date/time value is required.")

        datetime_formats = (
            cls.STORAGE_DATETIME_FORMAT,
            "%Y-%m-%d %H:%M",
            cls.PREFERRED_DATETIME_FORMAT,
            "%H:%M:%S %d/%m/%Y",
            "%H%M %d/%m/%Y",
            "%H%M%S %d/%m/%Y",
        )
        date_formats = (
            cls.STORAGE_DATE_FORMAT,
            cls.PREFERRED_DATE_FORMAT,
        )
        time_formats = (
            cls.STORAGE_TIME_FORMAT,
            cls.PREFERRED_TIME_FORMAT,
            "%H%M",
            "%H%M%S",
        )

        for format_string in datetime_formats:
            try:
                return datetime.strptime(raw_value, format_string), "datetime"
            except ValueError:
                continue

        for format_string in date_formats:
            try:
                parsed_date = datetime.strptime(raw_value, format_string).date()
                parsed_time = cls._resolveDefaultTime(default_time)
                return datetime.combine(parsed_date, parsed_time), "date"
            except ValueError:
                continue

        for format_string in time_formats:
            try:
                parsed_time = datetime.strptime(raw_value, format_string).time()
                parsed_date = cls._resolveDefaultDate(default_date)
                return datetime.combine(parsed_date, parsed_time), "time"
            except ValueError:
                continue

        raise ValueError(
            "Invalid date/time value. Use HH:MM DD/MM/YYYY, DD/MM/YYYY, or HH:MM."
        )

    @classmethod
    def _resolveDefaultDate(cls, default_date: Optional[str]) -> date:
        """
        Resolve the date used when only a time value is supplied.
        """

        if default_date is None:
            return datetime.now().date()

        raw_value = str(default_date).strip()
        for format_string in (cls.STORAGE_DATE_FORMAT, cls.PREFERRED_DATE_FORMAT):
            try:
                return datetime.strptime(raw_value, format_string).date()
            except ValueError:
                continue

        raise ValueError("Invalid default date. Use YYYY-MM-DD or DD/MM/YYYY.")

    @classmethod
    def _resolveDefaultTime(cls, default_time: Optional[str]) -> time:
        """
        Resolve the time used when only a date value is supplied.
        """

        if default_time is None:
            return time(0, 0, 0)

        raw_value = str(default_time).strip()
        for format_string in (cls.STORAGE_TIME_FORMAT, cls.PREFERRED_TIME_FORMAT, "%H%M", "%H%M%S"):
            try:
                return datetime.strptime(raw_value, format_string).time()
            except ValueError:
                continue

        raise ValueError("Invalid default time. Use HH:MM or HH:MM:SS.")
