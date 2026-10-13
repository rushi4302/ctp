def test_public_search_and_comment_collection(client, citizen_headers):
    created = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Searchable FC Road pothole",
            "description": "A sample pothole for search and comments testing.",
            "category": "Pothole/Road Damage",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    search = client.get("/api/v1/search", params={"q": "Searchable FC Road"})
    assert search.status_code == 200
    assert any(item["id"] == report_id for item in search.json())

    added = client.post(
        "/api/v1/comments",
        params={"report_id": report_id},
        headers=citizen_headers,
        json={"content": "I can confirm the location."},
    )
    assert added.status_code == 201
    assert "email" not in added.json()["user"]
    listed = client.get("/api/v1/comments", params={"report_id": report_id})
    assert listed.status_code == 200
    assert [comment["content"] for comment in listed.json()] == [
        "I can confirm the location."
    ]
