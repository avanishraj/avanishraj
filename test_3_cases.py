import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Optional, Any
from fastapi import BackgroundTasks, HTTPException
from app.config import config
from app.models.chat_model import ChatRequest, ChatResponse, MemorySource, MediaUrls, ChatMetadata, ChatSession, ChatMessage, ConversationTurn
from app.services.retrieval_service import retrieval_service
from app.services.reranking_service import reranking_service
from app.services.context_refinement_service import refinement_service
from app.services.summarization_service import summarization_service
from app.services.llm_service import llm_service
from app.services.translation_service import translation_service
from app.services.firebase_service import firebase_service
import re as _re
from app.services.query_routing_service import (
    QueryRoutingService,
    ROUTE_SMALLTALK, ROUTE_FOLLOWUP_SAME,
    ROUTE_FOLLOWUP_RETRIEVAL, ROUTE_NEW_QUERY,
)
# Compiled shared-only patterns for CONVERSATIONAL-bypass override
_SHARED_ONLY_COMPILED = [
    _re.compile(p, _re.IGNORECASE) for p in QueryRoutingService.SHARED_ONLY_PATTERNS
]
from app.services.session_state_service import session_state_service
from app.services.query_rewrite_service import query_rewrite_service
from app.services.chat_router_agent import (
    chat_router_agent,
    ROUTE_GREETING, ROUTE_FOLLOWUP_SAME as AGENT_FOLLOWUP_SAME,
    ROUTE_FOLLOWUP_RETRIEVAL as AGENT_FOLLOWUP_RETRIEVAL,
    ROUTE_MEMORY_QUERY,
    ROUTE_OUT_OF_SCOPE,
)
from app.utils.time import get_utc_now
import time
import uuid
import re
from app.services.query_intent_service import query_intent_service
from app.services.reasoning_agent_service import reasoning_agent_service

def normalize_query(query: str) -> str:
    q = re.sub(r'[^\w\s]', '', query.strip().lower())
    if re.match(r'^hi+$', q):
        return "hi"
    if re.match(r'^hey+$', q):
        return "hey"
    if re.match(r'^hello+$', q):
        return "hello"
    return q

_INSTANT_MAP = {
    "hi": "Hey there! 👋 I'm SmritiQ, your personal memory companion. Ask me anything about your memories — I'm all yours!",
    "hello": "Hello! 😊 I'm SmritiQ. Think of me as a friend who remembers everything you've ever shared. What's on your mind?",
    "hey": "Hey! I'm SmritiQ. What would you like to explore from your memories today?",
    "yo": "Yo! 😄 SmritiQ here. Ready to dig into your memories whenever you are!",
    "sup": "Not much! Just here, ready to help you recall anything from your past. What's up with you?",
    "hiya": "Hiya! 🌟 SmritiQ here. What would you like to remember today?",
    "ok": "Got it! Let me know whenever you want to explore your memories.",
    "okay": "Alright! Whenever you're ready, just ask me anything.",
    "thanks": "Of course! 😊 Always here when you want to remember something.",
    "thankyou": "Always happy to help! Come back anytime you want to revisit your memories.",
    "ty": "Anytime! 🙂",
    "thx": "No problem at all!",
    "bye": "Take care! 👋 Your memories will be right here waiting whenever you need them.",
    "goodbye": "Goodbye! Come back anytime you want to walk down memory lane.",
    "cool": "Nice! 😊 Let me know if you want to dig into anything.",
    "nice": "Great! Anything else you'd like to recall?",
    "awesome": "Love to hear it! Let me know if there's more you want to explore.",
}

RAW_HISTORY_WINDOW = 4
MIN_MSGS_FOR_TEXTRANK = 6

def extract_media_from_context(context_memories: List[Dict], used_memory_ids: List[str]) -> MediaUrls:
    """Extract, deduplicate, and cap media from context memory matches.

    ONLY processes personal memories (source != 'group').
    Group memories are skipped entirely because their media assets require
    per-share Content Keys (held only by the client) to decrypt — the backend
    can never produce readable media for them.

    For personal memories, uses a single-pass cited-track strategy:
    Only memories the LLM explicitly cited (via cited_docs) contribute media.
    This prevents unrelated personal memories from leaking into the response.

    Global caps prevent bloat:
        - Max MAX_IMAGES_PER_MEMORY images per memory
        - Max MAX_IMAGES_GLOBAL images total
        - Max MAX_AUDIOS_GLOBAL audios total
    """
    MAX_IMAGES_PER_MEMORY = 3   # max images from a single memory
    MAX_IMAGES_GLOBAL = 5       # hard cap on total images
    MAX_AUDIOS_GLOBAL = 3       # hard cap on total audios

    seen_image_keys: set = set()
    seen_audio_keys: set = set()
    final_images: List = []
    final_audios: List = []

    def _collect_from(ctx: Dict) -> None:
        """Collect media from a single context memory dict, respecting all caps.
        Group-sourced entries are silently skipped.
        """
        # Skip group memories — their media can't be decrypted server-side
        if ctx.get('source') == 'group':
            return

        mem_images_collected = 0

        # 1. Legacy plain-URL images
        for url in (ctx.get('images', []) or []):
            if not url or not isinstance(url, str):
                continue
            if (url not in seen_image_keys
                    and mem_images_collected < MAX_IMAGES_PER_MEMORY
                    and len(final_images) < MAX_IMAGES_GLOBAL):
                seen_image_keys.add(url)
                final_images.append(url)
                mem_images_collected += 1

        # 2. New encrypted MediaAsset descriptors
        for asset in (ctx.get('media', []) or []):
            if not isinstance(asset, dict):
                continue
            asset_type = asset.get('type', '')
            if asset_type == 'image':
                key = asset.get('mediaId') or asset.get('storagePath')
                if (key and key not in seen_image_keys
                        and mem_images_collected < MAX_IMAGES_PER_MEMORY
                        and len(final_images) < MAX_IMAGES_GLOBAL):
                    seen_image_keys.add(key)
                    final_images.append(asset)
                    mem_images_collected += 1
            elif asset_type == 'audio':
                key = asset.get('mediaId') or asset.get('storagePath')
                if (key and key not in seen_audio_keys
                        and len(final_audios) < MAX_AUDIOS_GLOBAL):
                    seen_audio_keys.add(key)
                    final_audios.append(asset)

        # 3. Legacy plain-URL audios
        for url in (ctx.get('audios', []) or []):
            if not url or not isinstance(url, str):
                continue
            if url not in seen_audio_keys and len(final_audios) < MAX_AUDIOS_GLOBAL:
                seen_audio_keys.add(url)
                final_audios.append(url)

    # ── CITED TRACK ──────────────────────────────────────────────────────────
    # Only process memories the LLM explicitly cited, in citation order.
    # Group-sourced memories are skipped inside _collect_from.
    cited_set = set(used_memory_ids)
    cited_contexts = sorted(
        [c for c in context_memories if c.get('memoryId') in cited_set],
        key=lambda c: used_memory_ids.index(c.get('memoryId'))
        if c.get('memoryId') in used_memory_ids else 999
    )
    for ctx in cited_contexts:
        _collect_from(ctx)

    personal_cited = [c for c in cited_contexts if c.get('source') != 'group']
    logger.debug(
        f"[MEDIA_EXTRACT] cited={len(cited_contexts)} total "
        f"(personal={len(personal_cited)}, group_skipped={len(cited_contexts)-len(personal_cited)}), "
        f"images={len(final_images)}, audios={len(final_audios)}"
    )

    return MediaUrls(
        images=final_images,
        audios=final_audios,
    )



