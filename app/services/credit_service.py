#!/usr/bin/env python3

"""Kredi işlemleri için yardımcı servis"""

from typing import Tuple

from app.config import firebase_manager


class CreditService:
    def use_credit(self, user_id: str) -> Tuple[bool, int, str]:
        return self.use_credits(user_id, 1)

    def use_credits(self, user_id: str, amount: int) -> Tuple[bool, int, str]:
        if not user_id or amount <= 0:
            return False, 0, "Geçersiz parametre"
        try:
            return firebase_manager.use_credits(user_id, amount)
        except Exception as exc:  # noqa: BLE001
            return False, 0, str(exc)

    def refund_credit(self, user_id: str, reason: str = "İşlem başarısız - iade") -> Tuple[bool, int, str]:
        if not user_id:
            return False, 0, "Kullanıcı bulunamadı"
        try:
            success, message, new_credits = firebase_manager.add_credits_to_user(
                user_id,
                1,
                reason=reason,
            )
            return success, new_credits, message
        except Exception as exc:  # noqa: BLE001
            return False, firebase_manager.get_user_credits(user_id), str(exc)


credit_service = CreditService()
