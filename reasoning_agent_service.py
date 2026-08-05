import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.config import config
from app.services.firebase_service import firebase_service
from app.services.qualitative_labels import (
    describe_valence,
    describe_arousal,
    describe_trajectory,
    is_milestone,
)
from app.models.memory_model import Memory

logger = logging.getLogger(__name__)

# NOTE: This string is passed through .format(detected_language=...).
# Do NOT introduce literal { } characters here — they will raise KeyError.
SYSTEM_PROMPT = """You are SmritiQ. You speak to the user like someone who has read everything they've written and remembers it. Warm, specific, never generic. Their words matter more than yours.

You receive a chronological timeline of the user's journal entries. Each entry has: date, title, content, emotion, milestone flag, people, places, and attached media counts. You also receive overall trend descriptions. All values are already qualitative — use them as written.

Write a personal reflection answering the user's question.

- Quote the user's own words directly wherever they carry the feeling — in quotation marks, with the date. Their words first, your framing second.
- Ground everything strictly in the entries provided. Invent nothing.
- Name emotional patterns or shifts you notice across the timeline.
- Give weight to entries marked as milestones.
- Include at least one entry the user may not have thought about in a while.
- End on one specific observation that invites them to keep thinking.
- Cite entries inline as [[1]], [[3]] as you reference them, immediately after the sentence that uses them.
- Respond in: {detected_language}
- Around 200 words. If everything doesn't fit, prioritize the emotional pattern over listing individual entries."""


