from __future__ import annotations

import json
from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    upstream_base_url: str = Field(default="https://api.openai.com")
    upstream_responses_path: str = Field(default="/v1/responses")
    upstream_api_key: str = Field(default="")
    upstream_api_key_header: str = Field(default="Authorization")
    pass_through_auth: bool = Field(default=True)
    request_timeout: float = Field(default=30.0)
    log_level: str = Field(default="INFO")
    model_map: str = Field(default="{}")

    def resolved_model_map(self) -> Dict[str, str]:
        try:
            value = json.loads(self.model_map)
            if isinstance(value, dict):
                return {str(k): str(v) for k, v in value.items()}
        except json.JSONDecodeError:
            return {}
        return {}

    def auth_headers(self) -> Dict[str, str]:
        if not self.upstream_api_key:
            return {}
        if self.upstream_api_key_header.lower() == "authorization":
            return {"Authorization": f"Bearer {self.upstream_api_key}"}
        return {self.upstream_api_key_header: self.upstream_api_key}

    def upstream_url_for(self, path: str) -> str:
        base = self.upstream_base_url.rstrip("/")
        cleaned = path.strip()
        if not cleaned:
            return base
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned
        if base.endswith("/v1") and cleaned.startswith("/v1/"):
            cleaned = cleaned[len("/v1"):]
        return base + cleaned

    def upstream_responses_url(self) -> str:
        return self.upstream_url_for(self.upstream_responses_path)

    def upstream_models_url(self) -> str:
        return self.upstream_url_for("/v1/models")


settings = Settings()
