"""
auth_manager.py
Authentication and User Management Module
Supports sign-up, sign-in, session tokens, and instant demo login.
"""

import os
import json
import uuid
import hashlib
import time
from typing import Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

class AuthManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.users: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._load_users()

    def _load_users(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except Exception:
                self.users = {}
        
        # Seed default demo account if not exists
        if "analyst@company.com" not in self.users:
            self.create_user(
                email="analyst@company.com",
                name="Shivani (Senior Analyst)",
                password="demo123",
                role="Senior Business Analyst"
            )

    def _save_users(self):
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"[!] Warning: Could not save users: {e}")

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

    def create_user(self, email: str, name: str, password: str, role: str = "Business Analyst") -> Dict[str, Any]:
        email_clean = email.strip().lower()
        if email_clean in self.users:
            raise ValueError("An account with this email already exists.")
        
        salt = uuid.uuid4().hex
        pwd_hash = self._hash_password(password, salt)
        user = {
            "id": str(uuid.uuid4()),
            "email": email_clean,
            "name": name.strip(),
            "role": role,
            "salt": salt,
            "pwd_hash": pwd_hash,
            "created_at": time.time()
        }
        self.users[email_clean] = user
        self._save_users()
        return self._sanitize_user(user)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        email_clean = email.strip().lower()
        user = self.users.get(email_clean)
        if not user:
            return None
        
        test_hash = self._hash_password(password, user["salt"])
        if test_hash == user["pwd_hash"]:
            return self._sanitize_user(user)
        return None

    def create_session(self, user: Dict[str, Any]) -> str:
        token = str(uuid.uuid4())
        self.sessions[token] = {
            "user": user,
            "created_at": time.time(),
            "expires_at": time.time() + (86400 * 7) # 7 days
        }
        return token

    def get_user_from_session(self, token: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(token)
        if not session:
            return None
        if time.time() > session["expires_at"]:
            del self.sessions[token]
            return None
        return session["user"]

    def revoke_session(self, token: str):
        if token in self.sessions:
            del self.sessions[token]

    def _sanitize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role", "Business Analyst")
        }

auth_manager = AuthManager()
