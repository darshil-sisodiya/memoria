"""WhatsApp parser and import API tests using synthetic data."""

import os
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

    assert result.skipped_lines == 0
    assert len(result.messages) == 3
    
    assert result.messages[0].is_system is True
    assert result.messages[0].content == "Export metadata that is not a message"

    assert result.messages[1].timestamp == datetime(2019, 8, 12, 20, 41)
    assert result.messages[1].sender == "Synthetic Person"
    assert result.messages[1].content == "Remember we're going tomorrow\nThis is a multiline message"
    
    assert result.messages[2].timestamp == datetime(2019, 8, 13, 9, 10)


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

    assert result.skipped_lines == 0
    assert len(result.messages) == 5
    
    assert result.messages[0].is_system is True
    assert result.messages[0].content == "Messages and calls are end-to-end encrypted."
    
    assert result.messages[1].is_media is True
    assert result.messages[1].is_system is True
    assert result.messages[1].content == "[Call]"
    
    assert result.messages[2].is_media is True
    assert result.messages[2].is_system is True
    
    assert result.messages[3].timestamp == datetime(2025, 8, 10, 11, 30, 39)
    assert result.messages[3].content == "First message\nSecond line"
    
    assert result.messages[4].sender == "You"


def test_finetuner_various_cases() -> None:
    chat_content = """This is a malformed line at the top
Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.
[5/26/25, 7:29:05 PM] - [Call]
[5/26/25, 7:30:00 PM] Alice: Hello everyone!
[5/26/25, 7:30:15 PM] Bob: Hi Alice.
[5/26/25, 7:30:30 PM] Bob: How are you?
[5/26/25, 7:31:00 PM] Alice: I am doing well.
This is a multiline message!
It spans multiple lines.
[5/26/25, 7:32:00 PM] Charlie: ok
[5/26/25, 7:33:00 PM] Alice: 👨‍🌾 emojis work?
[5/26/25, 7:34:00 PM] Bob: <Media omitted>
[5/26/25, 7:35:00 PM] Bob: 안녕하세요! This is korean.
[5/26/25, 7:36:00 PM] Charlie: Hello, how are things going? I hope well!
Just some random malformed line without a previous context
[5/26/25, 7:37:00 PM] Alice: End."""

    messages = WhatsAppParser().parse(chat_content).messages

    assert len(messages) == 13
    
    # 1. Malformed line at the top becomes a system message
    assert messages[0].is_system is True
    assert messages[0].content == "This is a malformed line at the top"
    
    # 2. Encryption message
    assert messages[1].is_system is True
    assert "end-to-end encrypted" in messages[1].content
    
    # 3. System message [Call]
    assert messages[2].is_system is True
    assert messages[2].is_media is True
    assert messages[2].content == "[Call]"
    
    # 4. Normal message & Multiple speakers
    assert messages[3].sender == "Alice"
    assert messages[3].content == "Hello everyone!"
    
    # 5. Consecutive messages
    assert messages[4].sender == "Bob"
    assert messages[5].sender == "Bob"
    
    # 6. Multiline message
    assert messages[6].sender == "Alice"
    assert "multiline message!" in messages[6].content
    assert "multiple lines." in messages[6].content
    
    # 7. Short message
    assert messages[7].content == "ok"
    
    # 8. Emoji
    assert "👨‍🌾" in messages[8].content
    
    # 9. Media placeholder
    assert messages[9].is_media is True
    assert messages[9].content == "<Media omitted>"
    
    # 10. Unicode/non-English
    assert "안녕하세요" in messages[10].content
    
    # 11. Punctuation
    assert messages[11].sender == "Charlie"
    assert "Hello, how are things going?" in messages[11].content


def test_integration() -> None:
    raw_chat = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "whatsapp", "chat.txt"))
    if os.path.exists(raw_chat):
        with open(raw_chat, "r", encoding="utf-8") as f:
            text = f.read()
        parsed = WhatsAppParser().parse(text)
        
        assert len(parsed.messages) > 0
        
        multiline_count = sum(1 for m in parsed.messages if "\n" in m.content)
        system_count = sum(1 for m in parsed.messages if m.is_system)
        media_count = sum(1 for m in parsed.messages if m.is_media)
        unique_speakers = len({m.sender for m in parsed.messages if m.sender})
        
        assert len(parsed.messages) >= 19000
        assert multiline_count > 100
        assert system_count > 0
        assert media_count > 0
        assert unique_speakers > 0


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
