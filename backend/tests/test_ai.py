from pathlib import Path

from fastapi import status

from app.services.ai_service import AIService

SAMPLE_IMAGE = Path(__file__).resolve().parents[2] / "ai" / "test_images" / "sample2.jpg"


def test_ai_text_classifier_reports_missing_model_explicitly():
    result = AIService.classify_text("Huge pothole on the road causing traffic hazard")
    assert result["available"] is False
    assert result["category"] is None
    assert "not found" in result["error"]


def test_ai_image_classification_real():
    result = AIService.classify_image(str(SAMPLE_IMAGE))
    assert result["available"] is True
    assert result["category"] == "Pothole/Road Damage"
    assert result["confidence"] is not None
    assert result["confidence"] > 0.5


def test_ai_multimodal_consensus():
    result = AIService.analyze_report(
        text="Huge pothole on the road causing traffic hazard",
        image_source=str(SAMPLE_IMAGE),
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


def test_model_status_reports_available_assets(client):
    response = client.get("/api/v1/ai/models")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["image_classifier"]["available"] is True
    assert data["text_classifier"]["available"] is False
    assert "not found" in data["text_classifier"]["error"]
    assert data["object_detector"]["available"] is False
    assert "ultralytics" in data["object_detector"]["error"]
