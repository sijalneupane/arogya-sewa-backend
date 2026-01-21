import base64
import json
import logging
import os

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)


def init_firebase():
    try:
        if firebase_admin._apps:
            return  # Prevent re-initialization

        firebase_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")

        if not firebase_base64:
            raise RuntimeError("Firebase credentials not found")
        cred_dict = json.loads(
            base64.b64decode(firebase_base64).decode(encoding="utf-8")
        )

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info(f"Firebase initialized for project: {cred_dict.get('project_id')}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid Firebase credentials JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Firebase initialization error: {e}")
        raise
