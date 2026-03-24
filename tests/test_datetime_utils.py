"""Tests for Aura's datetime utility helpers."""

import unittest
from datetime import datetime
from unittest.mock import patch

from core.runtime.datetimeUtils import DateTimeUtils


class DateTimeUtilsTests(unittest.TestCase):
    """Validate preferred/storage datetime conversions for partial and full inputs."""

    def test_to_preferred_datetime_converts_storage_datetime(self):
        """Storage datetime strings should convert into the preferred combined format."""

        self.assertEqual(
            DateTimeUtils.toPreferredDateTime("2026-03-24 17:45:00"),
            "17:45 24/03/2026",
        )

    def test_to_storage_datetime_converts_preferred_datetime(self):
        """Preferred datetime strings should convert into storage datetime format."""

        self.assertEqual(
            DateTimeUtils.toStorageDateTime("17:45 24/03/2026"),
            "2026-03-24 17:45:00",
        )

    def test_to_storage_date_converts_preferred_date(self):
        """Preferred date strings should convert into storage date format."""

        self.assertEqual(
            DateTimeUtils.toStorageDate("24/03/2026"),
            "2026-03-24",
        )

    def test_to_storage_time_converts_preferred_time(self):
        """Preferred time strings should convert into storage time format."""

        self.assertEqual(
            DateTimeUtils.toStorageTime("17:45"),
            "17:45:00",
        )

    def test_time_only_uses_default_date_when_converting_to_storage_datetime(self):
        """Time-only values should use the supplied default date."""

        self.assertEqual(
            DateTimeUtils.toStorageDateTime("17:45", default_date="24/03/2026"),
            "2026-03-24 17:45:00",
        )

    def test_date_only_uses_default_time_when_converting_to_storage_datetime(self):
        """Date-only values should use the supplied default time."""

        self.assertEqual(
            DateTimeUtils.toStorageDateTime("24/03/2026", default_time="17:45"),
            "2026-03-24 17:45:00",
        )

    @patch("core.runtime.datetimeUtils.datetime")
    def test_time_only_defaults_to_current_date_when_default_not_supplied(self, mock_datetime):
        """Time-only values should fall back to the current local date."""

        mock_datetime.now.return_value = datetime(2026, 3, 24, 9, 0, 0)
        mock_datetime.strptime = datetime.strptime
        mock_datetime.combine = datetime.combine

        self.assertEqual(
            DateTimeUtils.toStorageDateTime("17:45"),
            "2026-03-24 17:45:00",
        )

    def test_split_datetime_returns_preferred_and_storage_parts(self):
        """Datetime splitting should expose both preferred and storage date/time pieces."""

        result = DateTimeUtils.splitDateTime("2026-03-24 17:45:00")

        self.assertEqual(result["type"], "datetime")
        self.assertEqual(result["preferred_date"], "24/03/2026")
        self.assertEqual(result["preferred_time"], "17:45")
        self.assertEqual(result["storage_date"], "2026-03-24")
        self.assertEqual(result["storage_time"], "17:45:00")
        self.assertEqual(result["preferred_datetime"], "17:45 24/03/2026")
        self.assertEqual(result["storage_datetime"], "2026-03-24 17:45:00")


if __name__ == "__main__":
    unittest.main()
