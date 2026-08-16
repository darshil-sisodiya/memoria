"""Parser for common WhatsApp text export formats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ParsedWhatsAppMessage:
    """A message parsed from one WhatsApp header and its continuation lines."""

    timestamp: datetime
    sender: str
    content: str
    line_number: int


@dataclass(frozen=True)
class WhatsAppParseResult:
    """Parsed messages plus lines that could not begin a message."""

    messages: list[ParsedWhatsAppMessage]
    skipped_lines: int


class WhatsAppParser:
    """Parse WhatsApp exports without assuming a single date delimiter or locale."""

    _header_patterns = (
        re.compile(
            r"^(?P<date>[^,\[\]]+),\s*(?P<time>[^\-\[\]]+)\s+-\s+(?P<body>.*)$"
        ),
        re.compile(
            r"^\[(?P<date>[^,\]]+),\s*(?P<time>[^\]]+)\]\s*(?P<body>.*)$"
        ),
    )
    _date_time_formats = (
        "%d/%m/%Y, %H:%M",
        "%m/%d/%Y, %H:%M",
        "%d-%m-%Y, %H:%M",
        "%m-%d-%Y, %H:%M",
        "%Y-%m-%d, %H:%M",
        "%d/%m/%y, %H:%M",
        "%m/%d/%y, %H:%M",
        "%d/%m/%Y, %H:%M:%S",
        "%m/%d/%Y, %H:%M:%S",
        "%d-%m-%Y, %H:%M:%S",
        "%m-%d-%Y, %H:%M:%S",
        "%d/%m/%y, %H:%M:%S",
        "%m/%d/%y, %H:%M:%S",
        "%d/%m/%Y, %I:%M %p",
        "%m/%d/%Y, %I:%M %p",
        "%d-%m-%Y, %I:%M %p",
        "%m-%d-%Y, %I:%M %p",
        "%d/%m/%y, %I:%M %p",
        "%m/%d/%y, %I:%M %p",
        "%d-%m-%y, %I:%M %p",
        "%m-%d-%y, %I:%M %p",
        "%d/%m/%Y, %I:%M:%S %p",
        "%m/%d/%Y, %I:%M:%S %p",
        "%d-%m-%Y, %I:%M:%S %p",
        "%m-%d-%Y, %I:%M:%S %p",
        "%d/%m/%y, %I:%M:%S %p",
        "%m/%d/%y, %I:%M:%S %p",
        "%d-%m-%y, %I:%M:%S %p",
        "%m-%d-%y, %I:%M:%S %p",
        "%d/%m/%Y, %I:%M%p",
        "%m/%d/%Y, %I:%M%p",
        "%d/%m/%y, %I:%M%p",
        "%m/%d/%y, %I:%M%p",
        "%d/%m/%Y, %I:%M:%S%p",
        "%m/%d/%Y, %I:%M:%S%p",
        "%d/%m/%y, %I:%M:%S%p",
        "%m/%d/%y, %I:%M:%S%p",
    )

    def parse(self, text: str) -> WhatsAppParseResult:
        """Parse normal and bracketed headers while preserving multiline content."""

        messages: list[ParsedWhatsAppMessage] = []
        skipped_lines = 0
        current: dict[str, object] | None = None
        date_order = self._infer_date_order(text)

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.rstrip("\r")
            header = self._parse_header(line, date_order)
            if header is not None:
                if current is not None:
                    messages.append(self._finish_message(current))
                timestamp, sender, content = header
                if not sender:
                    skipped_lines += 1
                    current = None
                    continue
                current = {
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "line_number": line_number,
                }
                continue

            if current is None:
                if line.strip():
                    skipped_lines += 1
                continue

            current["content"] = f"{current['content']}\n{line}"

        if current is not None:
            messages.append(self._finish_message(current))

        return WhatsAppParseResult(messages=messages, skipped_lines=skipped_lines)

    def _parse_header(self, line: str, date_order: str) -> tuple[datetime, str, str] | None:
        for pattern in self._header_patterns:
            match = pattern.match(line)
            if match is None:
                continue

            timestamp = self._parse_timestamp(match.group("date"), match.group("time"), date_order)
            if timestamp is None:
                continue

            body = match.group("body")
            if ":" not in body:
                # Timestamped call/system records have no sender/message.
                # Recognize them so they do not become continuations of the
                # preceding chat message.
                return timestamp, "", ""
            sender, content = body.split(":", maxsplit=1)
            sender = sender.strip()
            if not sender:
                return None
            return timestamp, sender, content.lstrip()
        return None

    def _parse_timestamp(self, date_part: str, time_part: str, date_order: str) -> datetime | None:
        # Mobile exports may use NBSP/narrow-NBSP around lowercase am/pm.
        # Normalize those characters before applying the locale candidates.
        normalized_date = date_part.replace("\u00a0", " ").replace("\u202f", " ").strip()
        normalized_time = time_part.replace("\u00a0", " ").replace("\u202f", " ").strip()
        normalized_time = re.sub(r"\s+", " ", normalized_time).upper()
        value = f"{normalized_date}, {normalized_time}"
        formats = self._date_time_formats
        if date_order == "month_first":
            formats = tuple(
                format_string
                for format_string in self._date_time_formats
                if format_string.startswith("%m")
            ) + tuple(
                format_string
                for format_string in self._date_time_formats
                if not format_string.startswith("%m")
            )
        for date_time_format in formats:
            try:
                return datetime.strptime(value, date_time_format)
            except ValueError:
                continue
        return None

    @staticmethod
    def _infer_date_order(text: str) -> str:
        """Infer month/day versus day/month from unambiguous dates in an export.

        Ambiguous dates such as 8/10/25 cannot identify their locale alone. If
        the file contains a date such as 5/26/25, the second component proves
        the export is month-first. When no such evidence exists, day-first is
        retained for compatibility with common WhatsApp exports.
        """

        month_first = False
        day_first = False
        date_pattern = re.compile(r"^\[?(?P<date>\d{1,4}[/-]\d{1,2}[/-]\d{1,4}),")
        for line in text.splitlines():
            match = date_pattern.match(line)
            if match is None:
                continue
            parts = re.split(r"[/-]", match.group("date"))
            if len(parts) != 3 or len(parts[0]) == 4:
                continue
            first, second = int(parts[0]), int(parts[1])
            if second > 12:
                month_first = True
            elif first > 12:
                day_first = True
        if month_first and not day_first:
            return "month_first"
        return "day_first"

    @staticmethod
    def _finish_message(raw: dict[str, object]) -> ParsedWhatsAppMessage:
        return ParsedWhatsAppMessage(
            timestamp=raw["timestamp"],  # type: ignore[arg-type]
            sender=str(raw["sender"]),
            content=str(raw["content"]),
            line_number=int(raw["line_number"]),
        )


def decode_whatsapp_bytes(payload: bytes) -> str:
    """Decode common local WhatsApp export encodings."""

    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("whatsapp", payload, 0, len(payload), "Unsupported text encoding")
