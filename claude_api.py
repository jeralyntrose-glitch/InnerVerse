import os
from openai import OpenAI
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pinecone import Pinecone
import openai
import time
import json
from src.services.pinecone_organizer import extract_all_metadata, organize_results_by_metadata, format_organized_context
from src.services.conversation_context import get_or_create_context
from src.services.prompt_builder import build_system_prompt, PromptAssemblyError
from src.services.type_injection import get_type_stack

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

# Load MBTI reference data at module level (loaded once on startup)
try:
    with open('src/data/reference_data.json', 'r') as f:
        REFERENCE_DATA = json.load(f)
    print("✅ [REFERENCE DATA] Loaded MBTI reference data successfully")
except FileNotFoundError:
    print("⚠️ [REFERENCE DATA] reference_data.json not found - using Pinecone only")
    REFERENCE_DATA = {}
except Exception as e:
    print(f"⚠️ [REFERENCE DATA] Error loading reference_data.json: {e}")
    REFERENCE_DATA = {}

# ===== EMBEDDING CACHE (RAG Optimization) =====
# Stores embeddings for repeated questions to avoid re-computation
# Bounded to prevent memory bloat
_embedding_cache = {}
_EMBEDDING_CACHE_MAX_SIZE = 100  # Max entries before eviction

def get_cached_embedding(text: str) -> list | None:
    """Get embedding from cache if exists."""
    return _embedding_cache.get(text)

def cache_embedding(text: str, embedding: list) -> None:
    """Cache embedding with LRU-style eviction when at capacity."""
    if len(_embedding_cache) >= _EMBEDDING_CACHE_MAX_SIZE:
        # Remove oldest entry (first key in dict - Python 3.7+ maintains insertion order)
        oldest_key = next(iter(_embedding_cache))
        del _embedding_cache[oldest_key]
        print(f"🗑️ [CACHE] Evicted oldest entry, cache size: {len(_embedding_cache)}")
    _embedding_cache[text] = embedding

PROJECTS = [
    {"id": "relationship-lab", "name": "💕 Relationship Lab", "emoji": "💕", "description": "Deep focus on golden pairs, compatibility, relationship dynamics"},
    {"id": "mbti-academy", "name": "🎓 MBTI Academy", "emoji": "🎓", "description": "Structured learning on cognitive functions and type theory"},
    {"id": "type-detective", "name": "🔍 Type Detective", "emoji": "🔍", "description": "Practice typing real people and analyzing behavior patterns"},
    {"id": "trading-psychology", "name": "📈 Trading Psychology", "emoji": "📈", "description": "Analyze trading behavior through MBTI lens"},
    {"id": "pm-playbook", "name": "💼 PM Playbook", "emoji": "💼", "description": "Product management applications of MBTI"},
    {"id": "quick-hits", "name": "⚡ Quick Hits", "emoji": "⚡", "description": "Random questions that don't fit elsewhere"},
    {"id": "brain-dump", "name": "🧠 Brain Dump", "emoji": "🧠", "description": "Capture thoughts and ideas"}
]

def get_db_connection():
    """Get PostgreSQL database connection"""
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)

def get_pinecone_index():
    """Get Pinecone index client"""
    if not PINECONE_API_KEY or not PINECONE_INDEX:
        return None
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)

def extract_follow_up_question(text: str) -> str:
    """
    Extract follow-up question from Claude's response.
    Pattern: [FOLLOW-UP: question?]
    Returns: The extracted question string, or None if not found
    """
    import re
    follow_up_match = re.search(r'\[FOLLOW-UP:\s*(.+?)\]', text, re.IGNORECASE)
    if follow_up_match:
        return follow_up_match.group(1).strip()
    return None

def detect_functions_in_message(text: str) -> List[str]:
    """
    Detect cognitive functions mentioned in message.
    Returns list of function codes (e.g., ['Ni', 'Te', 'Fi'])
    """
    import re
    
    if not text:
        return []
    
    text_upper = text.upper()
    functions = ['NI', 'NE', 'SI', 'SE', 'TI', 'TE', 'FI', 'FE']
    detected = []
    
    for func in functions:
        # Match function code as standalone word or with common suffixes
        patterns = [
            rf'\b{func}\b',  # Standalone: "Ni hero"
            rf'\b{func} HERO\b',
            rf'\b{func} PARENT\b',
            rf'\b{func} CHILD\b',
            rf'\b{func} INFERIOR\b',
            rf'\b{func} NEMESIS\b',
            rf'\b{func} CRITIC\b',
            rf'\b{func} TRICKSTER\b',
            rf'\b{func} DEMON\b',
        ]
        
        if any(re.search(pattern, text_upper) for pattern in patterns):
            detected.append(func.capitalize())
    
    return list(set(detected))  # Remove duplicates

