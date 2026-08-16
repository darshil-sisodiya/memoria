"""Phase 2 database API tests."""

from fastapi.testclient import TestClient


def test_people_memories_and_conversations_api(client: TestClient) -> None:
    person_response = client.post(
        "/api/people",
        json={"name": "Synthetic Person", "description": "Test-only profile"},
    )
    assert person_response.status_code == 201
    person = person_response.json()
    person_id = person["id"]

    assert client.get(f"/api/people/{person_id}").json()["name"] == "Synthetic Person"

    memory_response = client.post(
        "/api/memories",
        json={
            "person_id": person_id,
            "title": "Synthetic trip",
            "content": "We visited a synthetic place.",
            "importance": 2,
        },
    )
    assert memory_response.status_code == 201
    memory_id = memory_response.json()["id"]
    assert client.get(f"/api/memories?person_id={person_id}").json()[0]["id"] == memory_id

    conversation_response = client.post(
        "/api/conversations",
        json={"person_id": person_id, "title": "First test conversation"},
    )
    assert conversation_response.status_code == 201
    assert conversation_response.json()["messages"] == []

    assert client.delete(f"/api/memories/{memory_id}").status_code == 204
    assert client.get(f"/api/memories/{memory_id}").status_code == 404

