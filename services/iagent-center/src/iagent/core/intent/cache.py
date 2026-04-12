import hashlib  # Python's built-in cryptography library — like java.security.MessageDigest
import json      # Python's built-in JSON library — like Jackson's ObjectMapper

from iagent.core.intent.models import Intent, IntentResult

# How long (in seconds) to cache an intent classification result in Redis.
# 300 seconds = 5 minutes. Declared as a module-level constant (like Java's static final).
CACHE_TTL_SECONDS = 300


def _cache_key(user_id: str, message: str) -> str:
    """Build a Redis key for a given user + message combination.

    The leading underscore in "_cache_key" is a Python convention meaning
    "this is a private/internal function" — similar to Java's private modifier,
    but Python doesn't enforce it; it's just a signal to other developers.

    We hash the message so the Redis key is a fixed length regardless of how
    long the user's message is. Same logic as a HashMap key in Java.
    """

    # Normalise the message before hashing so "What's my balance?" and
    # "what's my balance?" produce the SAME cache key.
    # .strip() removes leading/trailing whitespace. .lower() lowercases everything.
    # In Java: message.strip().toLowerCase()
    normalized = message.strip().lower()

    # Build the string to hash: "user-123:what's my balance?"
    # f"..." is an f-string — Python's string interpolation (like Java's String.format or
    # the + concatenation operator, but cleaner).
    # f"{user_id}:{normalized}" produces: "user-123:what's my balance?"
    #
    # .encode() converts the Python string to bytes (UTF-8 by default).
    # hashlib.sha256(...).hexdigest() produces a 64-character hex string.
    # In Java: MessageDigest.getInstance("SHA-256").digest(input.getBytes())
    digest = hashlib.sha256(f"{user_id}:{normalized}".encode()).hexdigest()

    # Prefix with "intent:" so this key namespace is distinct from any other
    # Redis keys the system might use in the future.
    return f"intent:{digest}"


async def get_cached(redis, user_id: str, message: str) -> IntentResult | None:
    """Try to retrieve a previously cached intent classification from Redis.

    Returns an IntentResult if found, or None if not cached (cache miss).

    "IntentResult | None" is Python 3.10+ syntax for Optional<IntentResult> in Java.
    The "|" here means "OR" — the return value is either an IntentResult or None (null).
    In older Python you'd write: Optional[IntentResult]
    """

    # Build the cache key for this user+message pair.
    key = _cache_key(user_id, message)

    # "await redis.get(key)" calls Redis GET asynchronously.
    # Returns the stored bytes if the key exists, or None if it doesn't.
    raw = await redis.get(key)

    # "if raw is None" checks for None (Python's null).
    # "is None" is preferred over "== None" in Python for null checks.
    # In Java: if (raw == null) return null;
    if raw is None:
        return None

    # json.loads() deserialises a JSON string (or bytes) into a Python dict.
    # In Java: objectMapper.readValue(raw, Map.class)
    data = json.loads(raw)

    # Build and return an IntentResult from the cached data.
    # Intent(data["intent"]) converts the string "balance_inquiry" back into the Intent enum.
    # In Java: Intent.valueOf(data.get("intent"))
    result = IntentResult(
        intent=Intent(data["intent"]),
        confidence=data["confidence"],
        # .get("entities", {}) returns the value for key "entities", or {} if missing.
        # In Java: (Map) data.getOrDefault("entities", new HashMap<>())
        entities=data.get("entities", {}),
        cache_hit=True,   # Mark this result as coming from cache, not the LLM
    )
    return result


async def set_cached(redis, user_id: str, message: str, result: IntentResult) -> None:
    """Store an intent classification result in Redis with a 5-minute TTL.

    "-> None" means this function returns nothing (like Java's void).
    """

    key = _cache_key(user_id, message)

    # Build a dict of only the fields we want to store (we don't store cache_hit).
    # Then json.dumps() serialises it to a JSON string.
    # ".value" on a StrEnum gives the raw string ("balance_inquiry" not "Intent.BALANCE_INQUIRY").
    # In Java: objectMapper.writeValueAsString(map)
    payload = json.dumps(
        {
            "intent": result.intent.value,
            "confidence": result.confidence,
            "entities": result.entities,
        }
    )

    # redis.setex(key, ttl_seconds, value) stores the value with an automatic expiry.
    # After 300 seconds Redis deletes this key automatically.
    # In Java: redisTemplate.opsForValue().set(key, payload, 300, TimeUnit.SECONDS)
    await redis.setex(key, CACHE_TTL_SECONDS, payload)
