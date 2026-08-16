"""WhatsApp parser and import API tests using synthetic data."""

from datetime import datetime

from fastapi.testclient import TestClient

from backend.app.importers.whatsapp import WhatsAppParser


def test_parser_supports_normal_bracketed_and_multiline_messages() -> None:
    text = (
        "Export metadata that is not a message\n"
        "12/08/2019, 20:41 - Synthetic Person: Remember we're going tomorrow\n"
        "This is a multiline message\n"
        "[13/08/2019, 09:10] Friend: Yes, I remember.\n"
    )

    result = WhatsAppParser().parse(text)

    assert result.skipped_lines == 1
    assert len(result.messages) == 2
    assert result.messages[0].timestamp == datetime(2019, 8, 12, 20, 41)
    assert result.messages[0].sender == "Synthetic Person"
    assert result.messages[0].content == "Remember we're going tomorrow\nThis is a multiline message"
    assert result.messages[1].timestamp == datetime(2019, 8, 13, 9, 10)


def test_parser_handles_mobile_am_pm_spacing() -> None:
    result = WhatsAppParser().parse("8/4/2025, 11:44\u202fpm - Synthetic Person: Hello\n")

    assert result.skipped_lines == 0
    assert result.messages[0].timestamp == datetime(2025, 4, 8, 23, 44)


def test_parser_handles_bracketed_seconds_and_skips_call_records() -> None:
    text = (
        "Messages and calls are end-to-end encrypted.\n"
        "[5/26/25, 7:29:05 PM] - [Call]\n"
        "[6/1/25, 10:37:04 PM] - [Call]\n"
        "[8/10/25, 11:30:39 AM] Noel NHCE: First message\n"
        "Second line\n"
        "[8/10/25, 11:32:23 AM] You: Reply\n"
    )

    result = WhatsAppParser().parse(text)

    assert result.skipped_lines == 3
    assert len(result.messages) == 2
    assert result.messages[0].timestamp == datetime(2025, 8, 10, 11, 30, 39)
    assert result.messages[0].content == "First message\nSecond line"
    assert result.messages[1].sender == "You"


def test_import_endpoint_persists_whatsapp_messages(client: TestClient) -> None:
    person_response = client.post("/api/people", json={"name": "Synthetic Import Person"})
    person_id = person_response.json()["id"]
    chat = (
        "12/08/2019, 20:41 - Synthetic Person: Remember our synthetic trip?\n"
        "We should go tomorrow.\n"
        "[12/08/2019, 20:45] Friend: Yes.\n"
    )

    response = client.post(
        "/api/import/whatsapp",
        data={"person_id": str(person_id)},
        files={"file": ("synthetic-chat.txt", chat.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["messages_imported"] == 2
    assert response.json()["messages_skipped"] == 0
