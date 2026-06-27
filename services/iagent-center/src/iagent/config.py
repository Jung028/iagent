# In Python, imports work similarly to Java's import statements.
# "from X import Y" means: go into module X and bring Y into this file's scope.
# This is like Java's "import com.example.X;" but more selective.
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Python classes are defined with the "class" keyword, just like Java.
# "class Settings(BaseSettings)" means Settings INHERITS from BaseSettings.
# In Java this would be: public class Settings extends BaseSettings { }
#
# BaseSettings (from the pydantic-settings library) is a special base class that
# automatically reads environment variables and .env files. It maps env var names
# to the fields you declare below.
class Settings(BaseSettings):

    # model_config is a class-level variable (like a static field in Java).
    # SettingsConfigDict() tells pydantic WHERE to read settings from:
    #   - env_file=".env"  → also read from a .env file on disk
    #   - extra="ignore"   → silently ignore env vars that aren't declared as fields below
    # Resolve .env relative to this file so it works regardless of which
    # directory uvicorn / the test runner is launched from.
    _env_file = Path(__file__).parent.parent.parent / ".env"
    model_config = SettingsConfigDict(env_file=str(_env_file), extra="ignore")

    # --- Field declarations ---
    # In Python (with Pydantic), you declare fields as:
    #   field_name: type = default_value
    # If there is NO default value, the field is REQUIRED (like @NonNull in Java).
    # Pydantic reads the matching environment variable (uppercased) at startup.
    # e.g. "app_env" reads the env var "APP_ENV".

    # Application settings
    app_env: str = "development"   # str is Python's String. Default = "development"
    app_port: int = 8000           # int is Python's int (no Integer wrapper class needed)
    log_level: str = "info"

    # Anthropic API key — NO default value = REQUIRED.
    # Get yours from https://console.anthropic.com/settings/keys
    anthropic_api_key: str

    # Redis connection string. Has a default so it's optional in .env.
    redis_url: str = "redis://localhost:6379/0"

    # Java backend service base URLs — all REQUIRED (no defaults).
    iaccount_base_url: str
    ibusiness_base_url: str
    iuser_base_url: str

    # Tracely — the unified system graph the agent queries to answer
    # architecture / dependency / impact questions via traversal.
    tracely_base_url: str = "http://localhost:3000"

    # JWT Authentication settings (Asymmetric RSA)
    # jwt_public_key_path: Path to the .pem public key file.
    # In local dev, we might use a dummy path or allow it to be optional.
    jwt_public_key_path: str = "public_key.pem"
    jwt_algorithm: str = "RS256"

    # RAG memory service — both optional; server starts (without RAG) if either is missing.
    # DATABASE_URL must use SQLAlchemy format: postgresql://user@host:port/dbname
    # pgvector extension must be installed in the target database.
    database_url: Optional[str] = None
    openai_api_key: Optional[str] = None

    # CORS — comma-separated list of allowed origins.
    cors_origins: str = "http://localhost:8089,http://localhost:5173,http://localhost:3000"

    # WhatsApp Cloud API — all optional so the server starts without WhatsApp configured.
    # Get these from Meta Developer Console → WhatsApp → API Setup.
    whatsapp_phone_number_id: str = ""     # e.g. "123456789012345"
    whatsapp_access_token: str = ""        # temporary or permanent system user token
    whatsapp_verify_token: str = "iagent" # any string you choose — used for hub challenge
    whatsapp_app_secret: str = ""          # used to verify X-Hub-Signature-256 on incoming webhooks


# Create a single shared instance of Settings.
# In Java this would be a Singleton: Settings.getInstance()
# The "# type: ignore[call-arg]" comment suppresses a mypy type-checker warning —
# mypy doesn't know pydantic fills the required fields from env vars automatically.
settings = Settings()  # type: ignore[call-arg]
