import secrets
from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel


class AgentKey(BaseModel):
    key: str
    instance_id: str
    created_at: datetime
    is_active: bool = True


class AuthManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.agent_keys: dict[str, AgentKey] = {}

    def generate_agent_key(self, instance_id: str) -> str:
        """Generate an API key for an agent"""
        key = secrets.token_urlsafe(32)

        self.agent_keys[key] = AgentKey(
            key=key,
            instance_id=instance_id,
            created_at=datetime.now(UTC),
        )
        return key

    def verify_agent_key(self, key: str) -> Optional[str]:
        """Verify an agent's API key, returns instance_id if valid"""
        agent_key = self.agent_keys.get(key)
        if not agent_key or not agent_key.is_active:
            return None
        return agent_key.instance_id