def _filter_media_ids_by_score(
    ranked_memory_scores: List[tuple],
    raw_candidates: List[Dict],
    relative_threshold: float = 0.25,
) -> List[str]:
    """Return only the memory IDs whose BM25 score clears the relative threshold.

    The threshold is *relative* — a memory must score at least
    ``relative_threshold * top_score`` to be included. This prevents
    tangentially-retrieved memories (which BM25 scores slightly above zero due
    to corpus-relative scoring) from contributing their images.

    Args:
        ranked_memory_scores: List of (memory_id, aggregate_bm25_score) sorted
                              descending, as returned by ContextRefinementService.
        raw_candidates:       Original context list (used as fallback).
        relative_threshold:   A memory must score >= this fraction of the best
                              score. Default 0.25 (25 %).

    Returns:
        List of memory_ids eligible for media attachment, preserving score order.
    """
    if not ranked_memory_scores:
        # BM25 returned nothing (e.g. refiner got empty context).
        # Safest fallback: only the top vector-ranked memory gets media.
        if raw_candidates:
            top_id = raw_candidates[0].get("memoryId")
            return [top_id] if top_id else []
        return []

    top_score = ranked_memory_scores[0][1]

    if top_score <= 0:
        # All scores are zero or negative — nothing is genuinely relevant.
        return []

    cutoff = top_score * relative_threshold
    eligible = [mid for mid, score in ranked_memory_scores if score >= cutoff]
    logger.debug(
        f"[MEDIA_FILTER] top_score={top_score:.4f}, cutoff={cutoff:.4f}, "
        f"eligible={eligible}"
    )
    return eligible

