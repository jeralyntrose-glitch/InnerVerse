"""
InnerVerse Query Intelligence Module
VERIFIED against live Pinecone metadata on 2025-11-20

Provides intent detection, entity extraction, and metadata filter building
for intelligent Pinecone queries using ACTUAL metadata values.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class QueryConfig:
    """Configuration for query intelligence - VERIFIED VALUES"""
    # Increase from 5 to 50 for better recall (0.6% of 7,890-vector corpus)
    # Note: Index has 7,890 vectors, not 340 docs
    DEFAULT_TOP_K = 50
    # Return top 10 after re-ranking
    FINAL_RESULTS = 10
    # Minimum similarity score threshold
    MIN_SCORE_THRESHOLD = 0.60  # Lowered from 0.65 to avoid over-filtering
    # Minimum intent confidence to apply smart filters
    MIN_CONFIDENCE_FOR_FILTERS = 0.6
    
    # Score boosting multipliers
    BOOST_TITLE_MATCH = 1.5
    BOOST_EXACT_TYPE = 1.4
    BOOST_RELATIONSHIP_MATCH = 1.5
    BOOST_SEASON_MATCH = 1.3
    BOOST_FUNCTION_MATCH = 1.3

# ============================================================================
# INTENT DETECTION
# ============================================================================

class IntentDetector:
    """Detects user query intent to guide retrieval strategy"""
    
    INTENT_PATTERNS = {
        "compatibility": [
            r"compatible|compatibility|pair|pairing",
            r"golden|pedagogue|bronze|silver|dyad",
            r"romantic|sexual|social\s+compatib",
            r"work well|get along|match with",
            r"relationship.*type|type.*relationship"
        ],
        "type_lookup": [
            r"^what is\s+(an?\s+)?[A-Z]{4}\b",
            r"^tell me about\s+[A-Z]{4}",
            r"^explain\s+[A-Z]{4}",
            r"^describe\s+[A-Z]{4}",
            r"^[A-Z]{4}\s+personality",
            r"^how\s+(do|does)\s+[A-Z]{4}"
        ],
        "function_analysis": [
            r"\b(Ne|Ni|Se|Si|Te|Ti|Fe|Fi)\b",
            r"\b(hero|parent|child|inferior)\b.*function",
            r"\b(nemesis|critic|trickster|demon)\b",
            r"cognitive function|function stack",
            r"shadow function"
        ],
        "four_sides": [
            r"four sides|4 sides",
            r"\bego\b.*\b(type|side)",
            r"\bsubconscious\b",
            r"\bunconscious\b.*type",
            r"\bsuperego\b",
            r"aspirational|opposite\s+type"
        ],
        "development": [
            r"growth|develop|improve|mature|evolve",
            r"shadow work|integration|individuation",
            r"self-improvement|personal growth",
            r"become better|how to grow"
        ],
        "framework": [
            r"octagram|temple|quadra",
            r"interaction style|cognitive axis",
            r"deadly sin|holy virtue",
            r"temperament"
        ],
        "season_specific": [
            r"season\s+\d+",
            r"\[\d+\]|\[\d+\.\d+\]"
        ]
    }
    
    @classmethod
    def detect(cls, question: str) -> Tuple[str, float]:
        """
        Detect primary intent of question
        
        Returns:
            (intent_name, confidence_score)
        """
        question_lower = question.lower()
        scores = {}
        
        for intent, patterns in cls.INTENT_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                # Score based on percentage of patterns matched
                scores[intent] = matches / len(patterns)
        
        if not scores:
            return "general", 0.5
        
        # Return intent with highest score
        top_intent = max(scores.items(), key=lambda x: x[1])
        return top_intent[0], min(top_intent[1] * 2, 1.0)  # Scale confidence

# ============================================================================
# ENTITY EXTRACTION - VERIFIED VALUES
# ============================================================================

class EntityExtractor:
    """Extracts MBTI types, functions, and frameworks from questions"""
    
    # VERIFIED: ALL 23 values from types_discussed field (exact match)
    MBTI_TYPES = [
        # Standard 16 types
        "ENFP", "INFP", "ENFJ", "INFJ",
        "ENTP", "INTP", "ENTJ", "INTJ",
        "ESFP", "ISFP", "ESFJ", "ISFJ",
        "ESTP", "ISTP", "ESTJ", "ISTJ",
        # Typos found in metadata (preserve for matching)
        "ESFB", "ISFB",
        # Type groups found in metadata
        "NJs", "NPs", "SJs", "SPs",
        # Fallback value
        "none"
    ]
    
    # VERIFIED: From functions_covered field
    FUNCTIONS = ["Ne", "Ni", "Se", "Si", "Te", "Ti", "Fe", "Fi"]
    
    FUNCTION_POSITIONS = [
        "hero", "parent", "child", "inferior",
        "nemesis", "critic", "trickster", "demon"
    ]
    
    # VERIFIED: Only 4 relationship types exist in actual Pinecone metadata
    # User may use friendly names, we map them to metadata values
    RELATIONSHIP_TYPES = [
        "golden", "pedagogue", "bronze"
        # Note: silver, dyad, companion, etc. NOT found in metadata
    ]
    
    # VERIFIED: From quadra field - EXACT values from metadata
    QUADRAS = ["alpha", "beta", "gamma", "none"]  # Note: "delta" does NOT exist!
    
    # VERIFIED: From temple field - EXACT values from metadata  
    TEMPLES = ["heart", "mind", "soul", "none"]  # Note: "body" does NOT exist!
    
    FRAMEWORKS = [
        "four_sides", "four sides", "4 sides",
        "octagram", "temple", "quadra",
        "interaction_style", "interaction style",
        "cognitive_axis", "deadly_sins", "holy_virtues"
    ]
    
    @classmethod
    def extract_types(cls, question: str) -> List[str]:
        """Extract MBTI types from question"""
        found = []
        question_upper = question.upper()
        
        for mbti_type in cls.MBTI_TYPES:
            if re.search(rf'\b{mbti_type}\b', question_upper):
                found.append(mbti_type)
        
        return found
    
    @classmethod
    def extract_functions(cls, question: str) -> List[str]:
        """Extract cognitive functions from question"""
        found = []
        
        for func in cls.FUNCTIONS:
            if re.search(rf'\b{func}\b', question):
                found.append(func)
        
        return found
    
    @classmethod
    def extract_function_positions(cls, question: str) -> List[str]:
        """Extract function positions (hero, parent, etc.)"""
        found = []
        question_lower = question.lower()
        
        for position in cls.FUNCTION_POSITIONS:
            if position in question_lower:
                found.append(position)
        
        return found
    
    @classmethod
    def extract_relationships(cls, question: str) -> List[str]:
        """Extract relationship types from question"""
        found = []
        question_lower = question.lower()
        
        for rel in cls.RELATIONSHIP_TYPES:
            if rel in question_lower:
                found.append(rel)
        
        return found
    
    @classmethod
    def extract_quadra(cls, question: str) -> Optional[str]:
        """Extract quadra from question (returns lowercase to match Pinecone)"""
        question_lower = question.lower()
        
        for quadra in cls.QUADRAS:
            if quadra in question_lower:
                return quadra  # Return lowercase to match metadata
        
        return None
    
    @classmethod
    def extract_temple(cls, question: str) -> Optional[str]:
        """Extract temple from question (returns lowercase to match Pinecone)"""
        question_lower = question.lower()
        
        for temple in cls.TEMPLES:
            if temple in question_lower:
                return temple  # Return lowercase to match metadata
        
        return None
    
    @classmethod
    def extract_season(cls, question: str) -> Optional[str]:
        """Extract season number from question (returns string to match Pinecone)"""
        # Match "season 14", "Season 14", "[14]", etc.
        match = re.search(r'season\s+(\d+)', question, re.IGNORECASE)
        if match:
            return match.group(1)  # Return as string to match metadata
        
        # Match bracket notation [14.1]
        match = re.search(r'\[(\d+)', question)
        if match:
            return match.group(1)
        
        return None
    
    @classmethod
    def extract_all(cls, question: str) -> Dict[str, Any]:
        """Extract all entities from question"""
        return {
            "types": cls.extract_types(question),
            "functions": cls.extract_functions(question),
            "function_positions": cls.extract_function_positions(question),
            "relationships": cls.extract_relationships(question),
            "quadra": cls.extract_quadra(question),
            "temple": cls.extract_temple(question),
            "season": cls.extract_season(question)
        }

# ============================================================================
# METADATA FILTER BUILDER - USING CORRECT PINECONE OPERATORS
# ============================================================================

class FilterBuilder:
    """Builds Pinecone metadata filters using VERIFIED field types and operators"""
    
    @classmethod
    def build(
        cls,
        intent: str,
        entities: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """
        Build metadata filter for Pinecone query
        
        Args:
            intent: Detected query intent
            entities: Extracted entities from question
            confidence: Intent confidence score
        
        Returns:
            Pinecone filter dictionary (can be empty for no filtering)
        """
        # Conservative fallback: don't apply smart filters if confidence is low
        if confidence < QueryConfig.MIN_CONFIDENCE_FOR_FILTERS:
            logger.info(f"Low confidence ({confidence:.2f}), skipping smart filters")
            return {}
        
        filters = []
        
        # Season filter (highest priority - very specific)
        # VERIFIED: season is string type in Pinecone
        season = entities.get("season")
        if season:
            filters.append({"season": {"$eq": season}})
        
        # Type filters - PINECONE ARRAY SYNTAX: use $in to check if value is in array
        # ARCHITECT FIX: Only filter if types exist (avoids filtering out all docs when field missing)
        types = entities.get("types", [])
        if types:
            # Use $or to allow docs with missing field OR matching types
            filters.append({
                "$or": [
                    {"types_discussed": {"$in": types}},
                    {"types_discussed": {"$exists": False}}  # Include docs without this field
                ]
            })
        
        # Function filters - PINECONE ARRAY SYNTAX: use $in to check if value is in array
        # ARCHITECT FIX: Only filter if functions exist
        functions = entities.get("functions", [])
        if functions:
            filters.append({
                "$or": [
                    {"functions_covered": {"$in": functions}},
                    {"functions_covered": {"$exists": False}}
                ]
            })
        
        # Relationship type filter
        # VERIFIED: Only 4 values exist: golden_pair, pedagogue_pair, bronze_pair, none
        relationships = entities.get("relationships", [])
        if relationships:
            # Map user terms to actual Pinecone values (ONLY verified ones)
            rel_map = {
                "golden": "golden_pair",
                "gold": "golden_pair",      # Common abbreviation users say
                "pedagogue": "pedagogue_pair",
                "bronze": "bronze_pair"
            }
            # Filter out unmapped relationships (silver, dyad, etc. don't exist in metadata)
            mapped_rels = [rel_map[r] for r in relationships if r in rel_map]
            
            if len(mapped_rels) == 1:
                filters.append({"relationship_type": {"$eq": mapped_rels[0]}})
            elif len(mapped_rels) > 1:
                filters.append({"relationship_type": {"$in": mapped_rels}})
            # If no valid mappings, fall back to compatibility category filter (handled below)
        
        # Quadra filter (VERIFIED: lowercase values)
        quadra = entities.get("quadra")
        if quadra:
            filters.append({"quadra": {"$eq": quadra}})
        
        # Temple filter (VERIFIED: lowercase values)
        temple = entities.get("temple")
        if temple:
            filters.append({"temple": {"$eq": temple}})
        
        # Intent-specific category filters
        # VERIFIED: primary_category values from actual Pinecone data
        if intent == "compatibility" and not relationships:
            filters.append({
                "$or": [
                    {"primary_category": {"$eq": "compatibility"}},
                    {"primary_category": {"$eq": "relationships"}},
                    {"relationship_type": {"$ne": "none"}}
                ]
            })
        
        elif intent == "four_sides":
            filters.append({
                "$or": [
                    {"primary_category": {"$eq": "four_sides"}},
                    {"topics": {"$in": ["four_sides"]}}
                ]
            })
        
        elif intent == "function_analysis":
            filters.append({"primary_category": {"$eq": "cognitive_functions"}})
        
        # Combine filters
        if len(filters) == 0:
            return {}
        elif len(filters) == 1:
            return filters[0]
        else:
            return {"$and": filters}

# ============================================================================
# RESULT RE-RANKER
# ============================================================================

class ResultRanker:
    """Re-ranks Pinecone results using metadata relevance scoring"""
    
    @classmethod
    def rank(
        cls,
        matches: List[Any],
        question: str,
        intent: str,
        entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Re-rank results based on metadata relevance
        
        Args:
            matches: Pinecone query matches
            question: Original question
            intent: Detected intent
            entities: Extracted entities
        
        Returns:
            Re-ranked list of results with adjusted scores
        """
        question_lower = question.lower()
        question_words = set(question_lower.split())
        
        types = entities.get("types", [])
        functions = entities.get("functions", [])
        relationships = entities.get("relationships", [])
        season = entities.get("season")
        
        ranked_results = []
        
        for match in matches:
            # Handle both Match objects and dict responses
            if hasattr(match, 'metadata'):
                metadata = match.metadata
                score = float(match.score)
                match_id = match.id
            else:
                metadata = match.get('metadata', {})
                score = float(match.get('score', 0.0))
                match_id = match.get('id', '')
            
            original_score = score
            
            # ARCHITECT FIX: Clamp score to minimum epsilon to prevent zero-score issues
            MIN_SCORE = 0.01  # Small epsilon to maintain ordering
            score = max(score, MIN_SCORE)
            
            # BOOST 1: Title/filename contains query keywords
            filename = metadata.get('filename', '').lower()
            title_words = set(filename.replace('_', ' ').replace('-', ' ').split())
            keyword_overlap = len(question_words & title_words)
            if keyword_overlap >= 2:
                score *= QueryConfig.BOOST_TITLE_MATCH
            
            # BOOST 2: Exact type match in types_discussed
            doc_types = metadata.get('types_discussed', [])
            if types and any(t in doc_types for t in types):
                score *= QueryConfig.BOOST_EXACT_TYPE
            
            # BOOST 3: Relationship type match
            doc_rel = metadata.get('relationship_type', '')
            if relationships:
                for rel in relationships:
                    if rel in doc_rel.lower() or f"{rel}_pair" == doc_rel:
                        score *= QueryConfig.BOOST_RELATIONSHIP_MATCH
                        break
            
            # BOOST 4: Season match
            doc_season = str(metadata.get('season', ''))
            if season and doc_season == season:
                score *= QueryConfig.BOOST_SEASON_MATCH
            
            # BOOST 5: Function match
            doc_functions = metadata.get('functions_covered', [])
            if functions and any(f in doc_functions for f in functions):
                score *= QueryConfig.BOOST_FUNCTION_MATCH
            
            # BOOST 6: Intent-specific category match
            doc_category = metadata.get('primary_category', '')
            if intent == "compatibility" and doc_category in ['compatibility', 'relationships']:
                score *= 1.2
            elif intent == "four_sides" and doc_category == 'four_sides':
                score *= 1.3
            elif intent == "function_analysis" and doc_category == 'cognitive_functions':
                score *= 1.2
            
            ranked_results.append({
                'id': match_id,
                'score': score,
                'original_score': original_score,
                'metadata': metadata,
                'text': metadata.get('text', '')
            })
        
        # Sort by adjusted score (highest first)
        ranked_results.sort(key=lambda x: x['score'], reverse=True)
        
        return ranked_results