def rerank_chunks_with_metadata(chunks: List[Dict], user_question: str) -> List[Dict]:
    """
    Re-rank chunks using BOTH similarity score AND metadata relevance.
    Boosts chunks that match detected types, functions, and query intent.
    """
    from src.services.type_injection import detect_types_in_message
    
    detected_types = detect_types_in_message(user_question)
    detected_functions = detect_functions_in_message(user_question)
    question_lower = user_question.lower()
    
    for chunk in chunks:
        base_score = chunk.get('score', 0.0)
        boost = 0.0
        
        # Boost if types match (strongest signal)
        chunk_types = chunk.get('types_discussed', [])
        if chunk_types and detected_types:
            matching_types = set(chunk_types) & set(detected_types)
            if matching_types:
                boost += 0.12 * len(matching_types)  # Up to +0.24 for 2 types
        
        # Boost if functions match
        chunk_functions = chunk.get('functions_covered', [])
        if chunk_functions and detected_functions:
            matching_funcs = set(chunk_functions) & set(detected_functions)
            if matching_funcs:
                boost += 0.08 * len(matching_funcs)
        
        # Boost recent seasons (Season 20+ reflects latest thinking)
        season_str = chunk.get('season', '')
        if season_str:
            try:
                season_num = int(season_str)
                if season_num >= 20:
                    boost += 0.06
                elif season_num >= 15:
                    boost += 0.03
            except (ValueError, TypeError):
                pass
        
        # Boost if content_type matches query intent
        content_type = chunk.get('content_type', '').lower()
        
        # Relationship queries
        if any(keyword in question_lower for keyword in ['relationship', 'compatible', 'interact', 'pair', 'together']):
            if 'relationship' in content_type:
                boost += 0.10
        
        # Octagram queries
        if any(keyword in question_lower for keyword in ['octagram', 'udsf', 'uduf', 'sdsf', 'sduf', 'developed', 'focused']):
            if 'octagram' in content_type or 'development' in content_type:
                boost += 0.15
        
        # Function-specific queries
        if any(keyword in question_lower for keyword in ['function', 'hero', 'parent', 'child', 'inferior', 'shadow']):
            if 'function' in content_type or 'cognitive' in content_type:
                boost += 0.08
        
        # Type comparison queries
        if len(detected_types) >= 2:
            if 'comparison' in content_type or 'dynamics' in content_type:
                boost += 0.10
        
        # Apply boost (cap at 1.0)
        chunk['boosted_score'] = min(1.0, base_score + boost)
        chunk['boost_applied'] = boost
    
    # Re-sort by boosted score
    chunks.sort(key=lambda x: x.get('boosted_score', x.get('score', 0.0)), reverse=True)
    
    return chunks

def format_rag_context_professional(sorted_chunks: List[Dict]) -> str:
    """
    Format RAG chunks with full metadata for Claude accuracy.
    
    Includes critical metadata (types, functions, category, score) in clean single-line format.
    This helps Claude understand context relevance without verbose decorative bloat.
    """
    if not sorted_chunks:
        return "No relevant content found in the knowledge base."
    
    context_parts = []
    
    for i, chunk in enumerate(sorted_chunks, 1):
        # Build metadata line - clean, single-line format
        meta_parts = [f"[Source {i}]"]
        
        # Season (recency/authority)
        season = chunk.get('season', '')
        if season:
            meta_parts.append(f"Season:{season}")
        
        # Types discussed (CRITICAL for function stack accuracy)
        types_discussed = chunk.get('types_discussed', [])
        if types_discussed:
            types_str = ','.join(types_discussed[:4]) if isinstance(types_discussed, list) else str(types_discussed)
            meta_parts.append(f"Types:{types_str}")
        
        # Functions covered (CRITICAL for function stack accuracy - full 8-function stack)
        functions_covered = chunk.get('functions_covered', [])
        if functions_covered:
            funcs_str = ','.join(functions_covered[:8]) if isinstance(functions_covered, list) else str(functions_covered)
            meta_parts.append(f"Functions:{funcs_str}")
        
        # Category (helps Claude understand content type)
        category = chunk.get('primary_category', '')
        if category and category != 'unknown':
            meta_parts.append(f"Category:{category}")
        
        # Score (relevance indicator)
        score = chunk.get('boosted_score', chunk.get('score', 0.0))
        if score:
            meta_parts.append(f"Score:{score:.2f}")
        
        # Join with pipe separator for clean readability
        metadata_line = " | ".join(meta_parts)
        context_parts.append(metadata_line)
        context_parts.append(chunk['text'])
        context_parts.append("")  # Blank line between chunks
    
    return "\n".join(context_parts)

def calculate_confidence_score(chunks: list, query: str) -> dict:
    """
    Calculate answer confidence based on retrieval quality.
    OPTIMIZED: Single-pass calculation with simplified thresholds.
    
    Args:
        chunks: Retrieved Pinecone chunks with scores
        query: User's query
        
    Returns:
        Dict with confidence level, score, and reasoning
    """
    if not chunks:
        return {
            "level": "none",
            "score": 0.0,
            "reasoning": "No relevant sources found",
            "stars": "⭐",
            "source_count": 0
        }
    
    # Single pass: calculate avg_score (uses boosted_score if available)
    chunk_count = len(chunks)
    avg_score = sum(c.get('boosted_score', c.get('score', 0.0)) for c in chunks) / chunk_count
    
    # Simplified thresholds - avg_score is primary indicator
    # MBTI domain: 0.50-0.60 can be good quality due to semantic complexity
    if avg_score >= 0.75:
        level, stars = "very_high", "⭐⭐⭐⭐⭐"
        reasoning = f"{chunk_count} highly relevant sources"
    elif avg_score >= 0.65:
        level, stars = "high", "⭐⭐⭐⭐"
        reasoning = f"{chunk_count} strong matches"
    elif avg_score >= 0.55:
        level, stars = "medium", "⭐⭐⭐"
        reasoning = f"{chunk_count} moderate matches"
    elif avg_score >= 0.45:
        level, stars = "low", "⭐⭐"
        reasoning = f"Limited information ({chunk_count} sources)"
    else:
        level, stars = "very_low", "⭐"
        reasoning = "Insufficient information"
    
    return {
        "level": level,
        "score": avg_score,
        "reasoning": reasoning,
        "stars": stars,
        "source_count": chunk_count
    }


