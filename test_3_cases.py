import os
import sys
import logging

# Add backend root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.reasoning_agent_service import reasoning_agent_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_3_cases")

FAKE_CONTEXT = [
    {
        "memoryId": "fake_001",
        "title": "First day at new job",
        "excerpt": "Aaj pehla din tha naye office mein. Sab log bahut friendly the. Manager ne bola ki team flexible hai. Thoda nervous tha par overall achha laga.",
        "text": "Aaj pehla din tha naye office mein. Sab log bahut friendly the. Manager ne bola ki team flexible hai. Thoda nervous tha par overall achha laga.",
        "date": "2025-01-15T09:00:00Z",
        "images": ["img1.jpg"],
    },
    {
        "memoryId": "fake_002",
        "title": "Fight with best friend",
        "excerpt": "Rahul se badi baat ho gayi. Usne kaha ki main hamesha apni hi sunta hoon. Dukh hua par shayad wo sahi tha. Mujhe change hona padega.",
        "text": "Rahul se badi baat ho gayi. Usne kaha ki main hamesha apni hi sunta hoon. Dukh hua par shayad wo sahi tha. Mujhe change hona padega.",
        "date": "2025-03-22T18:30:00Z",
    },
    {
        "memoryId": "fake_003",
        "title": "Goa trip with family",
        "excerpt": "Teen saal baad poori family ek saath thi. Papa koitne saalon baad tension-free dekha. Shaam ko beach pe chai peete hue purani baatein yaad ki.",
        "text": "Teen saal baad poori family ek saath thi. Papa koitne saalon baad tension-free dekha. Shaam ko beach pe chai peete hue purani baatein yaad ki.",
        "date": "2025-05-10T12:00:00Z",
        "images": ["img2.jpg", "img3.jpg"],
    },
    {
        "memoryId": "fake_004",
        "title": "Got promoted",
        "excerpt": "Finally Senior Engineer ban gaya! Hard work paid off. Raat ko akele baith ke thoda roya — khushi mein. Mummy-papa ko sabse pehle bataya.",
        "text": "Finally Senior Engineer ban gaya! Hard work paid off. Raat ko akele baith ke thoda roya — khushi mein. Mummy-papa ko sabse pehle bataya.",
        "date": "2025-07-30T15:45:00Z",
    },
    {
        "memoryId": "fake_005",
        "title": "Solo trip to Manali",
        "excerpt": "Pehli baar akele travelling ki. Pahadon mein shanti milti hai. Apne baare mein bohot kuch socha. Life kis taraf ja rahi hai, samajh aaya.",
        "text": "Pehli baar akele travelling ki. Pahadon mein shanti milti hai. Apne baare mein bohot kuch socha. Life kis taraf ja rahi hai, samajh aaya.",
        "date": "2025-10-05T10:00:00Z",
    },
]

QUERIES = [
    ("main kaisa insaan hoon", "Hindi"),
    ("meri life mein kya patterns dikh rahe hain", "Hinglish"),
    ("how have I changed this year", "English"),
    ("mere relationships kaisi hain", "Hinglish"),
]

TEST_CASES = [
    {
        "name": "Case 1: gpt-5-nano | effort=low | budget=3000",
        "model": "gpt-5-nano",
        "reasoning_effort": "low",
        "max_completion_tokens": 3000,
    },
    {
        "name": "Case 2: gpt-5-nano | effort=medium | budget=16000",
        "model": "gpt-5-nano",
        "reasoning_effort": "medium",
        "max_completion_tokens": 16000,
    },
    {
        "name": "Case 3: gpt-5.6-luna | budget=4000",
        "model": "gpt-5.6-luna",
        "reasoning_effort": None,
        "max_completion_tokens": 4000,
    },
]

def run():
    for case_info in TEST_CASES:
        print("\n" + "=" * 80)
        print(f"RUNNING: {case_info['name']}")
        print("=" * 80)

        for query, lang in QUERIES:
            print(f"\n>>> QUERY: {query!r}  |  lang={lang}")
            print("-" * 50)
            try:
                res = reasoning_agent_service.analyze_and_synthesize(
                    query=query,
                    context=FAKE_CONTEXT,
                    user_id="test_user_3cases",
                    conversation_history=[],
                    session_summary="",
                    detected_language=lang,
                    model_override=case_info["model"],
                    reasoning_effort_override=case_info["reasoning_effort"],
                    max_completion_tokens_override=case_info["max_completion_tokens"],
                )
                answer, cited_docs, doc_map = res
                print(f"cited_docs : {cited_docs}")
                print(f"answer ({len(answer)} chars):\n{answer[:300]}...")
            except Exception as exc:
                print(f"ERROR: {exc}")

if __name__ == "__main__":
    run()
