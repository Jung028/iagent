import hashlib
import hmac


class WhatsAppWebhookVerifier:
    """Verifies incoming WhatsApp webhook requests from Meta.

    Two verification modes:
    1. Hub challenge — GET request from Meta to confirm our endpoint (one-time setup)
    2. Signature   — X-Hub-Signature-256 header on every POST to prove authenticity
    """

    def __init__(self, verify_token: str, app_secret: str) -> None:
        self._verify_token = verify_token
        self._app_secret = app_secret

    def verify_hub_challenge(self, mode: str, token: str, challenge: str) -> str | None:
        """Return the challenge string if token matches, else None.

        Called by GET /webhooks/whatsapp during Meta's one-time endpoint verification.
        """
        if mode == "subscribe" and token == self._verify_token:
            return challenge
        return None

    def verify_signature(self, payload_bytes: bytes, signature_header: str) -> bool:
        """Return True if the X-Hub-Signature-256 header matches the payload HMAC.

        Prevents spoofed webhook calls from non-Meta sources.
        """
        # TODO: make sure to read raw bytes from request before any JSON parsing
        if not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(
            self._app_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        received = signature_header.removeprefix("sha256=")
        return hmac.compare_digest(expected, received)