def format_citations(chunks: list) -> str:
    """
    Format citations from retrieved chunks.
    
    Args:
        chunks: Retrieved Pinecone chunks
        
    Returns:
        Formatted citation string
    """
    citations = []
    
    for i, chunk in enumerate(chunks[:5], 1):  # Top 5 sources
        metadata = chunk.get('metadata', {}) if isinstance(chunk.get('metadata'), dict) else {}
        filename = metadata.get('filename', chunk.get('filename', 'Unknown'))
        season = metadata.get('season', chunk.get('season', 'Unknown'))
        match_score = chunk.get('score', chunk.get('boosted_score', 0.0))
        
        # Clean filename
        filename = filename.replace('.pdf', '').replace('_', ' ')
        
        citations.append(
            f"{i}. **Season {season}:** {filename} (Match: {match_score:.2f})"
        )
    
    return "\n".join(citations) if citations else "No sources available"


def extract_filters_from_query(query: str) -> dict:
    """
    Extract Pinecone filters from user query using FAST regex (no GPT call).
    
    PERFORMANCE FIX: Replaced GPT-4o-mini call with instant regex matching.
    GPT call was adding 1-2s latency on EVERY query for minimal benefit.
    
    Args:
        query: User's question
        
    Returns:
        Dict of Pinecone filters (empty dict if no filters extracted)
    """
    import re
    
    filters = {}
    query_upper = query.upper()
    
    # Extract MBTI types mentioned (instant regex, no API call)
    mbti_types = re.findall(r'\b(INTJ|INTP|ENTJ|ENTP|INFJ|INFP|ENFJ|ENFP|ISTJ|ISFJ|ESTJ|ESFJ|ISTP|ISFP|ESTP|ESFP)\b', query_upper)
    if mbti_types:
        # Deduplicate while preserving order
        unique_types = list(dict.fromkeys(mbti_types))
        filters["types_discussed"] = {"$in": unique_types}
        print(f"🎯 [FAST-FILTER] Detected types: {unique_types}")
    
    # Extract season if explicitly mentioned
    season_match = re.search(r'season\s*(\d+)', query, re.IGNORECASE)
    if season_match:
        filters["season"] = {"$eq": season_match.group(1)}
        print(f"🎯 [FAST-FILTER] Detected season: {season_match.group(1)}")
    
    return filters


def expand_query(original_query: str) -> list:
    """
    Generate multiple query variations for better recall using GPT-4o-mini.
    
    Args:
        original_query: User's original question
        
    Returns:
        List of query variations (including original)
    """
    if not OPENAI_API_KEY:
        return [original_query]
    
    try:
        openai.api_key = OPENAI_API_KEY
        
        prompt = f"""You are an expert in CS Joseph's MBTI/Jungian typology system.
Generate 2-3 alternative phrasings of this question to improve search recall.
Use different terminology, synonyms, and related concepts.

Original Question: "{original_query}"

Rules:
- Keep the core intent
- Use CS Joseph terminology (shadow, subconscious, octagram, etc.)
- Include related concepts (e.g., "ENFP development" → "ENFP Si inferior growth")
- Vary specificity (broader and narrower versions)

Return as JSON array of strings (2-3 variations only):"""
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate query variations for MBTI search. Return JSON array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Some creativity but consistent
            max_tokens=200  # Reduced for faster response
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in markdown
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        variations = json.loads(response_text)
        
        # Validate it's a list
        if not isinstance(variations, list):
            print(f"⚠️ [QUERY-EXPANSION] GPT returned non-list: {type(variations)}")
            return [original_query]
        
        # Add original query
        all_queries = [original_query] + variations
        print(f"🔍 [QUERY-EXPANSION] Expanded to {len(all_queries)} queries: {all_queries}")
        
        return all_queries[:3]  # Cap at 3 total (original + 2 variations) for faster processing
        
    except json.JSONDecodeError as e:
        print(f"⚠️ [QUERY-EXPANSION] JSON parsing failed: {e}")
        return [original_query]
    except Exception as e:
        print(f"⚠️ [QUERY-EXPANSION] Query expansion failed: {e}")
        return [original_query]


