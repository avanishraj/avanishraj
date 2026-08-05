import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    
    # Firebase
    FIREBASE_CRED_PATH: str = os.getenv("FIREBASE_CRED_PATH", "")
    FIREBASE_STORAGE_BUCKET: str = os.getenv("FIREBASE_STORAGE_BUCKET", "")

    # ── Notification Provider ──────────────────────────────────────────────────
    # "fcm"       → FCMProvider via NotificationService (default, production)
    # "onesignal" → @deprecated OneSignalProvider (emergency rollback only)
    CRM_PROVIDER: str = os.getenv("CRM_PROVIDER", "fcm")

    # OneSignal — @deprecated, kept for emergency rollback only.
    # Remove after FCM migration is verified stable.
    ONESIGNAL_APP_ID: str = os.getenv("ONESIGNAL_APP_ID", "36ccefda-30ba-45c5-b44a-93e2658a48aa")
    ONESIGNAL_REST_API_KEY: str = os.getenv("ONESIGNAL_REST_API_KEY", "")


    # Resend
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    OTP_SENDER_EMAIL: str = os.getenv("OTP_SENDER_EMAIL", "noreply@smritiq.com")
    
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "memory-vault-minilm")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    
    # =====================================================================
    # EMBEDDINGS
    # =====================================================================
    # OpenAI text-embedding-3-small with custom dimensions for Pinecone compatibility.
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    # =====================================================================
    # AI MODEL ROUTING — DYNAMIC ARCHITECTURE
    # =====================================================================
    # CLASSIFIER_LLM_MODEL: Ultra-cheap, fast model for routing/classification.
    #   Used for: chat routing, query intent, query rewriting.
    #   gpt-5-nano → $0.05/1M input — 50% cheaper than gpt-4.1-nano, same accuracy.
    CLASSIFIER_LLM_MODEL: str = os.getenv("CLASSIFIER_LLM_MODEL", "gpt-5-nano")

    # FAST_LLM_MODEL: Good quality model for FACTUAL and EXPLORATORY queries.
    #   Used for: final answer generation when no deep EQ needed.
    #   gpt-5-mini → supports temperature + max_tokens.
    FAST_LLM_MODEL: str = os.getenv("FAST_LLM_MODEL", "gpt-5-mini")

    # PREMIUM_LLM_MODEL: High-EQ model for CONVERSATIONAL and emotional queries.
    #   Used for: warmth, empathy, relationship analysis, casual conversation.
    #   Replaces the personality-refinement second pass — generates warm output in 1 call.
    #   gpt-5.6-luna → premium emotional intelligence, single call replaces 2×mini.
    PREMIUM_LLM_MODEL: str = os.getenv("PREMIUM_LLM_MODEL", "gpt-5.6-luna")

    # LLM_MODEL: Reasoning model. Reserved for INTROSPECTIVE queries and life summaries.
    #   gpt-5-nano → optimized with effort=low and token budget=3000 for cost/speed balance.
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-5-nano")
    LLM_TEMPERATURE: float = 0.7

    # ENRICHMENT_MODEL: Structured JSON extraction (emotions, entities, temporal).
    #   Used for: enrichment_service, translation_enrichment_service.
    #   gpt-5.4-nano → better JSON schema adherence, cheaper output than gpt-4.1-mini.
    ENRICHMENT_MODEL: str = os.getenv("ENRICHMENT_MODEL", "gpt-5.4-nano")

    # TRANSLATION_MODEL: Language detection and translation.
    #   Used for: translation_service (all 3 stages).
    #   gpt-4o-mini → industry standard for fast, cheap, accurate translation.
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "gpt-4o-mini")

    # EXPANSION_MODEL: Query variant generation and HyDE diary synthesis.
    #   Used for: query_expansion_service.
    #   gpt-5.4-nano → richer semantic diversity than gpt-4.1-nano, better recall.
    EXPANSION_MODEL: str = os.getenv("EXPANSION_MODEL", "gpt-5.4-nano")
    
    # Token Limits
    MAX_SESSION_INPUT_TOKENS: int = 3000  # Approx limit for query + history before forcing reset
    MAX_SINGLE_MSG_TOKENS: int = 1000     # Limit for a single user message
    MAX_CONTEXT_TOKENS: int = 500         # Max tokens for RAG context chunks (approx 2000 chars)

    BM25_WEIGHT: float = 0.4
    SEMANTIC_WEIGHT: float = 0.6
    TOP_TAGS_COUNT: int = 3
    MAX_MEDIA_ASSETS_PER_MEMORY: int = int(os.getenv("MAX_MEDIA_ASSETS_PER_MEMORY", "15"))

    # =====================================================================
    # PHASE 1 — CHUNK-LEVEL PERSONAL MEMORY INDEXING
    # =====================================================================

    # Gates write-time chunking in memory_service create/update.
    # Set True to start indexing new/updated memories as chunks.
    CHUNK_INDEXING_ENABLED: bool = bool(int(os.getenv("CHUNK_INDEXING_ENABLED", "1")))

    # Gates chunk-based retrieval in retrieval_service.
    # Keep False until a meaningful % of the user's memories are chunk-indexed
    # (see CHUNK_COVERAGE_THRESHOLD). Flip True once backfill is underway.
    CHUNK_RETRIEVAL_ENABLED: bool = bool(int(os.getenv("CHUNK_RETRIEVAL_ENABLED", "0")))
    PERSONALITY_LAYER_ENABLED: bool = bool(int(os.getenv("PERSONALITY_LAYER_ENABLED", "1")))


    # When a client opens a memory that is not yet chunk-indexed, trigger reindex.
    # Drives gradual coverage without a separate migration job.
    CHUNK_BACKFILL_ON_READ: bool = bool(int(os.getenv("CHUNK_BACKFILL_ON_READ", "1")))

    # Fraction of user's memories that must be chunk-indexed before switching
    # retrieval to chunk mode. Used as a guard in retrieval_service.
    CHUNK_COVERAGE_THRESHOLD: float = float(os.getenv("CHUNK_COVERAGE_THRESHOLD", "0.80"))

    # Chunk window size in approximate tokens (1 token ≈ 4 chars).
    # 140 tokens ≈ 560 chars — dense enough for personal memory prose.
    CHUNK_SIZE_TOKENS: int = int(os.getenv("CHUNK_SIZE_TOKENS", "140"))

    # Overlap between consecutive chunks in approximate tokens.
    # Ensures sentences on chunk boundaries are captured by at least two chunks.
    CHUNK_OVERLAP_TOKENS: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "20"))

    # Whether to extract and store named entities (persons, places) in chunk metadata.
    # Set False if your threat model considers entity names sensitive (medical etc.).
    ENTITY_INDEX_ENABLED: bool = bool(int(os.getenv("ENTITY_INDEX_ENABLED", "1")))

    # =====================================================================
    # PHASE 2 — SESSION STATE + FOLLOW-UP ROUTING
    # =====================================================================

    # Enable the 4-label LLM classifier for ambiguous follow-up queries.
    # When False, the heuristic (pronoun/continuation) classifier is used only.
    # When True, ambiguous queries are sent to the LLM for classification.
    LLM_CLASSIFIER_ENABLED: bool = bool(int(os.getenv("LLM_CLASSIFIER_ENABLED", "0")))

    # Enable LLM-assisted standalone query rewrite for follow-up queries.
    # When False, the original query is sent as-is to retrieval.
    # When True, pronoun-heavy queries are rewritten using session labels before retrieval.
    FOLLOWUP_REWRITE_ENABLED: bool = bool(int(os.getenv("FOLLOWUP_REWRITE_ENABLED", "1")))

    # Pre-RAG LLM Router Agent.
    # When True:  a single LLM call classifies every message BEFORE retrieval.
    #             Handles all greetings/follow-ups naturally (no static dict needed).
    #             Generates greeting responses in the same call (no second LLM call).
    # When False: falls back to heuristic regex + static dict routing.
    CHAT_ROUTER_AGENT_ENABLED: bool = bool(int(os.getenv("CHAT_ROUTER_AGENT_ENABLED", "1")))

    # Session backend: "firestore" (default) or "redis" (future).
    # Swap to "redis" when concurrent active sessions exceed ~200-500.
    # No code changes needed beyond this flag + REDIS_URL below.
    SESSION_BACKEND: str = os.getenv("SESSION_BACKEND", "firestore")

    # Redis URL — leave blank until Redis is added.
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Inactivity window before session rag_state is treated as stale (soft TTL).
    SESSION_TTL_MINUTES: int = int(os.getenv("SESSION_TTL_MINUTES", "30"))
    
    TAG_CATEGORIES = [
        "Sentiment", "Activity", "Mood", "Goals", 
        "Weather", "People", "Location", "Time"
    ]
    
    PREDEFINED_TAGS = {
        "Sentiment": [
            "joy", "sadness", "gratitude", "love", "excitement",
            "peace", "anxiety", "hope", "nostalgia", "pride",
            "accomplishment", "regret", "wonder", "contentment"
        ],
        "Activity": [
            "work", "exercise", "travel", "reading", "meditation",
            "cooking", "learning", "creating", "meeting", "celebration",
            "project", "hobby", "shopping", "gaming", "writing"
        ],
        "Mood": [
            "happy", "calm", "energetic", "thoughtful", "inspired",
            "tired", "stressed", "motivated", "relaxed", "creative",
            "focused", "distracted", "overwhelmed", "confident"
        ],
        "Goals": [
            "health", "career", "relationships", "personal-growth",
            "financial", "learning", "fitness", "spiritual", "creative",
            "social", "adventure", "achievement"
        ],
        "Weather": [
            "sunny", "rainy", "cloudy", "stormy", "snowy",
            "windy", "foggy", "clear", "humid", "cold", "warm"
        ],
        "People": [
            "family", "friends", "partner", "colleagues", "children",
            "parents", "siblings", "mentor", "stranger", "alone",
            "group", "community"
        ],
        "Location": [
            "home", "office", "outdoors", "cafe", "gym",
            "beach", "mountains", "city", "countryside", "abroad",
            "restaurant", "park", "indoors"
        ],
        "Time": [
            "morning", "afternoon", "evening", "night", "weekend",
            "weekday", "holiday", "birthday", "anniversary", "season"
        ]
    }
    
    @staticmethod
    def get_all_tags():
        all_tags = []
        for tags in Config.PREDEFINED_TAGS.values():
            all_tags.extend(tags)
        return all_tags

    # =====================================================================
    # ADMIN / ANALYTICS CONFIGURATION
    # =====================================================================

    # Comma-separated allowlists for founder/admin access.
    # Example:
    #   ADMIN_UIDS=uid1,uid2
    #   ADMIN_EMAILS=founder@example.com
    ADMIN_UIDS: str = os.getenv("ADMIN_UIDS", "")
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")

    @staticmethod
    def _split_csv(value: str) -> set:
        if not value:
            return set()
        return {v.strip() for v in value.split(",") if v.strip()}

    @property
    def admin_uids(self) -> set:
        return self._split_csv(self.ADMIN_UIDS)

    @property
    def admin_emails(self) -> set:
        return {e.lower() for e in self._split_csv(self.ADMIN_EMAILS)}

    # Subscriptions & limits
    PLAN_CACHE_TTL_MINUTES: int = 10

    # =====================================================================
    # PHASE 3 — PAYMENTS (RAZORPAY)
    # =====================================================================
    # Keep defaults as empty strings so local/dev can boot without keys.
    # Endpoints that require Razorpay will return a clear error if not configured.
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    
    # App info
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

config = Config()
