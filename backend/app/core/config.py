from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Unknown env vars are silently ignored — safe for a demo environment
        extra="ignore",
    )

    PROJECT_NAME: str = "MITRA"
    API_V1_PREFIX: str = "/api/v1"

    # SQLite for local demo. Swap for postgres+psycopg2 URL in production:
    #   postgresql://user:pass@host:5432/mitra
    DATABASE_URL: str = "sqlite:///./mitra_demo.db"

    # Echo SQL statements to stdout — set to True when debugging queries
    DATABASE_ECHO: bool = False

    # Allowed CORS origins for the Vite dev server
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """
        Accept CORS origins as either:
        - a JSON array string, or
        - a comma-separated string, or
        - a normal list
        """
        if value is None:
            return ["http://localhost:5173"]

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []

            if raw.startswith("["):
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]

            return [item.strip() for item in raw.split(",") if item.strip()]

        return value

    # --- Clinical thresholds (used by AlertService) ----------------------

    # Metres — distance from home before a wandering episode is flagged
    WANDERING_RADIUS_THRESHOLD_M: float = 200.0

    # Seconds — patient must remain outside radius before episode is confirmed
    WANDERING_DETECTION_WINDOW_S: int = 30

    # Minimum wearing hours per day to count the day as adherent
    ADHERENCE_MIN_HOURS: float = 6.0


settings = Settings()