class ChatService:
    
    def __init__(self):
        self.retrieval = retrieval_service
        self.reranker = reranking_service
        self.refiner = refinement_service
        self.summarizer = summarization_service
        self.llm = llm_service
        self.translator = translation_service
        self.firebase = firebase_service
        self.session_state = session_state_service
        self.query_rewriter = query_rewrite_service
        # Phase 2: use LLM classifier for ambiguous routing when flag is on
        self.routing_service = QueryRoutingService(
            use_llm_for_ambiguous=config.LLM_CLASSIFIER_ENABLED
        )
        self.query_intent_service = query_intent_service
        self.reasoning_agent = reasoning_agent_service
    
    def query_memories(
        self,
        request: ChatRequest,
        userId: str,
        background_tasks: BackgroundTasks = None,
        data_key_b64: Optional[str] = None
    ) -> ChatResponse:
        """
        Query memories with natural language
        
        NEW ARCHITECTURE:
        - Client provides pre-decrypted context
        - Server uses context directly for RAG
        - Server discards context after generating response
        
        Args:
            request: Chat request with query and context
            userId: User ID from authentication token
        
        Returns:
            Chat response with answer and metadata
        """
        start_time = time.time()
        
        original_query = request.query
        logger.info(f"[CHAT] Original Query: {original_query}")
        logger.info(f"[CHAT] User: {userId}")
        routing_type = request.routing_type or self.routing_service.detect_scope(original_query)

        # Map legacy "group"/"personal" values to new unified values
        if routing_type == "group":
            routing_type = "shared_only"   # legacy — map to canonical name
        if routing_type == "personal":
            routing_type = "personal_only"  # legacy — keep personal scope, do NOT search groups

        # If personal_only and a group_id was explicitly provided, still respect the group_id
        # but only after consent. shared_only = user confirmed they want shared results.
        if routing_type in ("both", "personal_only", "shared_only"):
            if routing_type in ("both", "shared_only") and request.group_id:
                self._ensure_group_member(request.group_id, userId)

        # --- TOKEN SAFETY CHECK ---
        # 1. Check if single message is too long
        query_tokens = len(original_query) / 4.0 # Approximation
        if query_tokens > config.MAX_SINGLE_MSG_TOKENS:
             return ChatResponse(
                answer=f"Your message is too long ({int(query_tokens)} tokens). Please shorten it to under {config.MAX_SINGLE_MSG_TOKENS} tokens.",
                sessionId=request.sessionId or "",
                sources=[],
                media=MediaUrls(),
                metadata=ChatMetadata(memories_searched=0, memories_retrieved=0, memories_used=0),
                retrieved_memories=[],
                retrieved_group_blocks=[]
            )

        # Step 1: Get or create session
        session = None
        session_summary = ""

        # E2E ENCRYPTION: conversation history comes from the CLIENT, not Firestore.
        # The client holds plaintext locally and sends recent turns in each request.
        # The server never reads plaintext message content from Firestore.
        conversation_history = list(request.conversation_history)  # List[ConversationTurn]

        if request.sessionId:
            session = self.firebase.get_session(request.sessionId)
            if session and session.userId == userId:
                session_summary = session.summary or ""
                logger.info(
                    f"[CHAT] Session loaded — client sent {len(conversation_history)} history turns, "
                    f"has_summary: {bool(session_summary)}"
                )
            else:
                logger.info(f"[CHAT] Session not found or unauthorized, creating new")
                session = None
        
        if not session:
            # Create new session with auto-generated title
            session_id = f"chat_{userId}_{uuid.uuid4().hex[:12]}"
            title = self._generate_title(original_query)
            session = ChatSession(
                sessionId=session_id,
                userId=userId,
                title=title,
                created_at=get_utc_now(),
                updated_at=get_utc_now()
            )
            self.firebase.create_session(session)
            logger.info(f"[CHAT] Created new session: {session_id}")

        # ── Phase 2: Load session RAG state ───────────────────────────────────
        rag_state = self.session_state.get(session.sessionId)
        if rag_state:
            logger.info(
                f"[CHAT] RAG state loaded — last_query: '{rag_state.get('lastStandaloneQuery', '')[:60]}' "
                f"route: {rag_state.get('lastQueryType', '')} "
                f"topic: {rag_state.get('topicLabel', '')}"
            )
        else:
            logger.info("[CHAT] No RAG state — cold start")
            
        # ═══════════════════════════════════════════════════════════════════
        #  PRE-RAG CLASSIFICATION GATE
        #  Order of decision (cheapest first):
        #   1. Single-word exact match   → instant, zero LLM cost
        #   2. LLM Router Agent          → one fast call, handles everything
        #   3. Heuristic fallback        → if agent disabled or failed
        # ═══════════════════════════════════════════════════════════════════

        # Step 1: Detect language and translate to English early
        english_query, detected_language = self.translator.detect_and_translate_to_english(original_query, skip_stage2=True)
        logger.info(f"[CHAT] Detected Language: {detected_language} | English Query: '{english_query}'")

        # Step 2: Ultra-fast exact match for single-word greetings
        clean_query = normalize_query(english_query)
        if clean_query in _INSTANT_MAP:
            logger.info(f"[CHAT] Instant match (no LLM): '{clean_query}'")
            
            english_answer = _INSTANT_MAP[clean_query]
            
            # Translate back
            final_answer = english_answer
            if detected_language.lower() != "english":
                final_answer = self.translator.translate_to_target_language(english_answer, detected_language)
            
            return self._save_and_respond(
                session=session,
                all_messages=conversation_history,
                original_query=original_query,
                final_answer=final_answer,
                background_tasks=background_tasks,
            )

        # ── Step 3: Run Query Intent Classification Engine ────────────────
        from app.utils.async_helper import run_async_safely
        query_plan = None

        if not request.context:
            query_plan = run_async_safely(self.query_intent_service.plan(english_query, userId))
            logger.info(f"[CHAT] Query Plan → intent={query_plan.intent}")

            if query_plan.intant == "INTROSPECTIVE" and routing_type != "personal_only":
                logger.info(f"[CHAT] Introspective query mis-classified as {routing_type} — forcing personal_only")
                routing_type = "personal_only"
                if intent == "INTROSPECTIVE":
                    logger.info("[CHAT] Introspective - Running Reasoning Agent Service")
                    introspective_context = [c for c in request.context if c.get('source') != 'group']
                    if len(introspective_context) != len(request.context):
                        logger.warning(
                            f"[CHAT][INTROSPECTIVE] Dropped "
                            f"{len(request.context) - len(introspective_context)} group memories"
                        )
                        

            # Bypass RAG search if intent is conversational
            # EXCEPTION: If query is explicitly about shared/group memories, force retrieval
            # regardless of intent — the classifier might mis-label these as CONVERSATIONAL.
            _is_shared_query = any(p.search(original_query) for p in _SHARED_ONLY_COMPILED)
            if query_plan.intent == "CONVERSATIONAL" and not _is_shared_query:
                logger.info(f"[CHAT] Conversational query — bypassing RAG search")
                english_answer, _, _ = self.llm.generate_chat_response(
                    query=english_query,
                    context_memories="",
                    conversation_history=conversation_history,
                    session_summary=session_summary
                )
                final_answer = english_answer
                if detected_language.lower() != "english":
                    final_answer = self.translator.translate_to_target_language(english_answer, detected_language)

                return self._save_and_respond(
                    session=session,
                    all_messages=conversation_history,
                    original_query=original_query,
                    final_answer=final_answer,
                    background_tasks=background_tasks,
                )
            elif query_plan.intent == "CONVERSATIONAL" and _is_shared_query:
                logger.info(f"[CHAT] Shared memory query mis-classified as CONVERSATIONAL — forcing retrieval")
                query_plan = query_plan.copy(update={"intent": "EXPLORATORY"})
        else:
            logger.info("[CHAT] Skip Query Plan — client provided context")

        # Pre-RAG router agent — classify every query, even on cold start
        agent_label = ROUTE_NEW_QUERY
        
        if not request.context:
            recent_turn_roles = [{"role": m.role} for m in conversation_history[-4:]]
            agent_result = chat_router_agent.classify(
                query=english_query,
                rag_state=rag_state or {},
                recent_turns=recent_turn_roles,
            )
            agent_label = agent_result["label"]
            logger.info(f"[CHAT] Router Agent label: {agent_label}")

            # Out-of-scope guard: non-memory queries are rejected before retrieval/LLM
            if agent_label == ROUTE_OUT_OF_SCOPE:
                logger.info(f"[CHAT] Out-of-scope query rejected: '{english_query[:80]}'")
                english_answer = (
                    "I'm SmritiQ, your personal memory assistant. I can only help with your saved memories "
                    "and past experiences. Ask me about a memory, person, place, or moment from your life."
                )
                final_answer = english_answer
                if detected_language.lower() != "english":
                    final_answer = self.translator.translate_to_target_language(english_answer, detected_language)

                return self._save_and_respond(
                    session=session,
                    all_messages=conversation_history,
                    original_query=original_query,
                    final_answer=final_answer,
                    background_tasks=background_tasks,
                )
        else:
            logger.info("[CHAT] Skip Router Agent — client provided context")

        # Fallback / follow-up routing labels mapping (legacy compatibility)
        _LABEL_MAP = {
            AGENT_FOLLOWUP_SAME:      ROUTE_FOLLOWUP_SAME,
            AGENT_FOLLOWUP_RETRIEVAL: ROUTE_FOLLOWUP_RETRIEVAL,
            ROUTE_MEMORY_QUERY:       ROUTE_NEW_QUERY,
        }
        route_label = _LABEL_MAP.get(agent_label, ROUTE_NEW_QUERY)

        logger.info(f"[CHAT] Route label: {route_label}")

        # ── followup_same_context → inject previous memory IDs for reuse ────────
        if route_label == ROUTE_FOLLOWUP_SAME and rag_state and not request.context:
            prev_ids = rag_state.get("lastMemoryIds", [])
            if prev_ids:
                logger.info(f"[CHAT] Reusing {len(prev_ids)} memory IDs from previous turn")
                request = request.copy(update={"_reuse_memory_ids": prev_ids})

        # ── followup_needs_retrieval → rewrite query before retrieval ────────────
        effective_query = original_query
        if route_label == ROUTE_FOLLOWUP_RETRIEVAL and rag_state:
            effective_query = self.query_rewriter.rewrite(
                current_query=original_query,
                last_standalone_query=rag_state.get("lastStandaloneQuery"),
                topic_label=rag_state.get("topicLabel"),
                entity_cache=rag_state.get("entityCache", []),
            )
            if effective_query != original_query:
                logger.info(f"[CHAT] Query rewritten: '{original_query}' → '{effective_query}'")

        logger.info(f"[CHAT] Context memories provided: {len(request.context)}")

        # If no plaintext context provided, perform retrieval.
        # followup_same_context: try to reuse previous memory IDs first.
        if not request.context:
            personal_payload: List[Dict] = []
            group_payload: List[Dict] = []

            # ── followup_same_context: re-fetch previous encrypted memories ────
            reuse_ids = getattr(request, "_reuse_memory_ids", None) or []
            if route_label == ROUTE_FOLLOWUP_SAME and reuse_ids:
                logger.info(f"[CHAT] followup_same_context — fetching {len(reuse_ids)} previous memories by ID")
                personal_payload = self._retrieve_personal_by_ids(reuse_ids)

            # ── new_query or followup_needs_retrieval: fresh hybrid search ─────
            if not personal_payload:
                if routing_type in ("personal", "both", "personal_only"):
                    if config.CHUNK_RETRIEVAL_ENABLED:
                        logger.info("[CHAT] Phase 1: Chunk retrieval enabled. Returning chunk hits to client.")
                        chunk_data = self.retrieval.chunk_search(
                            query=effective_query,
                            userId=userId,
                            include_vault=request.include_vault,
                            top_k=request.max_memories
                        )
                        chunk_data["sessionId"] = session.sessionId
                        return chunk_data
                    else:
                        logger.info(f"[CHAT] Running hybrid search for query: '{effective_query}' (user: {userId})")
                        personal_payload.extend(
                            self._retrieve_personal_results(
                                query=effective_query,
                                user_id=userId,
                                include_vault=request.include_vault,
                                top_k=request.max_memories,
                                data_key_b64=data_key_b64,
                                plan=query_plan,
                                skip_expansion=(query_plan.intent == "FACTUAL"),
                                intent=query_plan.intent,
                            )
                        )
                        logger.info(f"[CHAT] Hybrid search returned {len(personal_payload)} personal results")

            # ── Personal-only: if no personal results, signal consent_required ──
            if routing_type == "personal_only" and not personal_payload:
                logger.info("[CHAT] personal_only — no personal results. Signalling consent_required.")
                return ChatResponse(
                    answer="Hmm, I couldn't find anything in your personal memories about that 🤔 — but I did find some relevant memories in your shared group memories. Want me to look there instead?",
                    sessionId=session.sessionId,
                    sources=[],
                    media=MediaUrls(),
                    metadata=ChatMetadata(memories_searched=0, memories_retrieved=0, memories_used=0,
                                        processing_time_ms=(time.time()-start_time)*1000),
                    retrieved_memories=[],
                    retrieved_group_blocks=[],
                    consent_required=True,
                    intent=query_plan.intent if query_plan else "FACTUAL",
                )

            # ── Group search: runs for "both" and "shared_only" scopes ─────────
            # IMPORTANT: use english_query (translated), NOT original_query.
            # Embedding a Hindi query against English-embedded group memories produces
            # poor cosine scores. Even the Firestore fallback path benefits from this
            # because the translated query is logged for debugging.
            if routing_type in ("both", "shared_only"):
                group_payload.extend(
                    self._retrieve_group_results(
                        query=english_query,
                        user_id=userId,
                        group_id=request.group_id,
                        top_k=request.max_memories
                    )
                )

            merged_ranked = sorted(
                [dict(item, _kind='personal') for item in personal_payload] +
                [dict(item, _kind='group') for item in group_payload],
                key=lambda r: r.get('score', 0.0),
                reverse=True
            )

            personal_payload = [item for item in merged_ranked if item.get('_kind') == 'personal']
            group_payload = [item for item in merged_ranked if item.get('_kind') == 'group']

            for item in personal_payload:
                item.pop('_kind', None)
            for item in group_payload:
                item.pop('_kind', None)

            group_payload_response = [
                {
                    'memory_id': item.get('memory_id'),
                    'group_id': item.get('group_id'),
                    'group_name': item.get('group_name', ''),
                    'shared_by': item.get('shared_by'),
                    'author_id': item.get('author_id'),
                    'author_name': item.get('author_name'),
                    'shared_by_name': item.get('shared_by_name'),
                    'enc_ck_for_group': item.get('enc_ck_for_group'),
                    'gk_content_version': item.get('gk_content_version'),
                    'share_id': item.get('share_id'),
                    'encrypted_title': item.get('encrypted_title'),
                    'encrypted_text': item.get('encrypted_text'),
                    'media': item.get('media', []),
                    'images': item.get('images', []),
                    'audios': item.get('audios', []),
                    'tags': item.get('tags', []),
                    'created_at': item.get('created_at', ''),
                    'score': item.get('score', 0.0),
                    'chunk_id': item.get('chunk_id'),
                }
                for item in group_payload
            ]

            if personal_payload or group_payload:
                merged_count = len(personal_payload) + len(group_payload)
                processing_time = (time.time() - start_time) * 1000

                # ── Phase 2: persist rag_state after successful retrieval round ──
                retrieved_memory_ids = [p["memoryId"] for p in personal_payload if p.get("memoryId")]
                self._update_rag_state_async(
                    session_id=session.sessionId,
                    query=effective_query,
                    route_label=route_label,
                    memory_ids=retrieved_memory_ids,
                    rag_state=rag_state,
                    intent=query_plan.intent,
                )

                return ChatResponse(
                    answer="Retrieved encrypted results. Decrypt locally and resend plaintext context to continue.",
                    sessionId=session.sessionId,
                    sources=[],
                    media=MediaUrls(),
                    metadata=ChatMetadata(
                        memories_searched=merged_count,
                        memories_retrieved=merged_count,
                        memories_used=0,
                        processing_time_ms=processing_time
                    ),
                    retrieved_memories=personal_payload,
                    retrieved_group_blocks=group_payload_response,
                    intent=query_plan.intent
                )
            # If retrieval found nothing, fall through to no-context handling below
        
        # Handle "No Context" case (history-only answer)

        if not request.context:
            _current_intent = (query_plan.intent if query_plan else "FACTUAL")
            logger.info(f"[CHAT] ⚠️ No context provided. Retrieval returned 0 results. Intent={_current_intent}")

            # FACTUAL hard stop: if no memories found for a specific factual query,
            # return a definitive no-memory response WITHOUT calling the LLM.
            # This prevents the LLM from hallucinating answers from training data
            # or from conversation history that sounds plausible.
            if _current_intent == "FACTUAL":
                logger.info("[CHAT] FACTUAL + 0 results — returning hard no-memory response (no LLM call)")
                english_answer = "Hmm, I don't have a memory about that saved yet 🤔 Want to create one now?"
                final_answer = english_answer
                if detected_language.lower() != "english":
                    final_answer = self.translator.translate_to_target_language(english_answer, detected_language)

                return self._save_and_respond(
                    session=session,
                    all_messages=conversation_history,
                    original_query=original_query,
                    final_answer=final_answer,
                    background_tasks=background_tasks,
                )

            # Non-FACTUAL (EXPLORATORY / INTROSPECTIVE) with no memories:
            # Let the LLM handle gracefully using conversation history.
            logger.info(f"[CHAT] Non-FACTUAL query — letting LLM handle with empty context | History turns: {len(conversation_history)}")
            english_answer, _, _used_premium = self.llm.generate_chat_response(
                query=english_query,
                context_memories="",
                conversation_history=conversation_history,
                session_summary=session_summary,
                intent=intent if 'intent' in dir() else "EXPLORATORY"
            )
            
            # Translate back
            final_answer = english_answer
            if detected_language.lower() != "english":
                final_answer = self.translator.translate_to_target_language(english_answer, detected_language)
            
            # E2E: generate message IDs, save stubs (no plaintext), return IDs to client
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            self._save_message_stubs_and_update(
                session=session,
                user_msg_id=user_msg_id,
                asst_msg_id=asst_msg_id,
                conversation_history=conversation_history,
                current_query=original_query,
                current_answer=final_answer,
                session_summary=session_summary,
                background_tasks=background_tasks,
            )

            return ChatResponse(
                answer=final_answer,
                sessionId=session.sessionId,
                sources=[],
                media=MediaUrls(),
                metadata=ChatMetadata(
                    memories_searched=0,
                    memories_retrieved=0,
                    memories_used=0,
                    processing_time_ms=(time.time() - start_time) * 1000
                ),
                retrieved_memories=[],
                retrieved_group_blocks=[],
                user_message_id=user_msg_id,
                assistant_message_id=asst_msg_id,
                intent=query_plan.intent
            )
        
        # Step 2: Use provided context (already decrypted by client)
        # Context format: [{"memoryId": "...", "excerpt": "...", "title": "...", "date": "..."}, ...]
        logger.info(f"[CHAT] Context memories provided: {len(request.context)}")

        # Check query intent — REUSE query_plan already computed above (no second LLM call!)
        # query_plan was computed at the top of this function; reading .intent is free.
        intent = "FACTUAL"
        if rag_state and rag_state.get("intent"):
            intent = rag_state.get("intent")
        elif query_plan is not None:
            intent = query_plan.intent
            logger.info(f"[CHAT] Reusing cached query_plan intent: {intent} (no extra LLM call)")

        if intent == "INTROSPECTIVE":
            logger.info("[CHAT] Route: INTROSPECTIVE — running Reasoning Agent Service")
            english_answer, cited_docs, doc_map = self.reasoning_agent.analyze_and_synthesize(
                query=original_query,
                context=request.context,
                user_id=userId,
                conversation_history=conversation_history,
                session_summary=session_summary,
                detected_language=detected_language,
            )
            final_answer = english_answer
            
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            self._save_message_stubs_and_update(
                session=session,
                user_msg_id=user_msg_id,
                asst_msg_id=asst_msg_id,
                conversation_history=conversation_history,
                current_query=original_query,
                current_answer=final_answer,
                session_summary=session_summary,
                background_tasks=background_tasks,
            )
            # Map citations
            used_memory_ids = [doc_map.get(cid) for cid in cited_docs if doc_map.get(cid)]
            if not used_memory_ids:
                logger.warning("[CHAT][INTROSPECTIVE] LLM cited no docs. Falling back to BM25.")
                _, introspective_used_ids, introspective_scores, _ = self.refiner.refine_context(
                    query=english_query,
                    memories=request.context,
                    top_k=5
                )
                used_memory_ids = _filter_media_ids_by_score(introspective_scores, request.context)
            else:
                logger.info(f"[CHAT][INTROSPECTIVE] Used LLM citations for media: {used_memory_ids}")

            final_media = extract_media_from_context(request.context, used_memory_ids)
            logger.info(f"[CHAT][INTROSPECTIVE] Media-eligible memory IDs: {used_memory_ids}")
            if background_tasks and used_memory_ids:
                for mid in used_memory_ids:
                    background_tasks.add_task(self.firebase.update_memory_access, mid, userId)

            return ChatResponse(
                answer=final_answer,
                sessionId=session.sessionId,
                sources=[],
                media=final_media,
                metadata=ChatMetadata(
                    memories_searched=len(request.context),
                    memories_retrieved=len(request.context),
                    memories_used=len(request.context),
                    processing_time_ms=(time.time() - start_time) * 1000
                ),
                retrieved_memories=[],
                retrieved_group_blocks=[],
                user_message_id=user_msg_id,
                assistant_message_id=asst_msg_id,
                intent=intent
            )

        for i, ctx in enumerate(request.context[:3]):  # Log first 3 for debugging
            excerpt_len = len(ctx.get('excerpt') or ctx.get('text') or '')
            logger.info(f"  [CTX {i}] memoryId={ctx.get('memoryId')}, title={ctx.get('title')}, excerpt_len={excerpt_len}")
        # --- PHASE 1 OPTIMIZATION: Context Refinement ---
        # Instead of feeding raw memories to the LLM, we refine them into relevant chunks.
        # This saves tokens, reduces noise, and improves accuracy.
        
        # 1. Prepare raw candidates from request
        raw_candidates = []
        sources = []
        
        for ctx in request.context:
             # Basic validation
             if not ctx.get('excerpt') and not ctx.get('text'):
                 continue
                 
             raw_candidates.append(ctx)
             
             # Add to sources for metadata (tracking what was considered)
             sources.append(MemorySource(
                memoryId=ctx.get('memoryId', ''),
                title=ctx.get('title', 'Memory'),
                date=ctx.get('date', ''),
                excerpt=ctx.get('excerpt', '')[:100] + "...",
                relevance_score=0.0 # Will be updated if selected
            ))
            
        # ── SHARED MEMORY OVERVIEW BYPASS ────────────────────────────────────────
        # When the user asks an overview/inventory question about shared memories
        # (e.g. "has anyone shared anything?", "what memories are in my group?"),
        # BM25 CANNOT help — it strips "memories"/"shared"/"anyone" as stopwords
        # and scores group content near-zero because content is personal stories, not
        # about "sharing". The fix: detect these queries and bypass BM25 entirely,
        # feeding ALL context (personal + group) directly to the LLM with full attribution.
        _is_shared_overview = any(p.search(original_query) for p in _SHARED_ONLY_COMPILED)

        # Separate group vs personal context so group memories are never silently dropped
        group_candidates = [c for c in raw_candidates if c.get('source') == 'group']
        personal_candidates = [c for c in raw_candidates if c.get('source') != 'group']
        has_group_context = bool(group_candidates)

        if _is_shared_overview and has_group_context:
            logger.info(
                f"[CHAT] Shared-overview query detected — bypassing BM25. "
                f"Feeding ALL {len(raw_candidates)} contexts ({len(group_candidates)} group, "
                f"{len(personal_candidates)} personal) directly to LLM."
            )
            context_parts = []
            doc_map = {}
            used_memory_ids = []
            for idx, ctx in enumerate(raw_candidates):
                doc_id = idx + 1
                mid = ctx.get('memoryId', '')
                doc_map[doc_id] = mid
                if mid:
                    used_memory_ids.append(mid)

                title = ctx.get('title', 'Memory')
                date = ctx.get('date', 'Unknown')
                content = ctx.get('excerpt') or ctx.get('text') or ''
                if not content:
                    continue

                source_label = ctx.get('source', 'personal')
                author = ctx.get('author_name') or ctx.get('shared_by_name') or ctx.get('shared_by') or ''
                group_name = ctx.get('group_name', '')

                if source_label == 'group':
                    group_str = f" in group '{group_name}'" if group_name else " in a shared group"
                    author_str = f" — shared by {author}{group_str}" if author else f" — from shared group{group_str}"
                else:
                    author_str = ""

                # Truncate long excerpts to stay within token budget (shared overviews need breadth not depth)
                content_preview = content[:800] if len(content) > 800 else content
                context_parts.append(
                    f"[Doc {doc_id}] Source: {title} ({date}){author_str}\nContent: {content_preview}"
                )

            refined_context_str = "\n\n".join(context_parts)
            ranked_memory_scores = [(mid, 1.0) for mid in used_memory_ids]
            logger.info(f"[CHAT] Overview bypass context length: {len(refined_context_str)} chars, docs: {len(context_parts)}")

        else:
            # 2. Normal path: Refine Context using BM25 (Smart Squeeze)
            # Keeps only the sentences that actually answer the query.
            # For normal memory queries, BM25 works well and saves tokens.
            # But we ALWAYS include group memories in the context even if BM25 scores them low —
            # group memories use personal story content, so BM25 may score them low for shared-query
            # terms. We ensure group memories are appended after BM25-refined personal memories.
            refined_context_str, used_memory_ids, ranked_memory_scores, doc_map = self.refiner.refine_context(
                query=english_query,
                memories=raw_candidates,
                top_k=5  # Keep top 5 sentences/chunks
            )

            logger.info(f"[CHAT] Refined context string length: {len(refined_context_str)} chars")
            logger.info(f"[CHAT] Used memory IDs: {used_memory_ids}")
            logger.info(f"[CHAT] Ranked memory scores (top 3): {ranked_memory_scores[:3]}")

            # ── Guaranteed group injection: if BM25 ran but dropped all group memories ────
            # IMPORTANT: Only active when we explicitly searched groups (both/shared_only).
            # For personal_only queries, group memories must NEVER be injected.
            if has_group_context and routing_type in ("both", "shared_only"):
                bm25_ids_set = set(used_memory_ids)
                dropped_group = [c for c in group_candidates if c.get('memoryId') not in bm25_ids_set]
                if dropped_group:
                    logger.info(f"[CHAT] Re-injecting {len(dropped_group)} BM25-dropped group memories into context")
                    # Append after BM25 context — they'll be clearly labelled for the LLM
                    extra_parts = []
                    next_doc_id = max(doc_map.keys(), default=0) + 1
                    for ctx in dropped_group:
                        mid = ctx.get('memoryId', '')
                        doc_map[next_doc_id] = mid
                        if mid and mid not in bm25_ids_set:
                            used_memory_ids.append(mid)
                        title = ctx.get('title', 'Memory')
                        date = ctx.get('date', 'Unknown')
                        content = (ctx.get('excerpt') or ctx.get('text') or '')[:600]
                        author = ctx.get('author_name') or ctx.get('shared_by_name') or ctx.get('shared_by') or ''
                        group_name = ctx.get('group_name', '')
                        group_str = f" in group '{group_name}'" if group_name else " in a shared group"
                        author_str = f" — shared by {author}{group_str}" if author else f" — from shared group{group_str}"
                        extra_parts.append(
                            f"[Doc {next_doc_id}] Source: {title} ({date}){author_str}\nContent: {content}"
                        )
                        next_doc_id += 1
                    if extra_parts:
                        if refined_context_str:
                            refined_context_str = refined_context_str + "\n\n" + "\n\n".join(extra_parts)
                        else:
                            refined_context_str = "\n\n".join(extra_parts)

            # Fallback: if BM25 refiner returned empty (common with narrative/Hindi text),
            # use top memories preserving group memories too.
            fallback_memory_ids_for_media = []
            if not refined_context_str and raw_candidates:
                logger.warning("[CHAT] Refiner returned empty context — falling back to all memories (personal top-3 + all group).")
                # Personal: top 3 by score
                fallback_personal = personal_candidates[:3]
                # Group: only include if this query was meant to search groups
                fallback_group = group_candidates if routing_type in ("both", "shared_only") else []
                fallback_all = fallback_personal + fallback_group
                context_parts = []
                doc_map = {}
                used_memory_ids = []
                for idx, ctx in enumerate(fallback_all):
                    doc_id = idx + 1
                    mid = ctx.get('memoryId', '')
                    doc_map[doc_id] = mid
                    title = ctx.get('title', 'Memory')
                    date = ctx.get('date', 'Unknown')
                    content = ctx.get('excerpt') or ctx.get('text') or ''

                    num_legacy_imgs = len(ctx.get('images', []) or [])
                    num_encrypted_imgs = sum(1 for asset in (ctx.get('media', []) or []) if isinstance(asset, dict) and asset.get('type') == 'image')
                    total_images = num_legacy_imgs + num_encrypted_imgs

                    num_legacy_auds = len(ctx.get('audios', []) or [])
                    num_encrypted_auds = sum(1 for asset in (ctx.get('media', []) or []) if isinstance(asset, dict) and asset.get('type') == 'audio')
                    total_audios = num_legacy_auds + num_encrypted_auds

                    media_info = ""
                    if total_images > 0 or total_audios > 0:
                        parts = []
                        if total_images > 0:
                            parts.append(f"{total_images} image{'s' if total_images > 1 else ''}")
                        if total_audios > 0:
                            parts.append(f"{total_audios} audio note{'s' if total_audios > 1 else ''}")
                        media_info = f" [Attached Media: {', '.join(parts)}]"

                    author = ctx.get('author_name') or ctx.get('shared_by_name') or ctx.get('shared_by') or ''
                    group_name = ctx.get('group_name', '')
                    source_label = ctx.get('source', 'personal')
                    if source_label == 'group':
                        group_str = f" in group '{group_name}'" if group_name else " in a shared group"
                        author_str = f" — shared by {author}{group_str}" if author else f" — from shared group{group_str}"
                    else:
                        author_str = f" — shared by {author}" if author else ""
                    context_parts.append(f"[Doc {doc_id}] Source: {title} ({date}){author_str}{media_info}\nContent: {content}")
                    if mid:
                        used_memory_ids.append(mid)
                refined_context_str = "\n\n".join(context_parts)
                used_memory_ids = list(dict.fromkeys(used_memory_ids))
                logger.info(f"[CHAT] Fallback context length: {len(refined_context_str)} chars")

        # Update sources to only include those that were used
        final_sources = [s for s in sources if s.memoryId in used_memory_ids]

        # Step 3: Generate answer
        # --- Let the LLM decide ---
        should_skip_llm = False
        english_answer = ""
        cited_docs = []
        used_premium_model = False   # tracks which model path was used (premium skips personality pass)
        
        if not refined_context_str and not raw_candidates and not conversation_history and not session_summary:
            # Truly empty: no memories retrieved, no conversation context
            logger.info(f"[CHAT] 🛑 Strict Mode: no context, no history. Returning fallback.")
            english_answer = "Hmm, I don't seem to have any memories saved about that yet 🤔 — want to create one so I can remember it for you?"
            should_skip_llm = True
        
        if not should_skip_llm:
            english_answer, cited_docs, used_premium_model = self.llm.generate_chat_response(
                query=original_query,
                context_memories=refined_context_str,
                conversation_history=conversation_history,
                session_summary=session_summary,
                intent=intent   # Dynamic routing: FACTUAL → fast, CONVERSATIONAL/EXPLORATORY → premium
            )

        #  Media extraction 
        final_media = MediaUrls()
        if not should_skip_llm and raw_candidates:
            final_used_ids = [doc_map.get(cid) for cid in cited_docs if doc_map.get(cid)]
            if not final_used_ids:
                logger.warning("[CHAT] LLM cited no docs. Falling back to BM25 or top-1.")
                final_used_ids = _filter_media_ids_by_score(ranked_memory_scores, raw_candidates)
            else:
                logger.info(f"[CHAT] Used LLM citations for media: {final_used_ids}")

            final_media = extract_media_from_context(raw_candidates, final_used_ids)
            logger.info(
                f"[CHAT] Final media  images: {len(final_media.images)}, "
                f"audios: {len(final_media.audios)}, "
                f"media_eligible_ids: {final_used_ids}"
            )

        # Defensive: if context exists but model still returns a "couldn't find"-style
        # answer, rewrite to a truthful "mentioned vs not mentioned" response.
        if refined_context_str and isinstance(english_answer, str):
            lowered = english_answer.lower()
            if "couldn't find" in lowered or "could not find" in lowered:
                first_source = "a saved memory"
                for line in refined_context_str.splitlines():
                    if line.strip().lower().startswith("source:"):
                        first_source = line.split(":", 1)[1].strip() or first_source
                        break
                english_answer = (
                    f"I found a related memory ({first_source}) that mentions this topic, "
                    f"but it doesn't explicitly answer your exact question. "
                    f"If you want, ask a simpler question about what the memory directly says."
                )
                should_skip_llm = True
        
        # Step 4: Translate answer ONLY if it was a hardcoded English fallback
        final_answer = english_answer
        if should_skip_llm and detected_language.lower() != "english":
            final_answer = self.translator.translate_to_target_language(
                english_answer,
                detected_language
            )

        # Step 4b: Personality refinement pass
        # SKIPPED when premium model (Luna) was used — it already generates warm output.
        # Only applied on the FAST model (gpt-5-mini) path for FACTUAL queries.
        if final_answer and config.PERSONALITY_LAYER_ENABLED and not used_premium_model:
            has_group = bool(group_payload) if 'group_payload' in dir() else False
            final_answer = self.llm.refine_personality(
                factual_answer=final_answer,
                original_query=original_query,
                has_group_content=has_group,
            )

        logger.info(f"[CHAT] Generated response with {len(sources)} sources")

        
        # Step 5: E2E — save message stubs (no plaintext), return message IDs
        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        self._save_message_stubs_and_update(
            session=session,
            user_msg_id=user_msg_id,
            asst_msg_id=asst_msg_id,
            conversation_history=conversation_history,
            current_query=original_query,
            current_answer=final_answer,
            session_summary=session_summary,
            background_tasks=background_tasks,
        )

        logger.info(f"[CHAT] Context discarded (not stored)")
        
        if background_tasks and used_memory_ids:
            for mid in used_memory_ids:
                background_tasks.add_task(self.firebase.update_memory_access, mid, userId)

        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            answer=final_answer,
            sessionId=session.sessionId,
            sources=final_sources,
            media=final_media,
            metadata=ChatMetadata(
                memories_searched=len(request.context),
                memories_retrieved=len(request.context),
                memories_used=len(used_memory_ids),
                processing_time_ms=processing_time
            ),
            retrieved_memories=[],
            retrieved_group_blocks=[],
            intent=intent,
            user_message_id=user_msg_id,
            assistant_message_id=asst_msg_id,
        )
    
    def _generate_title(self, query: str) -> str:
        """Generate session title from first query"""
        words = query.split()[:6]
        title = ' '.join(words)
        return title + ('...' if len(words) >= 6 else '')

    def _ensure_group_member(self, group_id: str, user_id: str) -> None:
        member_doc = self.firebase.db.collection('group_members').document(f"{group_id}_{user_id}").get()
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a group member")
        member = member_doc.to_dict()
        if member.get('status') != 'active':
            raise HTTPException(status_code=403, detail="Membership inactive")

    # ─────────────────────────────────────────────────────────────────────────
    # Shared helper: build a slim, clean retrieval payload dict from a Memory.
    # ONLY includes fields that the Flutter client needs:
    #   • Encryption blobs (title / text / transcript)
    #   • Media assets (legacy plain-URL + new encrypted MediaAsset)
    #   • Metadata needed for UI (tags, vault flag, timestamps, score)
    #
    # Intentionally EXCLUDED (to stop leaking enrichment analytics):
    #   emotion, valence, arousal, dominance, importance_score, persons, places,
    #   events, temporal, semantic_concepts, access_count, last_accessed_at,
    #   is_reflection, text_formatting, search_tokens, moods, user_tags
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _build_memory_payload(mem, score: float) -> Dict:
        """Return a slim retrieval dict — safe to send to the client."""
        # Serialise new encrypted MediaAsset objects safely
        media_list = []
        for asset in getattr(mem, 'media', []):
            try:
                media_list.append(asset.model_dump() if hasattr(asset, 'model_dump') else dict(asset))
            except Exception:
                pass

        # Normalise created_at to an ISO string so JSON serialisation is safe
        created_at = getattr(mem, 'created_at', None)
        if created_at is not None and hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()

        return {
            'type': 'personal',
            'memoryId':             mem.memoryId,
            'encrypted_title':      getattr(mem, 'encrypted_title', ''),
            'encrypted_text':       getattr(mem, 'encrypted_text', ''),
            'encrypted_transcript': getattr(mem, 'encrypted_transcript', None),
            'encrypted_english_text': getattr(mem, 'encrypted_english_text', None),
            # Legacy plain-URL media fields (empty for new memories)
            'images':       list(getattr(mem, 'images', []) or []),
            'audios':       list(getattr(mem, 'audios', []) or []),
            # New encrypted-asset descriptors (populated for new memories)
            'media':        media_list,
            # Display / filter metadata
            'tags':         list(getattr(mem, 'tags', []) or []),
            'is_in_vault':  bool(getattr(mem, 'is_in_vault', False)),
            'created_at':   created_at,
            'score':        float(score),
        }

    def _retrieve_personal_results(
        self,
        query: str,
        user_id: str,
        include_vault: bool,
        top_k: int,
        data_key_b64: Optional[str] = None,
        plan: Optional[Any] = None,
        skip_expansion: bool = False,
        intent: Optional[str] = None,
    ) -> List[Dict]:
        """Hybrid search → slim retrieval payload (no enrichment fields)."""
        matches = self.retrieval.hybrid_search(
            query=query,
            userId=user_id,
            include_vault=include_vault,
            top_k=top_k,
            data_key_b64=data_key_b64,
            plan=plan,
            skip_expansion=skip_expansion,
            intent=intent,
        )
        return [self._build_memory_payload(mem, score) for mem, score in matches]

    def _retrieve_personal_by_ids(self, memory_ids: List[str]) -> List[Dict]:
        """
        Fetch specific memories by their IDs from Firestore.
        Used for followup_same_context: reuse previously retrieved memories
        without performing a new vector search.
        Returns the same slim payload as _retrieve_personal_results.
        """
        if not memory_ids:
            return []
        memories = self.firebase.get_memories_by_ids(memory_ids)
        results = [self._build_memory_payload(mem, score=1.0) for mem in memories]
        logger.info(f"[CHAT] _retrieve_personal_by_ids: fetched {len(results)} of {len(memory_ids)} IDs")
        return results

    def _retrieve_group_results(self, query: str, user_id: str, group_id: Optional[str], top_k: int) -> List[Dict]:
        return self.retrieval.group_chunk_search(
            query=query,
            userId=user_id,
            group_id=group_id,
            top_k=top_k
        )

    def _save_message_stubs_and_update(
        self,
        session: "ChatSession",
        user_msg_id: str,
        asst_msg_id: str,
        conversation_history: list,
        current_query: str,
        current_answer: str,
        session_summary: str,
        background_tasks=None,
    ) -> None:
        """
        Save message stubs (metadata only, no plaintext) and trigger TextRank.

        E2E ENCRYPTION:
          - Saves message stubs with empty encrypted_content (client fills later).
          - Updates session metadata (count, updated_at).
          - Runs TextRank on the TRANSIENT conversation history that the client
            sent in this request — the only time the server sees plaintext.
          - Plaintext is discarded after this call returns.

        TextRank uses the conversation turns provided by the client,
        not Firestore-stored messages (those are encrypted ciphertext).
        """
        # Save message stubs (no plaintext content)
        user_msg = ChatMessage(
            messageId=user_msg_id,
            sessionId=session.sessionId,
            role="user",
            timestamp=get_utc_now(),
        )
        asst_msg = ChatMessage(
            messageId=asst_msg_id,
            sessionId=session.sessionId,
            role="assistant",
            timestamp=get_utc_now(),
        )
        self.firebase.save_message(user_msg)
        self.firebase.save_message(asst_msg)

        # Update session metadata
        new_count = getattr(session, 'message_count', 0) + 2
        self.firebase.update_session(session.sessionId, {
            'message_count': new_count,
            'updated_at': get_utc_now(),
        })

        # TextRank summarization using CLIENT-PROVIDED history
        # Build full turn list = client history + current turn (just generated)
        all_turns = list(conversation_history) + [
            ConversationTurn(role="user", content=current_query),
            ConversationTurn(role="assistant", content=current_answer),
        ]

        if len(all_turns) > RAW_HISTORY_WINDOW:
            old_turns = all_turns[:-RAW_HISTORY_WINDOW]
            if (len(old_turns) >= MIN_MSGS_FOR_TEXTRANK or session_summary) and background_tasks:
                background_tasks.add_task(
                    self._update_summary,
                    session_id=session.sessionId,
                    old_turns=old_turns,
                    current_summary=session_summary,
                    new_message_count=new_count,
                )

    def _update_summary(
        self,
        session_id: str,
        old_turns: list,
        current_summary: str,
        new_message_count: int
    ) -> None:
        """
        Background task: Runs AFTER response is sent to the user (zero latency impact).

        E2E ENCRYPTION:
          - Uses the transient conversation turns that were passed from the
            request handler (NOT read from Firestore — Firestore has ciphertext).
          - Produces an abstract TextRank summary.
          - No wipe step needed — Firestore never had plaintext.
        """
        logger.info(f"[CHAT] Background: compressing {len(old_turns)} old turns for session {session_id}")
        new_summary = self.summarizer.summarize_messages(old_turns, current_summary)

        self.firebase.update_session_summary(
            sessionId=session_id,
            summary=new_summary,
            message_count=new_message_count
        )
        logger.info(f"[CHAT] Background: summary updated ({len(new_summary)} chars) for session {session_id}")

    def _save_and_respond(
        self,
        session: "ChatSession",
        all_messages: list,
        original_query: str,
        final_answer: str,
        background_tasks=None,
        sources: list = None,
    ) -> "ChatResponse":
        """
        E2E version: save stubs, return message IDs, no plaintext storage.
        Used by the Router Agent greeting path.
        """
        sources = sources or []

        user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"

        self._save_message_stubs_and_update(
            session=session,
            user_msg_id=user_msg_id,
            asst_msg_id=asst_msg_id,
            conversation_history=all_messages,  # these are ConversationTurn objects from client
            current_query=original_query,
            current_answer=final_answer,
            session_summary="",
            background_tasks=background_tasks,
        )

        return ChatResponse(
            answer=final_answer,
            sessionId=session.sessionId,
            sources=sources,
            media=MediaUrls(),
            metadata=ChatMetadata(
                memories_searched=0, memories_retrieved=0, memories_used=0
            ),
            retrieved_memories=[],
            retrieved_group_blocks=[],
            user_message_id=user_msg_id,
            assistant_message_id=asst_msg_id,
            intent="CONVERSATIONAL"
        )

    def _retrieve_personal_by_ids(self, memory_ids: List[str]) -> List[Dict]:
        """
        Fetch encrypted personal memory blobs by ID list.
        Used in followup_same_context route to skip vector search
        and re-serve the same memories from the previous turn.
        Returns the same slim payload as _retrieve_personal_results.
        """
        results: List[Dict] = []
        for mid in memory_ids:
            try:
                mem = self.firebase.get_memory(mid)
                if not mem:
                    continue
                results.append(self._build_memory_payload(mem, score=1.0))
            except Exception as e:
                logger.error(f"[CHAT] Failed to fetch memory {mid} by ID: {e}", exc_info=True)
        return results

    def _update_rag_state_async(
        self,
        session_id: str,
        query: str,
        route_label: str,
        memory_ids: List[str],
        rag_state: Optional[Dict],
        intent: Optional[str] = None,
    ) -> None:
        """
        Persist rag_state after a retrieval turn.

        Privacy rules:
          - Only stores IDs and abstract labels — no memory plaintext.
          - topic_label: carry forward from previous rag_state (updated below).
          - entity_cache: only stored if ENTITY_INDEX_ENABLED=True.
          - answer_summary: abstract only, never verbatim memory text.
        """
        try:
            # Carry forward topic_label if this is a follow-up; else derive from query
            topic_label = ""
            if rag_state:
                topic_label = rag_state.get("topicLabel", "")

            # Simple topic derivation from query: take first 5 meaningful words
            if not topic_label and query:
                stop = {"what", "is", "was", "are", "tell", "me", "about", "find", "my", "the", "a", "an"}
                words = [w for w in query.lower().split() if w not in stop][:5]
                topic_label = " ".join(words)

            # Carry forward entity_cache if following up on same topic
            entity_cache = []
            if rag_state and route_label in (ROUTE_FOLLOWUP_SAME, ROUTE_FOLLOWUP_RETRIEVAL):
                entity_cache = rag_state.get("entityCache", [])

            self.session_state.update(
                session_id=session_id,
                query=query,
                route_label=route_label,
                memory_ids=memory_ids,
                chunk_ids=[],     # Phase 1 chunk IDs wired in Phase 3 integration
                topic_label=topic_label,
                entity_cache=entity_cache,
                answer_summary="",  # Abstract answer summary written after LLM response in Phase 3+
                intent=intent,
            )
            logger.debug(f"[CHAT] RAG state updated for session {session_id}")
        except Exception as e:
            # Non-fatal — never let rag_state writes fail the user-facing response
            logger.error(f"[CHAT] rag_state update failed for {session_id}: {e}", exc_info=True)

chat_service = ChatService()