def query_innerverse_local(question: str, progress_callback=None) -> str:
    """
    IMPROVED HYBRID SEARCH for MBTI content:
    - Upgraded to text-embedding-3-large for better semantic matching
    - Optimized top_k to 15 for speed (only need 12 chunks + small buffer)
    - Smart query rewriting with MBTI ontology
    - Metadata filtering for type-specific queries
    - Re-ranking for relevance
    """
    try:
        print(f"\n🔍 [CLAUDE DEBUG] Query: '{question}'")
        print(f"📍 [CLAUDE DEBUG] Using Pinecone index: {PINECONE_INDEX}")
        print(f"🔑 [CLAUDE DEBUG] OpenAI API Key: {'✅ SET' if OPENAI_API_KEY else '❌ MISSING'}")
        print(f"🔑 [CLAUDE DEBUG] Pinecone API Key: {'✅ SET' if PINECONE_API_KEY else '❌ MISSING'}")
        
        if not OPENAI_API_KEY:
            print("❌ [CLAUDE DEBUG] OpenAI API key missing!")
            return ""
        
        openai.api_key = OPENAI_API_KEY
        pinecone_index = get_pinecone_index()
        if not pinecone_index:
            print("❌ [CLAUDE DEBUG] Failed to get Pinecone index!")
            return ""
        
        print(f"✅ [CLAUDE DEBUG] Pinecone index connected successfully")
        
        if progress_callback:
            progress_callback("searching")
        
        import time as _time  # Local import for timing
        from concurrent.futures import ThreadPoolExecutor
        
        # Check embedding cache first
        cached_embedding = get_cached_embedding(question)
        
        # RAG OPTIMIZATION: Parallel filter extraction + embedding creation (on cache miss)
        parallel_start = _time.time()
        
        if cached_embedding:
            # Cache hit: Only need filter extraction (fast)
            query_vector = cached_embedding
            metadata_filters = extract_filters_from_query(question)
            print(f"⚡ [CACHE HIT] Using cached embedding, filters extracted in {_time.time() - parallel_start:.3f}s")
        else:
            # Cache miss: Run filter extraction + embedding in PARALLEL
            print(f"🔄 [PARALLEL] Running filter extraction + embedding concurrently...")
            
            def create_embedding():
                response = openai.embeddings.create(
                    input=question,
                    model="text-embedding-3-large"
                )
                return response.data[0].embedding
            
            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    filter_future = executor.submit(extract_filters_from_query, question)
                    embed_future = executor.submit(create_embedding)
                    
                    # Collect results (waits for both to complete)
                    metadata_filters = filter_future.result(timeout=5.0)  # Filters should be instant
                    query_vector = embed_future.result(timeout=30.0)  # Embedding might take longer
                
                # Cache the embedding for future use
                cache_embedding(question, query_vector)
                parallel_time = _time.time() - parallel_start
                print(f"✅ [PARALLEL] Completed in {parallel_time:.2f}s (filter + embedding concurrent)")
            except Exception as e:
                # Fallback to sequential on parallel failure
                print(f"⚠️ [PARALLEL] Failed ({e}), falling back to sequential...")
                metadata_filters = extract_filters_from_query(question)
                response = openai.embeddings.create(input=question, model="text-embedding-3-large")
                query_vector = response.data[0].embedding
                cache_embedding(question, query_vector)
        
        # Single query mode (no expansion for speed)
        print(f"⚡ [SPEED MODE] Using single query (no expansion) for fastest response")
        
        # Optimized retrieval (top_k=15) - we only use 8 chunks, buffer for filtering
        all_chunks = {}  # Deduplicate by text
        
        # Process the single query
        for query_idx, query in enumerate([question], 1):
            if progress_callback:
                progress_callback(f"searching_pinecone")
            
            # Query Pinecone with INCREASED top_k for hybrid approach + metadata filters
            query_params = {
                "vector": query_vector,
                "top_k": 15,
                "include_metadata": True
            }
            
            # FEATURE #1: Apply metadata filters if extracted
            if metadata_filters:
                query_params["filter"] = metadata_filters
                print(f"🎯 [METADATA-FILTER] Applying filters to query #{query_idx}: {metadata_filters}")
            
            pinecone_start = _time.time()
            print(f"📡 [CLAUDE DEBUG] Querying Pinecone with top_k=15...")
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
                
                # Wrap Pinecone query with 10-second timeout
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        pinecone_index.query,
                        **query_params
                    )
                    query_response = future.result(timeout=10.0)
                pinecone_time = _time.time() - pinecone_start
                print(f"⏱️ [TIMING] Pinecone query took {pinecone_time:.2f}s")
            except (FuturesTimeoutError, TimeoutError) as e:
                print(f"⏱️ [CLAUDE DEBUG] Pinecone query #{query_idx} timed out after 10 seconds")
                continue  # Skip this query and try next one
            
            # Extract and deduplicate contexts
            try:
                matches = query_response.matches
            except AttributeError:
                matches = query_response.get("matches", [])
            
            print(f"📊 [CLAUDE DEBUG] Query #{query_idx} returned {len(matches)} matches")
            if matches:
                print(f"   Top match score: {matches[0].score:.4f}")
                print(f"   Lowest match score: {matches[-1].score:.4f}")
            
            # Extract ALL metadata (including 10 enriched fields)
            enriched_results = extract_all_metadata(matches)
            
            for result in enriched_results:
                text = result['text']
                if text and text not in all_chunks:
                    all_chunks[text] = result
        
        if not all_chunks:
            print("❌ [CLAUDE DEBUG] No chunks found! Returning empty message.")
            return "No relevant MBTI content found in knowledge base."
        
        # IMPROVEMENT 3: Metadata-boosted re-ranking
        # Sort by base score, apply metadata boosts, re-sort, take top 12
        sorted_chunks = sorted(all_chunks.values(), key=lambda x: x["score"], reverse=True)[:20]  # Get top 20 first
        
        print(f"📚 [CLAUDE DEBUG] Total unique chunks collected: {len(all_chunks)}")
        print(f"🔄 [CLAUDE DEBUG] Applying metadata-boosted re-ranking...")
        
        # Apply intelligent re-ranking
        reranked_chunks = rerank_chunks_with_metadata(sorted_chunks, question)
        
        # ENTERPRISE MODE: Skip GPT re-ranking entirely (saves 8-10s)
        # Metadata boosting provides 80% of the quality benefit at zero latency cost
        # GPT re-ranking was adding 8-10s for marginal improvement
        # SPEED OPTIMIZATION: Reduced from 12 to 8 chunks (saves ~5s Claude processing)
        final_chunks = reranked_chunks[:8]  # Use metadata-boosted chunks directly
        top_3_avg_score = sum(c.get('boosted_score', c.get('score', 0.0)) for c in final_chunks[:3]) / 3
        print(f"⚡ [CLAUDE DEBUG] Using metadata-boosted chunks (avg score: {top_3_avg_score:.3f}) - GPT re-ranking disabled for speed")
        
        # Log boost details
        boosted_count = sum(1 for c in final_chunks if c.get('boost_applied', 0) > 0)
        print(f"📈 [CLAUDE DEBUG] {boosted_count}/{len(final_chunks)} chunks received metadata boost")
        if boosted_count > 0:
            avg_boost = sum(c.get('boost_applied', 0) for c in final_chunks) / len(final_chunks)
            print(f"📈 [CLAUDE DEBUG] Average boost: +{avg_boost:.3f}")
        
        print(f"📚 [CLAUDE DEBUG] Top 8 chunks selected for context")
        print(f"📚 [CLAUDE DEBUG] Sample sources: {', '.join(set([c.get('season', 'Unknown') for c in final_chunks[:5] if c.get('season')]))}")
        
        # FEATURE #4: Calculate confidence score
        confidence = calculate_confidence_score(final_chunks, question)
        print(f"📊 [CONFIDENCE] {confidence['stars']} {confidence['level']} ({confidence['score']:.2f}) - {confidence['reasoning']}")
        
        # FEATURE #4: Format citations for display
        citations_text = format_citations(final_chunks)
        
        # Build structured citations data for frontend
        citations_data = {
            "sources": [
                {
                    "season": chunk.get('season', chunk.get('metadata', {}).get('season', 'Unknown')),
                    "filename": chunk.get('filename', chunk.get('metadata', {}).get('filename', 'Unknown')),
                    "score": chunk.get('score', chunk.get('boosted_score', 0.0))
                }
                for chunk in final_chunks[:5]  # Top 5 sources
            ],
            "confidence": {
                "level": confidence['level'],
                "score": confidence['score'],
                "stars": confidence['stars'],
                "reasoning": confidence['reasoning']
            }
        }
        
        # Format with professional structure
        result = format_rag_context_professional(final_chunks)
        
        # Append confidence and citations to context (Claude will include in response)
        result += f"\n\n---\n**Retrieval Confidence:** {confidence['stars']} {confidence['level'].replace('_', ' ').title()} *{confidence['reasoning']}*\n**Sources:**\n{citations_text}"
        
        print(f"✅ [CLAUDE DEBUG] Returning structured context ({len(result)} chars)")
        
        # Return tuple: (context_string, citations_data)
        return result, citations_data
        
    except Exception as e:
        print(f"❌ [CLAUDE DEBUG] Pinecone query error: {str(e)}")
        import traceback
        print(f"❌ [CLAUDE DEBUG] Full traceback:\n{traceback.format_exc()}")
        return ""