# ============================================================================
# MAIN QUERY INTELLIGENCE CLASS
# ============================================================================

class QueryIntelligence:
    """
    Main orchestrator for intelligent query processing.
    Combines intent detection, entity extraction, filter building, and re-ranking.
    """
    
    def __init__(self):
        self.intent_detector = IntentDetector()
        self.entity_extractor = EntityExtractor()
        self.filter_builder = FilterBuilder()
        self.result_ranker = ResultRanker()
    
    def analyze_query(self, question: str) -> Dict[str, Any]:
        """
        Analyze a query and return intelligence for Pinecone search
        
        Args:
            question: User's question
        
        Returns:
            {
                "intent": "compatibility",
                "confidence": 0.85,
                "entities": {...},
                "pinecone_filter": {...},
                "recommended_top_k": 40
            }
        """
        # Detect intent
        intent, confidence = self.intent_detector.detect(question)
        
        # Extract entities
        entities = self.entity_extractor.extract_all(question)
        
        # Build filter (with confidence check)
        pinecone_filter = self.filter_builder.build(intent, entities, confidence)
        
        # ARCHITECT FIX: Adaptive top_k to prevent rate limiting
        # Use higher top_k only when we have filters to narrow results
        # Otherwise stick to conservative values to avoid Pinecone rate limits
        has_filters = bool(pinecone_filter)
        
        if entities.get("season") or (entities.get("types") and entities.get("relationships")):
            # Very specific query with strong filters - moderate top_k
            recommended_top_k = 30
        elif has_filters:
            # Has metadata filters - can use higher top_k safely
            recommended_top_k = 40
        else:
            # No filters (general query) - use conservative top_k to avoid rate limits
            recommended_top_k = 20
        
        return {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "pinecone_filter": pinecone_filter,
            "recommended_top_k": recommended_top_k,
            "use_smart_filters": confidence >= QueryConfig.MIN_CONFIDENCE_FOR_FILTERS
        }
    
    def rerank_results(
        self,
        matches: List[Any],
        question: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Re-rank Pinecone results using metadata intelligence
        
        Args:
            matches: Raw Pinecone matches
            question: Original question
            analysis: Output from analyze_query()
        
        Returns:
            Re-ranked results (top FINAL_RESULTS count)
        """
        ranked = self.result_ranker.rank(
            matches,
            question,
            analysis["intent"],
            analysis["entities"]
        )
        
        # Filter by minimum score threshold
        filtered = [r for r in ranked if r['original_score'] >= QueryConfig.MIN_SCORE_THRESHOLD]
        
        # Return top N results
        return filtered[:QueryConfig.FINAL_RESULTS]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global instance for easy import
query_intelligence = QueryIntelligence()

def analyze_and_filter(question: str) -> Dict[str, Any]:
    """
    Convenience function to analyze query and get filter
    
    Usage in main.py:
        from src.services.query_intelligence import analyze_and_filter, rerank_results
        
        analysis = analyze_and_filter(question)
        # Use analysis['pinecone_filter'] in Pinecone query
        # Use analysis['recommended_top_k'] for top_k
    """
    return query_intelligence.analyze_query(question)

def rerank_results(matches: List[Any], question: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convenience function to re-rank results
    
    Usage in main.py:
        ranked_results = rerank_results(matches, question, analysis)
    """
    return query_intelligence.rerank_results(matches, question, analysis)
