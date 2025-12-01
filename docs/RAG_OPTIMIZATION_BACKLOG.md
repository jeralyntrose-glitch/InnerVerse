# RAG Performance Optimization Backlog

**Status:** Future Enhancements (After Phase 1-2 Complete)  
**Priority:** P2 (Performance Optimization)  
**Owner:** TBD

---

## Current Performance Baseline

**Current Response Time:** ~5-8 seconds
- Embedding: ~0.5s
- Pinecone search: ~0.5s
- Chunk retrieval: ~0.5s
- Confidence calculation: ~0.3s
- Citation formatting: ~0.3s
- Claude processing: ~2-3s
- Generation: ~2-3s

**Goal:** Reduce to 3-5 seconds (40% improvement)

---

## Optimization Ideas

### 1. Cache Embeddings for Common Questions

**Problem:** Every question gets re-embedded, even if asked before

**Solution:**
```python
# Pseudo-code
embedding_cache = {}

def get_embedding_cached(text):
    if text in embedding_cache:
        return embedding_cache[text]
    
    embedding = openai.embeddings.create(text)
    embedding_cache[text] = embedding
    return embedding
```

**Expected Gain:** -0.5s for cached questions  
**Effort:** 2 hours  
**Risk:** Low

---

### 2. Parallel Processing (Embed + Search Simultaneously)

**Problem:** Currently sequential: embed → wait → search → wait

**Solution:**
```python
import asyncio

async def rag_search(query):
    # Run these in parallel
    embedding_task = asyncio.create_task(get_embedding(query))
    metadata_task = asyncio.create_task(extract_filters(query))
    
    embedding, filters = await asyncio.gather(embedding_task, metadata_task)
    
    # Then search
    results = await pinecone_search(embedding, filters)
```

**Expected Gain:** -0.3s (overlap operations)  
**Effort:** 4 hours  
**Risk:** Medium (async complexity)

---

### 3. Streaming Citations (Show Sources As Found)

**Problem:** User waits for entire response before seeing sources

**Solution:**
- Retrieve chunks → Send citations data FIRST via SSE
- Frontend shows sources immediately
- Then stream the actual answer
- User sees "thinking with these sources..." perception

**Expected Gain:** -0s actual time, but FEELS faster (psychological)  
**Effort:** 6 hours  
**Risk:** Medium (requires SSE changes)

---

### 4. Reduce Chunk Count (Top 5 Instead of Top 10)

**Problem:** Retrieving/processing more chunks than needed

**Solution:**
```python
# Current
results = pinecone.query(top_k=10)

# Optimized
results = pinecone.query(top_k=5)  # Sufficient for most queries
```

**Expected Gain:** -0.2s (less data transfer + processing)  
**Effort:** 5 minutes (just change parameter)  
**Risk:** Low (may reduce answer quality slightly - test first!)

---

### 5. Embedding Model Optimization

**Problem:** text-embedding-3-large is powerful but slow

**Solution:**
- Use text-embedding-3-small for less critical queries
- Or use text-embedding-ada-002 (faster, cheaper, slightly less accurate)
- Route based on query complexity

**Expected Gain:** -0.3s for simple queries  
**Effort:** 3 hours  
**Risk:** Medium (accuracy tradeoff)

---

### 6. Confidence Calculation Optimization

**Problem:** Calculating confidence for every chunk/query

**Solution:**
- Pre-calculate confidence thresholds
- Use simpler heuristics (avg score > 0.85 = high)
- Skip complex scoring for obvious high/low cases

**Expected Gain:** -0.2s  
**Effort:** 2 hours  
**Risk:** Low

---

## Priority Order (When Ready)

**Phase 1 (Quick Wins):**
1. Reduce chunk count (5 min) - Test quality impact first
2. Cache embeddings (2 hours) - Easy, high impact

**Phase 2 (Medium Effort):**
3. Parallel processing (4 hours) - Async optimization
4. Confidence optimization (2 hours) - Simplify scoring

**Phase 3 (Advanced):**
5. Streaming citations (6 hours) - Requires SSE rework
6. Embedding model routing (3 hours) - Complexity-based selection

---

## Success Metrics

**Before:** 5-8 seconds average  
**After Phase 1:** 4-6 seconds (20-25% improvement)  
**After Phase 2:** 3.5-5 seconds (30-40% improvement)  
**After Phase 3:** 3-4 seconds (40-50% improvement)

**Target:** Stay under 5 seconds for 90% of queries

---

## Notes

- Don't optimize prematurely - wait until Phase 1-2 complete
- Measure actual performance before/after each optimization
- User perception matters - streaming can make slow feel fast
- Accuracy > Speed (don't sacrifice quality for milliseconds)

---

**Last Updated:** Dec 1, 2025  
**Status:** Backlog (not started)

