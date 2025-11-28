#!/usr/bin/env python3

import os
import sys
import json
import tempfile
import string
import secrets
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.cloud.firestore import Transaction
import bcrypt

from app.logger import logger


class EmailConfig:
    EMAIL_USER = "biyoves.info@gmail.com"
    EMAIL_PASSWORD = "gdvcdbjcmvymuzxo"
    EMAIL_SMTP_SERVER = "smtp.gmail.com"
    EMAIL_SMTP_PORT = 587


email_config = EmailConfig()


if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
else:
    BASE_DIR = Path(__file__).resolve().parents[2]


# Firebase Service Account JSON
SERVICE_ACCOUNT_JSON_DICT = {
    "type": "service_account",
    "project_id": "biyoves-4b051",
    "private_key_id": "dfb9f14615531c1bedd5be32eaed97ae6d216a4b",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDxEz9kvpbVHm7P\nNysubIYp6TK/THkX0Nk2AUojFDlOoBH6zi8Pa/cuika/uXvW1JIrA/t5g7QoHmVG\nTQVXDhwfZO1huXasAZXSbgT0E7iIxynw7+I11789JUHYlxsFHO3aADtYuNX7uzm+\niZqFxgRUNooIiMRB+eR+58d2D+sKy/8qLemZxTE2NvyN2YPVRXpR+UknxUu7O9Xa\naI5YWc6gzTpbNHjDAeylk5ssvMwoTSiTm/ZLuEAj1at9DyVWBttHC43f7dwMJEUE\nwv/i5Mbxt1rdPtGHchfAXICvIBkR4yWKbqolePM7Hg3C7Gvqps/MFLCClDRiIalP\nNJr6x6JxAgMBAAECggEABDw7tQIFrZsWJIkSNsO0lDQq/nIiHv1d8Y1Sf30FmDhm\n9HZunHlfu3c1sLzaHH85zaxpXLxH/BvzmMl13m6KpzELXBgJahJxjsO8zcpyZ6HD\nHn7iZSKEEzeOOXdHI977HUU7ha6ioMRsamjpuG+vCAk4wddgRk30+hdJmW0Eark7\nyE2EGKn2nWZONrQWpAu3Zwi7dbgebXDGSxLTN+YK+XuDYbDTAOc3uJA7SIQOJhZZ\nv0SCPchAy5SiIwrgxVxUgyz6p3uifZxnRJc0jcvlf73+m54yP/XHNFikGrulHdoU\noJ9/j7BcZjWIVKEZxGimmUFQJvRlGFEXqb2iXyY+mQKBgQD+M6pMBaSGo9cMo5w1\nWt7GeZKxzP7eMv3nvZOXV5GphX9S9FHapIU9Iv4jKeSQEvZeBplKwTmQWF/tWilP\nglnBR7u0mcy/GX66gt0zN0EoyYMyUgMvNytnKghN1KsHD3gIb9j5WSJi9RxdwB8A\nRgMIX7OamE1QY1GgIvSBK39SGQKBgQDyx8+0/uwahinh9gMWXMAKTwvZUV0Wjh3q\nlsK5MpWI2X5Zax6bZoE3TJCqu9BxouNgYjVHZOuP15fvZtkXjzpKKTm1NQ5NnTUI\n4gLk7uisRdUVpcNZIMWcaOTmM2wgb0RY5YcraA0PRXAnwx3SB6f5XDkyF9jDpyr6\ngezdL51OGQKBgHyJ+2j7aru8EWPT1HgfaP18Gm6ZrFRYTyT2MBT5hhezm8mcgW3J\nJK3rMu8vWxdq8uDmArwpJnadlYHHpm2Zwzd6WXAF2dXWO8xMyOqKq5W8BFbm70B2\nmwEUCrV298OhxID9qyOek8Y/qAIWWhncMygrGucmrtovjpISDhAqq1ohAoGBAOcS\nFjcGimGUYDiYlceq73zgTz6/mgHlscOdSihKZNijaQZiVfdCUKn5TZeyumntxsvt\nrRgOjcWSRSGumeE6iRgctLgrjzl/7wJNWsPaP8n3jR/VbWBfOLXtgC85sigMvth9\nXXGKzyNBy8WMh81nTBCiHi33VHCjotxa3L6ImwfBAoGBALAfp0y5ZNa1oVHgxLBJ\n4YUTJdg9OlxXj1QslQ2dLHQhUgTfDl4oSuqSxo/VU11ONV2GIGTWyD3gKRXsbei1\noCPTso8GnqTopNjbZcw239SweIFKH7i9M10kUd6C2eKZNQvnpGPjmxcXkJYsOiDT\nS3XaRHU/f/DvloFzYyitq888\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@biyoves-4b051.iam.gserviceaccount.com",
    "client_id": "111424347071761486373",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40biyoves-4b051.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com",
}


class FirebaseManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.db = None
            self._initialized = True
            self._temp_cred_file = None
            self._executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="firebase")
            self.FIRESTORE_TIMEOUT = 10
            self.FIRESTORE_MAX_RETRIES = 3
            self.FIRESTORE_RETRY_DELAY = 0.5

    def initialize(self):
        """Public initializer to make sure Firebase is ready."""
        self._ensure_initialized()

    def _ensure_initialized(self):
        if self.db is None:
            self._initialize_firebase()

    def _initialize_firebase(self):
        try:
            if firebase_admin._apps:
                self.db = firestore.client()
                return

            possible_paths = [
                BASE_DIR / "firebase_service_account.json",
                BASE_DIR / "app" / "config" / "firebase_service_account.json",
            ]
            service_account_path = next((p for p in possible_paths if p.exists()), None)

            if service_account_path:
                cred = credentials.Certificate(str(service_account_path))
            else:
                embedded_dict = SERVICE_ACCOUNT_JSON_DICT
                if not embedded_dict:
                    raise FileNotFoundError("Firebase credentials bulunamadı!")
                json_str = json.dumps(embedded_dict)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    delete=False,
                    encoding="utf-8",
                ) as tf:
                    tf.write(json_str)
                    self._temp_cred_file = tf.name
                cred = credentials.Certificate(self._temp_cred_file)

            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            logger.exception("Firebase initialization hatası: %s", e)
            raise

    def _execute_with_retry(self, func, *args, **kwargs):
        last_exception = None
        for attempt in range(1, self.FIRESTORE_MAX_RETRIES + 1):
            future = self._executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.FIRESTORE_TIMEOUT)
            except FutureTimeoutError as exc:
                logger.warning(
                    "Firestore timeout (attempt %s/%s)",
                    attempt,
                    self.FIRESTORE_MAX_RETRIES,
                )
                last_exception = exc
            except Exception as exc:  # noqa: BLE001
                last_exception = exc
                if not self._is_retryable_error(exc):
                    break
                logger.warning(
                    "Firestore hatası, yeniden denenecek (attempt %s/%s): %s",
                    attempt,
                    self.FIRESTORE_MAX_RETRIES,
                    exc,
                )
            if attempt < self.FIRESTORE_MAX_RETRIES:
                threading.Event().wait(self.FIRESTORE_RETRY_DELAY)
        if last_exception:
            raise last_exception
        raise RuntimeError("Firestore işlemi başarısız oldu")

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        error_str = str(exc).lower()
        return any(keyword in error_str for keyword in ["timeout", "deadline", "unavailable", "connection"])

    def _hash_password(self, password):
        """Şifreyi hash'ler"""
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
        return password_hash.decode("utf-8")

    def _verify_password(self, password, hashed_password):
        """Şifreyi doğrular"""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception as e:
            logger.error("Şifre doğrulama hatası: %s", e)
            return False

    def create_user(self, email, password):
        """Yeni kullanıcı oluşturur"""
        self._ensure_initialized()
        try:
            user = auth.create_user(email=email, password=password, email_verified=False)
            password_hash = self._hash_password(password)

            def _create_user_doc():
                self.db.collection("users").document(user.uid).set(
                    {
                        "email": email,
                        "credits": 0,
                        "emailVerified": False,
                        "createdAt": datetime.now(timezone.utc),
                        "username": email.split("@")[0],
                        "password_hash": password_hash,
                    }
                )

            self._execute_with_retry(_create_user_doc)
            return user
        except auth.EmailAlreadyExistsError as e:
            logger.error("Email zaten kayıtlı: %s", email)
            raise Exception(f"{e}")
        except Exception as e:
            logger.exception("Kullanıcı oluşturma hatası: %s", e)
            raise

    def sign_in_user(self, email, password):
        """Kullanıcı girişi yapar"""
        self._ensure_initialized()
        try:
            # Kullanıcıyı email ile bul
            user = auth.get_user_by_email(email)
            
            # Firestore'dan kullanıcı bilgilerini al
            user_doc = self._execute_with_retry(lambda: self.db.collection("users").document(user.uid).get())
            if not user_doc.exists:
                raise Exception("Kullanıcı kaydı bulunamadı")
            
            user_data = user_doc.to_dict()
            stored_password_hash = user_data.get("password_hash")
            
            if not stored_password_hash:
                raise Exception("Güvenlik hatası: kullanıcı için şifre hash'i bulunamadı")
            
            # Şifre doğrulaması
            if not self._verify_password(password, stored_password_hash):
                raise Exception("Geçersiz kimlik bilgileri - şifre hatalı")
            
            # Email doğrulama kontrolü
            if not user_data.get("emailVerified", False):
                raise Exception("EMAIL_NOT_VERIFIED")
            
            return user
        except auth.UserNotFoundError:
            raise Exception("Kullanıcı bulunamadı")
        except Exception as e:
            logger.exception("Kullanıcı giriş hatası: %s", e)
            raise

    def generate_verification_code(self, length=6):
        """Doğrulama kodu oluşturur"""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    def create_verification_code(self, user_id, email):
        """Email doğrulama kodu oluşturur ve kaydeder"""
        self._ensure_initialized()
        try:
            code = self.generate_verification_code()
            verification_data = {
                "userId": user_id,
                "email": email,
                "code": code,
                "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=10),
                "used": False,
                "createdAt": datetime.now(timezone.utc),
            }
            
            doc_ref = self._execute_with_retry(lambda: self.db.collection("verification_codes").add(verification_data))
            return code, doc_ref[1].id
        except Exception as e:
            logger.exception("Doğrulama kodu oluşturma hatası: %s", e)
            raise

    def verify_code(self, code, email):
        """Email doğrulama kodunu doğrular"""
        self._ensure_initialized()
        try:
            codes_ref = self.db.collection("verification_codes")

            def _fetch_codes():
                query = codes_ref.where("code", "==", code).where("email", "==", email).where("used", "==", False)
                return list(query.stream())

            docs = self._execute_with_retry(_fetch_codes)
            
            if not docs:
                return False, "Geçersiz kod"
            
            doc = docs[0]
            doc_data = doc.to_dict()
            expires_at = doc_data["expiresAt"]
            if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                return False, "Kod süresi dolmuş"
            
            # Kodu kullanıldı olarak işaretle
            self._execute_with_retry(lambda: doc.reference.update({"used": True, "usedAt": datetime.now(timezone.utc)}))
            
            # Kullanıcının email'ini doğrula
            user_obj = auth.get_user_by_email(email)
            auth.update_user(user_obj.uid, email_verified=True)
            self._execute_with_retry(
                lambda: self.db.collection("users").document(user_obj.uid).update(
                    {"emailVerified": True, "verifiedAt": datetime.now(timezone.utc)}
                )
            )
            
            # Email doğrulama bonusu olarak 3 kredi ekle
            success, message, _ = self.add_credits_to_user(user_obj.uid, 3, reason="Email doğrulama bonusu")
            if not success:
                logger.warning("Kredi eklenemedi: %s", message)
            
            return True, "Email başarıyla doğrulandı"
        except Exception as e:
            logger.exception("Kod doğrulama hatası: %s", e)
            return False, str(e)

    def add_credits_to_user(self, user_id, credits, reason=""):
        """Kullanıcıya kredi ekler"""
        self._ensure_initialized()
        try:
            user_ref = self.db.collection("users").document(user_id)

            def _apply_credit():
                user_doc = user_ref.get()
                if user_doc.exists:
                    current_credits = user_doc.to_dict().get("credits", 0)
                    new_total = current_credits + credits
                    user_ref.update({"credits": new_total, "lastCreditUpdate": datetime.now(timezone.utc)})
                    return True, new_total, False
                user_ref.set(
                    {
                        "credits": credits,
                        "createdAt": datetime.now(timezone.utc),
                        "lastCreditUpdate": datetime.now(timezone.utc),
                    }
                )
                return True, credits, True

            success, new_total, created = self._execute_with_retry(_apply_credit)
            if success and reason:
                def _add_history():
                    self.db.collection("credit_history").add(
                        {
                            "userId": user_id,
                            "amount": credits,
                            "type": "add",
                            "reason": reason,
                            "timestamp": datetime.now(timezone.utc),
                        }
                    )
                self._execute_with_retry(_add_history)
            message = f"Yeni kullanıcı oluşturuldu, {credits} kredi eklendi" if created else f"{credits} kredi eklendi"
            return True, message, new_total
        except Exception as e:
            logger.exception("Kredi ekleme hatası: %s", e)
            return False, str(e), self.get_user_credits(user_id)

    def create_password_reset_code(self, email):
        """Şifre sıfırlama kodu oluşturur"""
        self._ensure_initialized()
        try:
            try:
                user = auth.get_user_by_email(email)
            except auth.UserNotFoundError as e:
                raise Exception(f"{e}")
            
            reset_code = self.generate_verification_code(length=8)
            reset_data = {
                "userId": user.uid,
                "email": email,
                "code": reset_code,
                "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=15),
                "used": False,
                "createdAt": datetime.now(timezone.utc),
                "type": "password_reset",
            }
            
            doc_ref = self._execute_with_retry(lambda: self.db.collection("password_reset_codes").add(reset_data))
            return reset_code, doc_ref[1].id
        except Exception as e:
            logger.exception("Şifre sıfırlama kodu oluşturma hatası: %s", e)
            raise

    def verify_password_reset_code(self, code, email):
        """Şifre sıfırlama kodunu doğrular"""
        self._ensure_initialized()
        try:
            codes_ref = self.db.collection("password_reset_codes")

            def _fetch():
                query = codes_ref.where("code", "==", code).where("email", "==", email).where("used", "==", False)
                return list(query.stream())

            docs = self._execute_with_retry(_fetch)
            
            if not docs:
                return False, "Geçersiz kod"
            
            doc = docs[0]
            doc_data = doc.to_dict()
            expires_at = doc_data["expiresAt"]
            if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                return False, "Kod süresi dolmuş"
            
            # Kodu kullanıldı olarak işaretle
            self._execute_with_retry(lambda: doc.reference.update({"used": True, "verifiedAt": datetime.now(timezone.utc)}))
            return True, "Kod doğrulandı"
        except Exception as e:
            logger.exception("Şifre sıfırlama kodu doğrulama hatası: %s", e)
            return False, str(e)

    def reset_user_password(self, email, new_password, reset_code):
        """Kullanıcı şifresini sıfırlar"""
        self._ensure_initialized()
        try:
            user = auth.get_user_by_email(email)
            auth.update_user(user.uid, password=new_password)
            password_hash = self._hash_password(new_password)
            
            self._execute_with_retry(
                lambda: self.db.collection("users").document(user.uid).update(
                    {"password_hash": password_hash, "passwordResetAt": datetime.now(timezone.utc)}
                )
            )
            return True, "Şifre başarıyla sıfırlandı"
        except Exception as e:
            logger.exception("Şifre sıfırlama hatası: %s", e)
            return False, str(e)


    def get_user_credits(self, user_id):
        """Kullanıcının kredi sayısını döndürür"""
        self._ensure_initialized()
        try:
            user_doc = self._execute_with_retry(lambda: self.db.collection("users").document(user_id).get())
            if user_doc.exists:
                return user_doc.to_dict().get("credits", 0)
            return 0
        except Exception as e:
            logger.exception("Kredi okuma hatası: %s", e)
            return 0

    def use_credits(self, user_id, amount=1):
        """Belirtilen miktarda kredi düşer"""
        self._ensure_initialized()
        if amount <= 0:
            return False, self.get_user_credits(user_id), "Geçersiz kredi miktarı"

        try:
            user_ref = self.db.collection("users").document(user_id)

            @firestore.transactional
            def update_in_transaction(transaction: Transaction):
                snapshot = user_ref.get(transaction=transaction)
                if not snapshot.exists:
                    return False, 0, "Kullanıcı bulunamadı"

                current_credits = snapshot.to_dict().get("credits", 0)
                if current_credits < amount:
                    return False, current_credits, "Yetersiz kredi"

                new_credits = current_credits - amount
                transaction.update(
                    user_ref,
                    {"credits": new_credits, "lastCreditUse": datetime.now(timezone.utc)}
                )
                return True, new_credits, ""

            transaction = self.db.transaction()
            success, new_credits, message = update_in_transaction(transaction)
            if success:
                try:
                    self._execute_with_retry(
                        lambda: self.db.collection("credit_history").add(
                            {
                                "userId": user_id,
                                "amount": -amount,
                                "type": "use",
                                "reason": "Hak kullanımı",
                                "timestamp": datetime.now(timezone.utc),
                            }
                        )
                    )
                except Exception as history_error:
                    logger.warning("Kredi geçmişi ekleme hatası: %s", history_error)
                return True, new_credits, ""
            return False, new_credits, message
        except Exception as e:
            logger.exception("Kredi kullanma hatası: %s", e)
            return False, self.get_user_credits(user_id), str(e)

    def use_credit(self, user_id):
        return self.use_credits(user_id, 1)

    def verify_credit_code(self, code, user_id):
        """Kredi kodunu doğrular ve kullanıcıya hak ekler"""
        self._ensure_initialized()
        try:
            if not code:
                return False, "Kod gerekli", 0
            codes_ref = self.db.collection("credit_codes")

            def _fetch_codes():
                query = codes_ref.where("code", "==", code.upper()).where("used", "==", False)
                return list(query.stream())

            docs = self._execute_with_retry(_fetch_codes)
            if not docs:
                return False, "Geçersiz kod", 0

            doc = docs[0]
            doc_data = doc.to_dict()
            expires_at = doc_data.get("expiresAt")
            if expires_at:
                if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_at:
                    return False, "Kod süresi dolmuş", 0

            self._execute_with_retry(
                lambda: doc.reference.update({"used": True, "usedBy": user_id, "usedAt": datetime.now(timezone.utc)})
            )
            credits_to_add = doc_data.get("credits", 0)
            success, message, _ = self.add_credits_to_user(user_id, credits_to_add, reason=f"Kod: {code.upper()}")
            if not success:
                return False, "Kredi eklenirken hata oluştu", 0
            return True, "Kod başarıyla kullanıldı", credits_to_add
        except Exception as e:
            logger.exception("Kredi kodu doğrulama hatası: %s", e)
            return False, str(e), 0