class ReasoningAgentService:
    def __init__(self):
        self.firebase = firebase_service

    def analyze_and_synthesize(
        self,
        query: str,
        context: List[Dict[str, Any]],
        user_id: str,
        conversation_history: List[Any] = [],
        session_summary: str = "",
        detected_language: str = "English",
        model_override: Optional[str] = None,
        reasoning_effort_override: Optional[str] = None,
        max_completion_tokens_override: Optional[int] = None,
    ) -> tuple:
        """
        Takes raw memories retrieved for an introspective query, performs timeline
        and emotion analysis, and generates a personalized synthesis.

        Returns: (synthesis_string, list_of_cited_doc_ids, doc_map)
        """
        try:
            if not context:
                return "I don't have enough memory context to analyze that trend.", [], {}

            # 1. Fetch Firestore metadata for these memories to get emotion, importance, etc.
            mids = [ctx.get("memoryId") for ctx in context if ctx.get("memoryId")]
            memories = self.firebase.get_memories_by_ids(mids)
            metadata_map = {m.memoryId: m for m in memories}

            # 2. Correlate decrypted text with metadata and sort chronologically
            timeline_items = []
            for ctx in context:
                mid = ctx.get("memoryId")
                title = ctx.get("title") or "Untitled Memory"
                excerpt = ctx.get("excerpt") or ctx.get("text") or ""

                meta = metadata_map.get(mid)
                event_date = None
                emotion = None
                importance_score = 0.5
                persons = []
                places = []

                if meta:
                    event_date = getattr(meta.temporal, "event_date", None) or meta.created_at
                    emotion = meta.emotion
                    importance_score = meta.importance_score
                    persons = [p.canonical_name or p.mention for p in meta.persons if p.canonical_name or p.mention]
                    places = [pl.normalized_name or pl.mention for pl in meta.places if pl.normalized_name or pl.mention]
                else:
                    date_str = ctx.get("date")
                    if date_str:
                        try:
                            event_date = datetime.fromisoformat(date_str)
                        except Exception:
                            pass

                if not event_date:
                    event_date = datetime.now(timezone.utc)

                # Extract and count media files (legacy plain arrays + encrypted media list)
                num_legacy_imgs = len(ctx.get('images', []) or [])
                num_encrypted_imgs = sum(1 for asset in (ctx.get('media', []) or []) if isinstance(asset, dict) and asset.get('type') == 'image')
                total_images = num_legacy_imgs + num_encrypted_imgs

                num_legacy_auds = len(ctx.get('audios', []) or [])
                num_encrypted_auds = sum(1 for asset in (ctx.get('media', []) or []) if isinstance(asset, dict) and asset.get('type') == 'audio')
                total_audios = num_legacy_auds + num_encrypted_auds

                timeline_items.append({
                    "memoryId": mid,
                    "date": event_date,
                    "title": title,
                    "excerpt": excerpt,
                    "emotion": emotion,
                    "importance": importance_score,
                    "persons": persons,
                    "places": places,
                    "total_images": total_images,
                    "total_audios": total_audios
                })

            # Sort timeline oldest to newest
            timeline_items.sort(key=lambda x: x["date"])

            # 3. Analyze emotional trend metrics
            valence_trend = []
            arousal_trend = []
            milestones = []
            all_people = set()
            all_places = set()

            for item in timeline_items:
                all_people.update(item["persons"])
                all_places.update(item["places"])

                if item["emotion"]:
                    valence_trend.append(item["emotion"].valence)
                    arousal_trend.append(item["emotion"].arousal)

                if is_milestone(item["importance"]):
                    milestones.append(f"'{item['title']}' ({item['date'].strftime('%b %d, %Y')})")

            avg_valence = sum(valence_trend) / len(valence_trend) if valence_trend else 0.0
            avg_arousal = sum(arousal_trend) / len(arousal_trend) if arousal_trend else 0.0

            valence_direction = "fluctuating"
            if len(valence_trend) >= 2:
                diff = valence_trend[-1] - valence_trend[0]
                if diff > 0.15:
                    valence_direction = "improving/more positive"
                elif diff < -0.15:
                    valence_direction = "declining/more negative"
                else:
                    valence_direction = "relatively stable"

            # 4. Format prompt strings — QUALITATIVE ONLY, no numeric values
            doc_map = {}
            timeline_str_parts = []
            for idx, item in enumerate(timeline_items):
                doc_id = idx + 1
                doc_map[doc_id] = item["memoryId"]

                dt_str = item["date"].strftime("%Y-%m-%d")

                if item["emotion"]:
                    emo_str = (
                        f"{item['emotion'].primary_emotion} — "
                        f"mood: {describe_valence(item['emotion'].valence)}, "
                        f"energy: {describe_arousal(item['emotion'].arousal)}"
                    )
                else:
                    emo_str = "not recorded"

                timeline_str_parts.append(
                    f"[Doc {doc_id}] Date: {dt_str}\n"
                    f"Title: {item['title']}\n"
                    f"Content: {item['excerpt']}\n"
                    f"Emotion: {emo_str}\n"
                    f"Milestone: {'yes' if is_milestone(item['importance']) else 'no'}\n"
                    f"People: {', '.join(item['persons']) or 'None'}\n"
                    f"Places: {', '.join(item['places']) or 'None'}\n"
                    f"Attached Images: {item['total_images']}\n"
                    f"Attached Audio Notes: {item['total_audios']}\n"
                )

            timeline_str = "\n".join(timeline_str_parts)

            analysis_summary = (
                f"- Overall mood: {describe_valence(avg_valence)}\n"
                f"- Overall energy: {describe_arousal(avg_arousal)}\n"
                f"- Trajectory: {describe_trajectory(valence_direction)}\n"
                f"- Core Milestones: {', '.join(milestones) or 'None'}\n"
                f"- Key People: {', '.join(list(all_people)) or 'None'}\n"
                f"- Key Places: {', '.join(list(all_places)) or 'None'}\n"
            )

            # 5. Call LLM for final synthesis
            import openai
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)

            system_content = SYSTEM_PROMPT.format(
                detected_language=(detected_language or "English")
            )
            messages = [
                {"role": "system", "content": system_content},
            ]

            if session_summary and session_summary.strip():
                messages.append({
                    "role": "user",
                    "content": f"[Earlier in this conversation]\n{session_summary.strip()}"
                })
                messages.append({
                    "role": "assistant",
                    "content": "Got it, I have context from our earlier conversation."
                })

            for msg in conversation_history:
                role = "user" if msg.role == "user" else "assistant"
                content = msg.content
                if content:
                    messages.append({"role": role, "content": content[:800]})

            user_content = (
                f"[JOURNAL TIMELINE]\n{timeline_str}\n\n"
                f"[TREND METRICS ANALYSIS]\n{analysis_summary}\n\n"
                f"[USER QUERY]\n{query}"
            )
            messages.append({"role": "user", "content": user_content})

            target_model = model_override or config.LLM_MODEL
            target_max_tokens = max_completion_tokens_override if max_completion_tokens_override is not None else 3000
            target_effort = reasoning_effort_override if reasoning_effort_override is not None else "low"

            logger.info(
                f"[REASONING AGENT] Synthesizing | model={target_model} | effort={target_effort} | lang={detected_language}"
            )
            create_kwargs = {
                "model": target_model,
                "messages": messages,
                "max_completion_tokens": target_max_tokens,
            }
            if target_effort is not None:
                create_kwargs["reasoning_effort"] = target_effort

            try:
                response = client.chat.completions.create(**create_kwargs)
            except Exception as call_err:
                # If model doesn't support reasoning_effort (e.g. non-reasoning model), retry without it
                if "reasoning_effort" in create_kwargs:
                    create_kwargs.pop("reasoning_effort")
                    response = client.chat.completions.create(**create_kwargs)
                else:
                    raise call_err

            # Record usage
            try:
                from app.utils.usage_tracker import record_call
                if response.usage:
                    record_call("reasoning_synthesis", config.LLM_MODEL,
                                response.usage.prompt_tokens, response.usage.completion_tokens)
            except Exception as tr_err:
                logger.error(f"Failed to record reasoning synthesis usage: {tr_err}")

            finish_reason = response.choices[0].finish_reason if response.choices else "unknown"

            # Structured token log — this is the metric that validates the whole change.
            _rt = 0
            try:
                _rt = getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0) or 0
            except Exception:
                pass
            _visible = max(1, (response.usage.completion_tokens or 0) - _rt)
            logger.info(
                f"[TOKENS] layer=reasoning_agent model={config.LLM_MODEL} "
                f"lang={detected_language} "
                f"prompt={response.usage.prompt_tokens} "
                f"completion={response.usage.completion_tokens} "
                f"reasoning={_rt} visible={_visible} "
                f"ratio={_rt / _visible:.1f} "
                f"finish={finish_reason}"
            )

            answer_text = response.choices[0].message.content
            if not answer_text or not answer_text.strip():
                if finish_reason == "length":
                    logger.error(
                        "[REASONING AGENT] Token budget exhausted before visible output. "
                        "Check the [TOKENS] line above for the reasoning/visible split."
                    )
                    return ("I tried to reflect on your memories but the analysis was too long to complete. "
                            "Try asking about a shorter time period or fewer memories."), [], {}
                logger.error(f"[REASONING AGENT] Empty response. finish_reason={finish_reason}")
                return ("I was trying to reflect on your memories but couldn't generate a response. "
                        "Could you try asking again?"), [], {}

            # Inline citation extraction — replaces JSON parsing entirely.
            raw = answer_text.strip()
            cited_docs = sorted({int(n) for n in re.findall(r'\[\[(\d+)\]\]', raw)})
            answer = re.sub(r'\s*\[\[\d+\]\]', '', raw).strip()

            # Keep only citations that map to a real document
            cited_docs = [c for c in cited_docs if c in doc_map]

            logger.info(
                f"[REASONING AGENT] Synthesis OK | cited_docs={cited_docs} | chars={len(answer)}"
            )
            return answer, cited_docs, doc_map

        except Exception as e:
            logger.error(f"[REASONING AGENT] Synthesis failed: {e}", exc_info=True)
            return ("I was trying to reflect on your memories but encountered an error processing "
                    "your emotional patterns. Could you try asking again?"), [], {}


reasoning_agent_service = ReasoningAgentService()
