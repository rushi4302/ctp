from fastapi import status

from app.services.ai_service import AIService


def test_ai_text_classification_real():
    result = AIService.classify_text("Huge pothole on the road causing traffic hazard")
    assert result["available"] is True
    assert result["category"] == "Pothole/Road Damage"
    assert result["confidence"] is not None
    assert result["confidence"] > 0.5


def test_ai_image_classification_real():
    result = AIService.classify_image("ai/test_images/sample2.jpg")
    assert result["available"] is True
    assert result["category"] == "Pothole/Road Damage"
    assert result["confidence"] is not None
    assert result["confidence"] > 0.5


def test_ai_multimodal_consensus():
    result = AIService.analyze_report(
        text="Huge pothole on the road causing traffic hazard",
        image_source="ai/test_images/sample2.jpg",
    )
    assert result["suggested_category"] == "Pothole/Road Damage"
    assert result["suggested_confidence"] is not None
    assert result["suggested_confidence"] > 0.5



def test_ai_fallback_empty_inputs():
    res = AIService.analyze_report(text="", image_source=None)
    assert res["suggested_category"] is None
    assert res["primary_source"] == "none"


def test_ai_endpoint(client, citizen_headers):
    response = client.post(
        "/api/v1/reports/analyze-ai",
        json={"text": "Severe waterlogging and flooding after rains"},
        headers=citizen_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "suggested_category" in data
    assert "primary_source" in data
