# In Python, imports work similarly to Java's import statements.
# "from X import Y" means: go into module X and bring Y into this file's scope.
# This is like Java's "import com.example.X;" but more selective.
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
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    # If APP_ENV is missing from environment, the app crashes at startup with a clear error.
    anthropic_api_key: str

    # Redis connection string. Has a default so it's optional in .env.
    redis_url: str = "redis://localhost:6379/0"

    # Java backend service base URLs — all REQUIRED (no defaults).
    iaccount_base_url: str
    ibusiness_base_url: str


# Create a single shared instance of Settings.
# In Java this would be a Singleton: Settings.getInstance()
# The "# type: ignore[call-arg]" comment suppresses a mypy type-checker warning —
# mypy doesn't know pydantic fills the required fields from env vars automatically.
settings = Settings()  # type: ignore[call-arg]