def search_web_brave(query: str) -> str:
    """Search the web using Brave Search API for current information"""
    import httpx
    
    if not BRAVE_API_KEY:
        print("⚠️ BRAVE_API_KEY not set, web search unavailable")
        return "Web search is not configured. Please add a Brave Search API key."
    
    try:
        print(f"🌐 Searching web via Brave API: {query}")
        
        headers = {
            'X-Subscription-Token': BRAVE_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'q': query,
            'count': 5,
            'text_decorations': False,
            'search_lang': 'en'
        }
        
        response = httpx.get(
            'https://api.search.brave.com/res/v1/web/search',
            headers=headers,
            params=params,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Extract web results
            web_results = data.get('web', {}).get('results', [])
            
            for result in web_results[:5]:
                title = result.get('title', '')
                description = result.get('description', '')
                url = result.get('url', '')
                
                if description:
                    results.append(f"{title}\n{description}\nSource: {url}")
            
            if results:
                print(f"✅ Brave Search found {len(results)} results")
                return "\n\n---\n\n".join(results)
            else:
                return f"No web results found for '{query}'."
        
        elif response.status_code == 429:
            return "Rate limit reached. Please try again in a moment."
        
        elif response.status_code == 401:
            return "API key invalid. Please check your Brave Search API key."
        
        else:
            print(f"❌ Brave API error {response.status_code}: {response.text}")
            return f"Web search temporarily unavailable (Error {response.status_code})."
    
    except Exception as e:
        print(f"❌ Web search error: {str(e)}")
        return "Unable to perform web search at this time."

def make_together_api_call_with_retry(client, **kwargs):
    """
    Make Together.ai API call with exponential backoff retry logic for errors.
    Retries: 2s wait, then 4s wait. Max 3 attempts total.
    """
    max_retries = 2
    retry_delays = [2, 4]  # Exponential backoff: 2s, then 4s
    
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return response
        
        except Exception as e:
            error_message = str(e).lower()
            is_retriable = 'overloaded' in error_message or 'rate' in error_message or '503' in error_message or '529' in error_message
            
            if is_retriable and attempt < max_retries:
                wait_time = retry_delays[attempt]
                print(f"⚠️ Together API error (attempt {attempt + 1}/{max_retries + 1}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            # If not retriable or max retries reached, re-raise
            if is_retriable:
                raise Exception("Together API is temporarily busy. Please try again in a moment.")
            else:
                raise
    
    # This shouldn't be reached, but just in case
    raise Exception("Together API is temporarily busy. Please try again in a moment.")

def chat_with_claude(messages: List[Dict[str, str]], conversation_id: int) -> tuple[str, List[Dict]]:
    """
    Send messages to Claude and get response with automatic InnerVerse backend queries
    Returns: (response_text, tool_use_details)
    """
    if not TOGETHER_API_KEY:
        raise Exception("TOGETHER_API_KEY not set")
    
    client = OpenAI(
        api_key=TOGETHER_API_KEY,
        base_url="https://api.together.xyz/v1"
    )
    
    # OpenAI function calling format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_reference_data",
                "description": "Get exact MBTI type structures like four sides mappings, cognitive function stacks, temperaments, and quadra assignments. Use this FIRST for factual lookup questions about type structures (e.g., 'What are INFJ's four sides?', 'ENFP function stack', 'INTJ temperament'). Returns verified reference data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type_code": {
                            "type": "string",
                            "description": "The MBTI type code in uppercase (e.g., INFJ, ENFP, ISTJ, ENTP)"
                        }
                    },
                    "required": ["type_code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_innerverse_backend",
                "description": "Search the InnerVerse knowledge base containing 183+ CS Joseph YouTube transcripts on MBTI, Jungian psychology, cognitive functions, and type theory. Use this when the user asks MBTI/psychology questions that need examples, context, or detailed explanations beyond basic type structures.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to search for in the MBTI knowledge base."
                        }
                    },
                    "required": ["question"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for current information, facts, news, or general knowledge not in the MBTI knowledge base. Use this for restaurants, locations, current events, general facts, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for public information"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # Build system prompt with all 3 layers using centralized prompt builder
    # This ensures reference data injection is structurally enforced
    last_user_message_content = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_message_content = msg.get('content')
            break
    
    try:
        system_message, prompt_metadata = build_system_prompt(
            conversation_id=conversation_id,
            user_message=last_user_message_content or ""
        )
    except PromptAssemblyError as e:
        error_msg = f"Prompt assembly failed: {e}"
        print(f"❌ [PROMPT BUILDER] {error_msg}")
        return (error_msg, [])
    
    tool_use_details = []
    max_iterations = 3
    
    # Convert messages to OpenAI format with system message
    openai_messages = [{"role": "system", "content": system_message}]
    for msg in messages:
        openai_messages.append({"role": msg.get("role"), "content": msg.get("content")})
    
    for iteration in range(max_iterations):
        try:
            response = make_together_api_call_with_retry(
                client,
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                max_tokens=4096,
                messages=openai_messages,
                tools=tools,
                timeout=60.0
            )
        except Exception as e:
            # Catch user-friendly error messages from retry logic
            error_msg = str(e)
            if "temporarily busy" in error_msg.lower():
                # Return the user-friendly message to the frontend
                return (error_msg, tool_use_details, None)
            else:
                # Re-raise other unexpected errors
                raise
        
        # Log API usage
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            # Together.ai Llama 3.3 70B pricing: ~$0.88/M input, $0.88/M output
            cost = (input_tokens / 1000000 * 0.88) + (output_tokens / 1000000 * 0.88)
            
            # Import log function from main.py
            try:
                from main import log_api_usage
                log_api_usage("together_chat", "llama-3.3-70b", input_tokens, output_tokens, cost)
            except Exception as e:
                print(f"⚠️ Could not log Together usage: {e}")
        
        choice = response.choices[0]
        finish_reason = choice.finish_reason
        
        if finish_reason == "stop":
            # Normal completion
            full_text = choice.message.content or ""
            follow_up_question = extract_follow_up_question(full_text)
            
            # Remove the [FOLLOW-UP: ...] from the main text
            main_text = full_text
            if follow_up_question:
                import re
                follow_up_match = re.search(r'\[FOLLOW-UP:\s*(.+?)\]', full_text, re.IGNORECASE)
                if follow_up_match:
                    main_text = full_text[:follow_up_match.start()].strip()
            
            return (main_text, tool_use_details, follow_up_question)
        
        elif finish_reason == "tool_calls":
            # Handle tool calls
            tool_calls = choice.message.tool_calls or []
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                    
                if tool_name == "query_reference_data":
                    type_code = tool_input.get("type_code", "").upper()
                    print(f"📖 [REFERENCE DATA] Looking up type: {type_code}")
                    
                    # Lookup in reference data using same loader as type_injection
                    type_data = get_type_stack(type_code)
                    
                    if type_data:
                        # Extract four sides data properly
                        four_sides = type_data.get("four_sides", {})
                        
                        # Extract type codes from each side
                        ego_type = four_sides.get('ego', {}).get('type', 'Unknown')
                        shadow_type = four_sides.get('shadow', {}).get('type', 'Unknown')
                        subconscious_type = four_sides.get('subconscious', {}).get('type', 'Unknown')
                        superego_type = four_sides.get('superego', {}).get('type', 'Unknown')
                        
                        # Format functions for each side
                        def format_functions(funcs):
                            return '\n'.join([f"  • {f.get('position', 'Unknown')}: {f.get('function', 'Unknown')}" for f in funcs])
                        
                        # Build formatted response
                        result_text = f"""**{type_code} Complete Type Information:**

🎭 **Ego ({ego_type}):**
{format_functions(four_sides.get('ego', {}).get('functions', []))}

👥 **Shadow ({shadow_type}):**
{format_functions(four_sides.get('shadow', {}).get('functions', []))}

🔄 **Subconscious ({subconscious_type}):**
{format_functions(four_sides.get('subconscious', {}).get('functions', []))}

⚡ **Superego ({superego_type}):**
{format_functions(four_sides.get('superego', {}).get('functions', []))}

**Categories:**
• Temperament: {type_data.get('categories', {}).get('temperament', 'Unknown')}
• Quadra: {type_data.get('categories', {}).get('quadra', 'Unknown')}
• Interaction Style: {type_data.get('categories', {}).get('interaction_style', 'Unknown')}
• Temple: {type_data.get('categories', {}).get('temple', 'Unknown')}"""
                        
                        print(f"✅ [REFERENCE DATA] Found and formatted data for {type_code}")
                    else:
                        result_text = f"No reference data found for type: {type_code}"
                        print(f"❌ [REFERENCE DATA] No data for {type_code}")
                    
                    tool_use_details.append({
                        "tool": "query_reference_data",
                        "type_code": type_code,
                        "found": bool(type_data)
                    })
                    
                    # OpenAI format: add assistant message with tool_calls, then tool result
                    openai_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": tool_name, "arguments": tool_call.function.arguments}}]
                    })
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text
                    })
                
                elif tool_name == "query_innerverse_backend":
                    question = tool_input.get("question", "")
                    print(f"🔍 Querying InnerVerse Pinecone (local) for: {question}")
                    
                    result = query_innerverse_local(question)
                    # Handle tuple return (context, citations_data) or string (backwards compat)
                    if isinstance(result, tuple):
                        backend_result, _ = result  # Citations not used in non-streaming mode
                    else:
                        backend_result = result
                    
                    tool_use_details.append({
                        "tool": "query_innerverse_backend",
                        "question": question,
                        "result_length": len(backend_result)
                    })
                    
                    # OpenAI format: add assistant message with tool_calls, then tool result
                    openai_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": tool_name, "arguments": tool_call.function.arguments}}]
                    })
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": backend_result if backend_result else "No relevant content found in knowledge base."
                    })
                
                elif tool_name == "search_web":
                    query = tool_input.get("query", "")
                    print(f"🌐 Searching web for: {query}")
                    
                    web_result = search_web_brave(query)
                    
                    tool_use_details.append({
                        "tool": "search_web",
                        "query": query,
                        "result_length": len(web_result)
                    })
                    
                    # OpenAI format: add assistant message with tool_calls, then tool result
                    openai_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": tool_name, "arguments": tool_call.function.arguments}}]
                    })
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": web_result
                    })
            continue
        
        else:
            return "I encountered an error processing your request.", tool_use_details, None
    
    return "I reached the maximum number of processing steps. Please try rephrasing your question.", tool_use_details, None


