from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/efootball"
    APP_ENV: str = "production"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email verification (migration 023). Ships dark: the flow only
    # engages when EMAIL_VERIFICATION_ENABLED is set in the deployment
    # environment, so code can deploy before the mail provider's
    # credentials land. MAIL_PROVIDER: "console" (in-process outbox,
    # for tests/dev), "smtp" (any SMTP relay — Brevo, Gmail, ...) or
    # "resend" (Resend HTTPS API; needs RESEND_API_KEY).
    EMAIL_VERIFICATION_ENABLED: bool = False
    MAIL_PROVIDER: str = "console"
    MAIL_FROM: str = "eFootball Arena <no-reply@efootballarena.app>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    RESEND_API_KEY: str = ""


settings = Settings()
