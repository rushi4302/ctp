import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Model mapping from TFLite model to standard civic categories
TFLITE_LABEL_MAPPING = {
    "pothole": "Pothole/Road Damage",
    "trash": "Garbage",
    "flood": "Drainage Problem",
    "homeless_people": "Other",
}



class AIService:
    _nlp_model = None
    _nlp_tokenizer = None
    _nlp_loaded = False
    _nlp_load_error: Optional[str] = None

    _tflite_interpreter = None
    _tflite_labels: List[str] = []
    _tflite_loaded = False
    _tflite_load_error: Optional[str] = None

    _yolo_model = None
    _yolo_loaded = False
    _yolo_load_error: Optional[str] = None

    @classmethod
    def _find_asset_path(cls, relative_path: str) -> Optional[Path]:
        """Searches for model asset in common locations."""
        candidates = [
            Path(relative_path),
            Path("..") / relative_path,
            Path(__file__).resolve().parent.parent.parent.parent / relative_path,
        ]
        if settings.ai_model_path:
            candidates.insert(0, Path(settings.ai_model_path) / relative_path)

        for c in candidates:
            if c.exists():
                return c.resolve()
        return None

    @classmethod
    def load_nlp_model(cls) -> bool:
        """Lazily load XLM-RoBERTa civic NLP model once and cache in memory."""
        if cls._nlp_loaded:
            return cls._nlp_model is not None

        cls._nlp_loaded = True
        model_dir = cls._find_asset_path("ai/model/civic_nlp_model")
        if not model_dir:
            cls._nlp_load_error = "XLM-RoBERTa civic_nlp_model directory not found."
            logger.warning(cls._nlp_load_error)
            return False

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info(f"Loading civic NLP model from {model_dir}...")
            cls._nlp_tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            cls._nlp_model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
            cls._nlp_model.eval()
            logger.info("Civic NLP model loaded successfully.")
            return True
        except Exception as e:
            cls._nlp_load_error = f"Failed to load NLP model: {e}"
            logger.error(cls._nlp_load_error)
            cls._nlp_model = None
            cls._nlp_tokenizer = None
            return False

    @classmethod
    def load_tflite_model(cls) -> bool:
        """Lazily load civic_model.tflite image model once and cache in memory."""
        if cls._tflite_loaded:
            return cls._tflite_interpreter is not None

        cls._tflite_loaded = True
        model_file = cls._find_asset_path("ai/model/civic_model.tflite")
        labels_file = cls._find_asset_path("ai/model/labels.txt")

        if not model_file or not labels_file:
            cls._tflite_load_error = "civic_model.tflite or labels.txt not found."
            logger.warning(cls._tflite_load_error)
            return False

        try:
            try:
                from ai_edge_litert.interpreter import Interpreter
            except ImportError:
                import tensorflow as tf
                Interpreter = tf.lite.Interpreter

            with open(labels_file, "r") as f:
                cls._tflite_labels = [line.strip() for line in f if line.strip()]

            cls._tflite_interpreter = Interpreter(model_path=str(model_file))
            cls._tflite_interpreter.allocate_tensors()
            logger.info("Civic TFLite image model loaded successfully.")
            return True
        except Exception as e:
            cls._tflite_load_error = f"Failed to load TFLite model: {e}"
            logger.error(cls._tflite_load_error)
            cls._tflite_interpreter = None
            return False

    @classmethod
    def load_yolo_model(cls) -> bool:
        """Lazily load YOLOv8n pretrained model for supplementary object detection."""
        if cls._yolo_loaded:
            return cls._yolo_model is not None

        cls._yolo_loaded = True
        yolo_file = cls._find_asset_path("ai/yolov8n.pt")
        if not yolo_file:
            cls._yolo_load_error = "yolov8n.pt model not found."
            logger.warning(cls._yolo_load_error)
            return False

        try:
            from ultralytics import YOLO

            cls._yolo_model = YOLO(str(yolo_file))
            logger.info("Pretrained YOLOv8n model loaded successfully.")
            return True
        except Exception as e:
            cls._yolo_load_error = f"Failed to load YOLO model: {e}"
            logger.error(cls._yolo_load_error)
            cls._yolo_model = None
            return False

    @classmethod
    def classify_text(cls, text: str) -> Dict[str, Any]:
        """
        Classifies complaint text using the trained XLM-RoBERTa model.
        Returns prediction category, confidence score, and model info.
        """
        if not text or not text.strip():
            return {
                "available": True,
                "category": None,
                "confidence": 0.0,
                "model": "none",
            }

        if not cls.load_nlp_model():
            return {
                "available": False,
                "error": cls._nlp_load_error or "NLP model unavailable",
                "category": None,
                "confidence": None,
                "model": "xlm-roberta",
            }

        try:
            import torch

            inputs = cls._nlp_tokenizer(
                text.strip(),
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128,
            )

            with torch.no_grad():
                outputs = cls._nlp_model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)[0]
                prediction_idx = torch.argmax(probabilities).item()
                confidence = float(probabilities[prediction_idx].item())

            predicted_label = cls._nlp_model.config.id2label.get(
                prediction_idx,
                str(prediction_idx),
            )

            return {
                "available": True,
                "category": predicted_label,
                "confidence": round(confidence, 4),
                "model": "xlm-roberta",
            }
        except Exception as e:
            logger.error(f"Error during NLP classification: {e}")
            return {
                "available": False,
                "error": str(e),
                "category": None,
                "confidence": None,
                "model": "xlm-roberta",
            }

    @classmethod
    def classify_image(cls, image_source: str | bytes) -> Dict[str, Any]:
        """
        Classifies civic issue image using the trained civic_model.tflite.
        """
        if not cls.load_tflite_model():
            return {
                "available": False,
                "error": cls._tflite_load_error or "TFLite model unavailable",
                "category": None,
                "confidence": None,
                "model": "civic_tflite",
            }

        try:
            if isinstance(image_source, bytes):
                img = Image.open(io.BytesIO(image_source))
            else:
                img = Image.open(image_source)

            img = img.convert("RGB").resize((224, 224))
            img_array = np.array(img, dtype=np.float32) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            input_details = cls._tflite_interpreter.get_input_details()
            output_details = cls._tflite_interpreter.get_output_details()

            cls._tflite_interpreter.set_tensor(input_details[0]["index"], img_array)
            cls._tflite_interpreter.invoke()
            output = cls._tflite_interpreter.get_tensor(output_details[0]["index"])[0]

            prediction_index = int(np.argmax(output))
            raw_confidence = float(output[prediction_index])
            raw_label = (
                cls._tflite_labels[prediction_index]
                if prediction_index < len(cls._tflite_labels)
                else "unknown"
            )

            standard_category = TFLITE_LABEL_MAPPING.get(
                raw_label.lower(),
                raw_label.capitalize(),
            )

            return {
                "available": True,
                "category": standard_category,
                "raw_label": raw_label,
                "confidence": round(raw_confidence, 4),
                "model": "civic_tflite",
            }
        except Exception as e:
            logger.error(f"Error during TFLite classification: {e}")
            return {
                "available": False,
                "error": str(e),
                "category": None,
                "confidence": None,
                "model": "civic_tflite",
            }

    @classmethod
    def detect_objects_yolo(cls, image_source: str | bytes) -> Dict[str, Any]:
        """
        Runs pretrained YOLOv8n object detection for supplementary environment cues.
        """
        if not cls.load_yolo_model():
            return {
                "available": False,
                "error": cls._yolo_load_error or "YOLO model unavailable",
                "detections": [],
                "model": "yolov8n-pretrained",
            }

        try:
            if isinstance(image_source, bytes):
                img = Image.open(io.BytesIO(image_source)).convert("RGB")
            else:
                img = Image.open(image_source).convert("RGB")

            results = cls._yolo_model(img, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    detections.append({
                        "label": cls._yolo_model.names.get(cls_id, f"class_{cls_id}"),
                        "confidence": round(conf, 4),
                    })

            return {
                "available": True,
                "detections": detections,
                "model": "yolov8n-pretrained",
            }
        except Exception as e:
            logger.error(f"Error during YOLO detection: {e}")
            return {
                "available": False,
                "error": str(e),
                "detections": [],
                "model": "yolov8n-pretrained",
            }

    @classmethod
    def analyze_report(
        cls,
        text: Optional[str] = None,
        image_source: Optional[str | bytes] = None,
    ) -> Dict[str, Any]:
        """
        Multimodal analysis:
        1. Classifies complaint text with XLM-RoBERTa.
        2. Classifies complaint image with civic TFLite.
        3. Fuses predictions into a suggested category and confidence score.
        """
        text_result = cls.classify_text(text) if text else None
        image_result = cls.classify_image(image_source) if image_source else None

        suggested_category: Optional[str] = None
        suggested_confidence: Optional[float] = None
        primary_source = "none"

        # Prioritize NLP if text is available with high confidence, otherwise image model
        if text_result and text_result.get("available") and text_result.get("category"):
            suggested_category = text_result["category"]
            suggested_confidence = text_result["confidence"]
            primary_source = "nlp"

            # Cross-validate if image result also exists
            if (
                image_result
                and image_result.get("available")
                and image_result.get("category")
            ):
                if image_result["category"] == suggested_category:
                    # Boost confidence when text and image agree
                    suggested_confidence = min(
                        round(suggested_confidence * 1.05, 4),
                        0.99,
                    )
                    primary_source = "multimodal_consensus"
                elif (
                    image_result["confidence"] is not None
                    and text_result["confidence"] is not None
                    and image_result["confidence"] > text_result["confidence"] + 0.25
                ):
                    # Image model is significantly more confident
                    suggested_category = image_result["category"]
                    suggested_confidence = image_result["confidence"]
                    primary_source = "image"
        elif image_result and image_result.get("available") and image_result.get("category"):
            suggested_category = image_result["category"]
            suggested_confidence = image_result["confidence"]
            primary_source = "image"

        return {
            "suggested_category": suggested_category,
            "suggested_confidence": suggested_confidence,
            "primary_source": primary_source,
            "text_analysis": text_result,
            "image_analysis": image_result,
        }
