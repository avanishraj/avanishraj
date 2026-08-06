INFO:     [TRANSLATION] Detected: Hinglish
INFO:     [TRANSLATION] Original: hi, what type of person I am? and what is the best...
INFO:     [TRANSLATION] Translated: Hi, what kind of person am I? And what's the best ...
INFO:     [CHAT] Detected Language: Hinglish | English Query: 'Hi, what kind of person am I? And what's the best memory I have?'
INFO:     Saved scores for user XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [CRM] Scores computed for XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     Saved behavior state for user bSxYBrZPjSRXnanCVZDvEJrJlHS2
INFO:     [CRM] Behavior state computed for bSxYBrZPjSRXnanCVZDvEJrJlHS2
INFO:     Saved scores for user bSxYBrZPjSRXnanCVZDvEJrJlHS2
INFO:     [CRM] Scores computed for bSxYBrZPjSRXnanCVZDvEJrJlHS2
INFO:     HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     [TRACKER] Recorded call: stage=intent_classification, model=gpt-5-nano, input_tokens=1534, output_tokens=728, cost=$0.000222
INFO:     [QUERY PLANNER] Model response: {
  "intent": "INTROSPECTIVE",
  "people": [],
  "temporal": {
    "start_date": null,
    "end_date": null,
    "description": "no specific time period mentioned"
  },
  "emotional_tone": "neutral",
  "keywords": ["person", "best memory", "memory", "self-evaluation"]
}
INFO:     [QUERY PLANNER] Generated plan: {'intent': 'INTROSPECTIVE', 'people': [], 'resolved_person_ids': [], 'temporal': {'start_date': None, 'end_date': None, 'description': 'no specific time period mentioned'}, 'emotional_tone': 'neutral', 'keywords': ['person', 'best memory', 'memory', 'self-evaluation']}
INFO:     [CHAT] Query Plan → intent=INTROSPECTIVE
INFO:     [CHAT] INTROSPECTIVE — forcing personal_only (was both)
INFO:     Saved behavior state for user ec5RlFi45EW5YA2p7Lwt6TmDDzA3
INFO:     [CRM] Behavior state computed for ec5RlFi45EW5YA2p7Lwt6TmDDzA3
INFO:     Saved behavior state for user f57ObkXgk9UmJR1RbTtKJmermiC2
INFO:     [CRM] Behavior state computed for f57ObkXgk9UmJR1RbTtKJmermiC2
INFO:     Saved scores for user ec5RlFi45EW5YA2p7Lwt6TmDDzA3
INFO:     [CRM] Scores computed for ec5RlFi45EW5YA2p7Lwt6TmDDzA3
INFO:     Saved scores for user f57ObkXgk9UmJR1RbTtKJmermiC2
INFO:     HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     [TRACKER] Recorded call: stage=chat_routing, model=gpt-5-nano, input_tokens=608, output_tokens=405, cost=$0.000111
INFO:     [ROUTER AGENT] 'Hi, what kind of person am I? And what's the best memory I h' → label=memory_query
INFO:     [CHAT] Router Agent label: memory_query
INFO:     [CHAT] Route label: new_query
INFO:     [CHAT] Context memories provided: 0
INFO:     [CHAT] Running hybrid search for query: 'hi, what type of person I am? and what is the best memory I have?' (user: XS6zKg69sqRMNlx8bkSy00JTAy12)
INFO:     [HYBRID] Running Phase 3 orchestrated search for query: 'hi, what type of person I am? and what is the best memory I have?' | intent: INTROSPECTIVE
INFO:     [CRM] Scores computed for f57ObkXgk9UmJR1RbTtKJmermiC2
INFO:     HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     [EXPAND] Expanded query 'hi, what type of person I am? and what is the best memory I have?' into 5 variants:
INFO:       v1: hi, what type of person I am? and what is the best memory I have?
INFO:       v2: Find descriptions of my personality traits and identity, and identify the most meaningful or standout recollection in my past memories.
INFO:       v3: Search for a specific past moment or achievement I clearly remember—what I did, where I was, who was there, and any memorable details that made it stand out.
INFO:       v4: Look for memories that capture how I felt at the time—proud, excited, calm, anxious, grateful—and determine which one best reflects my character.
INFO:       v5: I think of myself as someone who keeps trying and learning, even when things feel uncertain. The best memory I have is a moment when I felt genuinely proud and supported, and I could tell I was growing into my own. I still remember the vibe really clearly.
INFO:     Saved behavior state for user jWgyCj9ICcWAMFS8ynreeRgH61D3
INFO:     [CRM] Behavior state computed for jWgyCj9ICcWAMFS8ynreeRgH61D3
INFO:     [HYBRID] Full expansion — 5 variants generated
INFO:     Saved scores for user jWgyCj9ICcWAMFS8ynreeRgH61D3
INFO:     [HYBRID] Vector search (ns=emotional) returned 8 matches
INFO:     [HYBRID] Vector search (ns=semantic) returned 8 matches
INFO:     [HYBRID] Vector search (ns=semantic) returned 8 matches
INFO:     [HYBRID] Vector search (ns=semantic) returned 8 matches
INFO:     [HYBRID] Vector search (ns=emotional) returned 8 matches
INFO:     [HYBRID] Vector search (ns=semantic) returned 8 matches
INFO:     [HYBRID] Vector search (ns=temporal) returned 8 matches
INFO:     [CRM] Scores computed for jWgyCj9ICcWAMFS8ynreeRgH61D3
INFO:     [HYBRID] Vector search (ns=emotional) returned 8 matches
INFO:     [HYBRID] Vector search (ns=temporal) returned 8 matches
INFO:     [HYBRID] Vector search (ns=semantic) returned 8 matches
INFO:     [HYBRID] Vector search (ns=emotional) returned 8 matches
INFO:     [HYBRID] Vector search (ns=temporal) returned 8 matches
INFO:     [HYBRID] Vector search (ns=emotional) returned 8 matches
INFO:     [HYBRID] Vector search (ns=temporal) returned 8 matches
INFO:     [HYBRID] Vector search (ns=temporal) returned 8 matches
INFO:     [HMAC SEARCH] Token search returned 1 matches
INFO:     [HYBRID] HMAC token search returned 1 results
INFO:     [HYBRID] RRF fused 8 unique candidates
INFO:     [CHAT] Hybrid search returned 8 personal results
INFO:     [TRACKER] Successfully saved usage log for user XS6zKg69sqRMNlx8bkSy00JTAy12. Total cost: $0.000389
INFO:     127.0.0.1:56660 - "POST /chat/ HTTP/1.1" 200 OK
INFO:     [TRACKER] Started tracking for activity: chat
INFO:     [CHAT] Original Query: hi, what type of person I am? and what is the best memory I have?
INFO:     [CHAT] User: XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [CHAT] Session loaded — client sent 0 history turns, has_summary: False
INFO:     [CHAT] RAG state loaded — last_query: 'hi, what type of person I am? and what is the best memory I ' route: new_query topic: hi, type of person i
INFO:     Saved behavior state for user XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [CRM] Behavior state computed for XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     [TRACKER] Recorded call: stage=translation, model=gpt-4o-mini, input_tokens=231, output_tokens=35, cost=$0.000056
INFO:     [TRANSLATION] Detected: Hinglish
INFO:     [TRANSLATION] Original: hi, what type of person I am? and what is the best...
INFO:     [TRANSLATION] Translated: hi, what kind of person am I? and what's the best ...
INFO:     [CHAT] Detected Language: Hinglish | English Query: 'hi, what kind of person am I? and what's the best memory I have?'
INFO:     [CHAT] Skip Query Plan — client provided context
INFO:     [CHAT] Skip Router Agent — client provided context
INFO:     [CHAT] Route label: new_query
INFO:     [CHAT] Context memories provided: 8
INFO:     [CHAT] Context memories provided: 8
INFO:     [CHAT] Route: INTROSPECTIVE — running Reasoning Agent Service
INFO:     [CTX-LEN] n=8 lens=[404, 1114, 118, 2102, 96, 684, 146, 422]
INFO:     [REASONING AGENT] Synthesizing | model=gpt-5.6-luna | effort=low | lang=Hinglish
INFO:     Saved scores for user XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [CRM] Scores computed for XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     Saved behavior state for user uPLOuaSjsiUjwXbFLH8ZJD8wdoA2
INFO:     [CRM] Behavior state computed for uPLOuaSjsiUjwXbFLH8ZJD8wdoA2
INFO:     HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
INFO:     [TRACKER] Recorded call: stage=reasoning_synthesis, model=gpt-5.6-luna, input_tokens=2055, output_tokens=448, cost=$0.009617
INFO:     [TOKENS] layer=reasoning_agent model=gpt-5.6-luna lang=Hinglish prompt=2055 completion=448 reasoning=55 visible=393 ratio=0.1 finish=stop
INFO:     [REASONING AGENT] Synthesis OK | cited_docs=[1, 2, 3, 4, 5, 6, 8] | chars=1363
INFO:     [CHAT][INTROSPECTIVE] Used LLM citations for media: ['mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085331_3043ce0f', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085805_a9885ea3', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085917_277845fb', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806090437_d9e7aa84', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806090830_580b2e08', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806091344_a2369940', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806140640_f2a443ec']
INFO:     [CHAT][INTROSPECTIVE] Media-eligible memory IDs: ['mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085331_3043ce0f', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085805_a9885ea3', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806085917_277845fb', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806090437_d9e7aa84', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806090830_580b2e08', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806091344_a2369940', 'mem_XS6zKg69sqRMNlx8bkSy00JTAy12_20260806140640_f2a443ec'] 
INFO:     Saved scores for user uPLOuaSjsiUjwXbFLH8ZJD8wdoA2
INFO:     [TRACKER] Successfully saved usage log for user XS6zKg69sqRMNlx8bkSy00JTAy12. Total cost: $0.009673
INFO:     127.0.0.1:49676 - "POST /chat/ HTTP/1.1" 200 OK
INFO:     [CRM] Scores computed for uPLOuaSjsiUjwXbFLH8ZJD8wdoA2
INFO:     Saved behavior state for user XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [CRM] Behavior state computed for XS6zKg69sqRMNlx8bkSy00JTAy12
INFO:     [FIREBASE] Saved 2/2 encrypted messages in session chat_XS6zKg69sqRMNlx8bkSy00JTAy12_eeaab39935e0
INFO:     127.0.0.1:56078 - "POST /chat/messages/save HTTP/1.1" 200 OK
INFO:     Saved behavior state for user xth787BEHvUWtVrmChDEz0w6fiU2