firebase_manager = FirebaseManager()


# Tema sınıfı - PySide6 için
class ModernTheme:
    # Renkler
    PRIMARY = "#1a73e8"
    PRIMARY_HOVER = "#1765cc"
    SUCCESS = "#34a853"
    SUCCESS_HOVER = "#2d8e47"
    DANGER = "#ea4335"
    DANGER_HOVER = "#c5221f"
    WARNING = "#fbbc04"
    INFO = "#4285f4"
    BACKGROUND = "#ffffff"
    BACKGROUND_SECONDARY = "#f8f9fa"
    BACKGROUND_TERTIARY = "#f5f5f5"
    TEXT_PRIMARY = "#202124"
    TEXT_SECONDARY = "#5f6368"
    TEXT_TERTIARY = "#80868b"
    BORDER = "#dadce0"
    BORDER_LIGHT = "#e8eaed"
    
    # Font boyutları
    FONT_SIZE_DISPLAY = 36
    FONT_SIZE_SUBHEADING = 18
    FONT_SIZE_BODY = 14
    FONT_SIZE_BODY_SMALL = 13
    
    # Spacing
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    SPACING_XXL = 48
    
    # Border radius
    RADIUS_MD = 8
    RADIUS_LG = 12
    
    # Buton yükseklikleri
    BUTTON_HEIGHT_SM = 32
    BUTTON_HEIGHT_MD = 40
    BUTTON_HEIGHT_LG = 48
    BUTTON_MIN_WIDTH = 120
    
    # Card ayarları
    CARD_PADDING = 24
    CARD_BORDER_WIDTH = 1
    CARD_BORDER_COLOR = BORDER_LIGHT
    CARD_BACKGROUND = BACKGROUND
    
    # Pencere ayarları
    WINDOW_MIN_WIDTH = 880
    WINDOW_MIN_HEIGHT = 580
    SHOP_URL = "https://biyoves.com.tr"


modern_theme = ModernTheme()
