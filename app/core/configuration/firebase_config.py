import base64
import json
import os

import firebase_admin
from firebase_admin import credentials


def init_firebase():
    if firebase_admin._apps:
        return  # Prevent re-initialization

    firebase_base64 = os.getenv("FIREBASE_CREDENTIALS_BASE64")

    if not firebase_base64:
        raise RuntimeError("Firebase credentials not found")

    cred_dict = json.loads(base64.b64decode(firebase_base64).decode("utf-8"))

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
