from iagent.core.models.intent import Intent

# All queries, greetings, and conversational messages → ReadAgent (Claude tool-use loop).
READ_INTENTS: frozenset[Intent] = frozenset({Intent.READ})

# Money movement → deterministic handlers with confirmation gate.
WRITE_INTENTS: frozenset[Intent] = frozenset({Intent.TRANSFER, Intent.TOP_UP})