def chat_with_claude_streaming(messages: List[Dict[str, str]], conversation_id: int):
    """
    Send messages to Claude with STREAMING enabled for real-time response display
    Yields chunks as they arrive from Claude
    RETURNS: Yields SSE events, final event includes follow-up question if present
    
    PERFORMANCE OPTIMIZATION (Dec 2024):
    - Pre-fetch RAG context BEFORE Claude call to eliminate tool use round-trip
    - This reduces response time from ~30-40s to ~15-20s
    - Tools kept as fallback for edge cases (web search, explicit reference lookups)
    
    STREAMING FIX (Dec 2024):
    - Use async RAG search to prevent blocking
    - Send heartbeat events to keep connection alive and show progress
    """
    # json is imported at module level (line 9)
    import time
    start_time = time.time()
    
    if not TOGETHER_API_KEY:
        yield "data: " + '{"error": "TOGETHER_API_KEY not set"}\n\n'
        return
    
    client = OpenAI(
        api_key=TOGETHER_API_KEY,
        base_url="https://api.together.xyz/v1"
    )
    full_response_text = []  # Accumulate response for follow-up extraction
    citations_data = None  # Store citations from RAG query
    
    # Extract last user message for RAG pre-fetch
    last_user_message_content = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_message_content = msg.get('content')
            # Handle content that might be a list
            if isinstance(last_user_message_content, list):
                for block in last_user_message_content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        last_user_message_content = block.get('text', '')
                        break
            break
    
    # Send initial status immediately - this MUST be yielded first to establish SSE connection
    yield "data: " + '{"status": "searching"}\n\n'
    
    # PRE-FETCH RAG CONTEXT: Do RAG search BEFORE Claude call
    # This eliminates the tool use round-trip (saves ~10-15s)
    rag_context = ""
    if last_user_message_content:
        print(f"⚡ [PRE-FETCH] Starting RAG search BEFORE Claude call...")
        rag_start = time.time()
        
        try:
            result = query_innerverse_local(last_user_message_content)
            
            # Handle tuple return (context, citations_data) or string
            if isinstance(result, tuple):
                rag_context, citations_data = result
            else:
                rag_context = result
                citations_data = None
            
            rag_time = time.time() - rag_start
            print(f"✅ [PRE-FETCH] RAG search completed in {rag_time:.1f}s ({len(rag_context)} chars)")
        except Exception as e:
            print(f"⚠️ [PRE-FETCH] RAG search failed: {e}")
            rag_context = ""
    
    # Send status update after RAG completes
    yield "data: " + '{"status": "generating"}\n\n'
    
    # Tools kept as FALLBACK only (web search, explicit reference lookups) - OpenAI function format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_reference_data",
                "description": "Get exact MBTI type structures like four sides mappings, cognitive function stacks, temperaments, and quadra assignments. Use this ONLY if you need to verify specific type data not already provided in context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type_code": {
                            "type": "string",
                            "description": "The MBTI type code in uppercase (e.g., INFJ, ENFP, ISTJ, ENTP)"
                        }
                    },
                    "required": ["type_code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for current information, facts, news, or general knowledge not in the MBTI knowledge base. Use this for restaurants, locations, current events, general facts, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query for public information"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    # Build system prompt with all 3 layers using centralized prompt builder
    try:
        system_message, prompt_metadata = build_system_prompt(
            conversation_id=conversation_id,
            user_message=last_user_message_content or ""
        )
    except PromptAssemblyError as e:
        error_msg = f"Prompt assembly failed: {e}"
        print(f"❌ [PROMPT BUILDER] {error_msg}")
        yield "data: " + json.dumps({"error": error_msg}) + "\n\n"
        return
    
    # INJECT PRE-FETCHED RAG CONTEXT into system prompt
    if rag_context:
        rag_injection = f"""

KNOWLEDGE BASE EXCERPTS
Priority: For cognitive function stacks and four sides mappings, ALWAYS use the AUTHORITATIVE REFERENCE DATA above. Use these excerpts for context and examples only.

{rag_context}
"""
        system_message = system_message + rag_injection
        print(f"✅ [INJECTION] Added {len(rag_context)} chars of RAG context to system prompt")
    
    max_iterations = 3
    
    # Convert messages to OpenAI format with system message
    openai_messages = [{"role": "system", "content": system_message}]
    for msg in messages:
        openai_messages.append({"role": msg.get("role"), "content": msg.get("content")})
    
    try:
        for iteration in range(max_iterations):
            # Send search status to frontend (only for tool use iterations)
            if iteration > 0:
                yield "data: " + '{"status": "searching"}\n\n'
            
            # OpenAI streaming format
            stream = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                max_tokens=4096,
                messages=openai_messages,
                tools=tools,
                stream=True,
                timeout=60.0
            )
            
            collected_tool_calls = []
            current_tool_call = None
            
            for chunk in stream:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                
                # Handle text content streaming
                if delta.content:
                    text_chunk = delta.content
                    full_response_text.append(text_chunk)
                    yield "data: " + json.dumps({"chunk": text_chunk}) + "\n\n"
                
                # Handle tool calls (accumulate them)
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        if tool_call_delta.index is not None:
                            # New tool call or continuing existing one
                            while len(collected_tool_calls) <= tool_call_delta.index:
                                collected_tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                            
                            tc = collected_tool_calls[tool_call_delta.index]
                            if tool_call_delta.id:
                                tc["id"] = tool_call_delta.id
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    tc["function"]["name"] = tool_call_delta.function.name
                                if tool_call_delta.function.arguments:
                                    tc["function"]["arguments"] += tool_call_delta.function.arguments
                
                # Handle finish
                if finish_reason == "tool_calls":
                    # Process tool calls
                    for tc in collected_tool_calls:
                        tool_name = tc["function"]["name"]
                        try:
                            tool_input = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            tool_input = {}
                        
                        if tool_name == "query_reference_data":
                            type_code = tool_input.get("type_code", "").upper()
                            yield "data: " + '{"status": "looking_up_reference"}\n\n'
                            type_data = get_type_stack(type_code)
                            
                            if type_data:
                                result_text = json.dumps(type_data, indent=2)
                                print(f"✅ [REFERENCE DATA STREAMING] Found data for {type_code}")
                            else:
                                result_text = f"No reference data found for type: {type_code}"
                                print(f"❌ [REFERENCE DATA STREAMING] No data for {type_code}")
                            
                            # OpenAI format: add assistant message with tool_calls, then tool result
                            openai_messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tool_name, "arguments": tc["function"]["arguments"]}}]
                            })
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result_text
                            })
                        
                        elif tool_name == "search_web":
                            query = tool_input.get("query", "")
                            yield "data: " + '{"status": "searching_web"}\n\n'
                            web_result = search_web_brave(query)
                            
                            # OpenAI format: add assistant message with tool_calls, then tool result
                            openai_messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tool_name, "arguments": tc["function"]["arguments"]}}]
                            })
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": web_result
                            })
                    
                    # Continue to next iteration
                    break
                
                elif finish_reason == "stop":
                    # Done! Extract follow-up and send done payload
                    follow_up = extract_follow_up_question("".join(full_response_text))
                    done_payload = {"done": True, "follow_up": follow_up}
                    if citations_data:
                        done_payload["citations"] = citations_data
                    
                    # Log total time
                    total_time = time.time() - start_time
                    print(f"⏱️ [TOTAL TIME] Response completed in {total_time:.1f}s")
                    
                    yield "data: " + json.dumps(done_payload) + "\n\n"
                    return
    
        # Max iterations reached - send done with follow-up
        follow_up = extract_follow_up_question("".join(full_response_text))
        done_payload = {"done": True, "follow_up": follow_up}
        if citations_data:
            done_payload["citations"] = citations_data
        
        # Log total time
        total_time = time.time() - start_time
        print(f"⏱️ [TOTAL TIME] Response completed in {total_time:.1f}s (max iterations)")
        
        yield "data: " + json.dumps(done_payload) + "\n\n"
    
    except Exception as e:
        error_msg = str(e)
        total_time = time.time() - start_time
        print(f"❌ Together streaming error after {total_time:.1f}s: {error_msg}")
        yield "data: " + json.dumps({"error": f"Sorry, I encountered an error: {error_msg}. Please try again."}) + "\n\n"
