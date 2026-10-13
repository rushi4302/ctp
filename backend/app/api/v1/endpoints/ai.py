from fastapi import APIRouter

from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/models", summary="Report actual classifier availability")
def model_status():
    image_available = AIService.load_tflite_model()
    text_available = AIService.load_nlp_model()
    object_detection_available = AIService.load_yolo_model()
    return {
        "image_classifier": {
            "available": image_available,
            "model": "civic_tflite",
            "error": AIService._tflite_load_error,
        },
        "text_classifier": {
            "available": text_available,
            "model": "xlm-roberta",
            "error": AIService._nlp_load_error,
        },
        "object_detector": {
            "available": object_detection_available,
            "model": "yolov8n",
            "error": AIService._yolo_load_error,
        },
    }
