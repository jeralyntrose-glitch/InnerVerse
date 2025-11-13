"""
YouTube Video Matching Service

Matches YouTube videos to lessons based on season number and title similarity.
Implements 2-stage matching: season filter → title similarity (70% threshold).
"""

import re
import csv
import io
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os

DATABASE_URL = os.getenv("DATABASE_URL")


@dataclass
class YouTubeVideo:
    """Represents a YouTube video from CSV"""
    season: str
    title: str
    category: str
    url: str
    video_id: str


@dataclass
class MatchResult:
    """Represents a match between video and lesson"""
    video: YouTubeVideo
    lesson_id: Optional[str]
    lesson_title: Optional[str]
    confidence_score: float
    match_type: str  # 'high', 'medium', 'low', 'unmatched'


class YouTubeMatcher:
    """Service for matching YouTube videos to lessons"""
    
    def __init__(self):
        """Initialize matcher"""
        self.high_threshold = 0.85
        self.medium_threshold = 0.70
        self.low_threshold = 0.50
    
    def extract_season_number(self, text: str) -> Optional[str]:
        """
        Extract season number from text.
        
        Patterns supported:
        - [1], [17.1], [20]
        - Season 1, Season 17.1
        - S01, S17.1
        
        Args:
            text: Text to extract season from
            
        Returns:
            Season number as string (e.g., "1", "17.1") or None
        """
        # Try bracket notation first [1], [17.1]
        bracket_match = re.search(r'\[(\d+(?:\.\d+)?)\]', text)
        if bracket_match:
            return bracket_match.group(1)
        
        # Try "Season X" notation
        season_match = re.search(r'Season\s+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if season_match:
            return season_match.group(1)
        
        # Try "SXX" notation
        s_match = re.search(r'S(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if s_match:
            return s_match.group(1)
        
        return None
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles (0-1).
        
        Uses SequenceMatcher for fuzzy matching.
        Case-insensitive, removes common noise words.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize titles
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)
        
        # Calculate similarity
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _normalize_title(self, title: str) -> str:
        """
        Normalize title for comparison.
        
        - Lowercase
        - Remove season numbers
        - Remove common noise words
        - Strip whitespace
        """
        # Lowercase
        title = title.lower()
        
        # Remove season brackets [1], [17.1]
        title = re.sub(r'\[\d+(?:\.\d+)?\]', '', title)
        
        # Remove noise words
        noise_words = ['the', 'a', 'an', 'and', 'or', 'but', '-', '–', '—']
        for word in noise_words:
            title = title.replace(f' {word} ', ' ')
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        return title.strip()
    
    def parse_youtube_url(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Supports formats:
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/watch?v=VIDEO_ID
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID
        """
        # youtu.be format
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        
        # youtube.com format
        match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        
        # Return original if no match
        return url
    
    def parse_csv(self, csv_content: str) -> List[YouTubeVideo]:
        """
        Parse CSV content into YouTubeVideo objects.
        
        Expected columns: season, title, category, url
        
        Args:
            csv_content: CSV string content
            
        Returns:
            List of YouTubeVideo objects
        """
        videos = []
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            video_id = self.parse_youtube_url(row['url'])
            videos.append(YouTubeVideo(
                season=row['season'],
                title=row['title'],
                category=row.get('category', ''),
                url=row['url'],
                video_id=video_id
            ))
        
        return videos
    
    def get_all_lessons(self) -> List[Dict]:
        """
        Fetch all lessons from database.
        
        Returns:
            List of lesson dictionaries with id, title, season
        """
        if not DATABASE_URL:
            print("⚠️ DATABASE_URL not set")
            return []
        
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT id, title, course_id, order_index
                FROM lessons
                ORDER BY course_id, order_index
            """)
            
            lessons = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(lesson) for lesson in lessons]
            
        except Exception as e:
            print(f"❌ Error fetching lessons: {e}")
            return []
    
    def match_video_to_lessons(
        self, 
        video: YouTubeVideo, 
        lessons: List[Dict]
    ) -> MatchResult:
        """
        Match a single video to lessons.
        
        Algorithm:
        1. Extract season from video title
        2. Filter lessons by matching season
        3. Calculate title similarity for each
        4. Return best match above threshold
        
        Args:
            video: YouTubeVideo to match
            lessons: List of lesson dicts
            
        Returns:
            MatchResult with best match or unmatched
        """
        # Extract season from video title
        video_season = self.extract_season_number(video.title)
        if not video_season and video.season:
            video_season = video.season
        
        best_match = None
        best_score = 0.0
        
        for lesson in lessons:
            # Extract season from lesson title
            lesson_season = self.extract_season_number(lesson['title'])
            
            # STRICT season-first filtering: videos WITH seasons ONLY match lessons with SAME season
            if video_season:
                # Normalize season numbers for comparison (1.0 == 1)
                if not lesson_season or float(video_season) != float(lesson_season):
                    continue
            
            # Calculate title similarity
            similarity = self.calculate_title_similarity(video.title, lesson['title'])
            
            if similarity > best_score:
                best_score = similarity
                best_match = lesson
        
        # Determine match type
        if best_score >= self.high_threshold:
            match_type = 'high'
        elif best_score >= self.medium_threshold:
            match_type = 'medium'
        elif best_score >= self.low_threshold:
            match_type = 'low'
        else:
            match_type = 'unmatched'
        
        return MatchResult(
            video=video,
            lesson_id=best_match['id'] if best_match else None,
            lesson_title=best_match['title'] if best_match else None,
            confidence_score=best_score,
            match_type=match_type
        )
    
    def process_csv_import(self, csv_content: str) -> Dict:
        """
        Process complete CSV import.
        
        Workflow:
        1. Parse CSV
        2. Fetch all lessons
        3. Match each video
        4. Insert high confidence → documents + lesson_documents
        5. Insert medium/low/unmatched → pending_youtube_videos
        
        Args:
            csv_content: CSV string content
            
        Returns:
            Summary dict with counts and results
        """
        print("🎬 Starting YouTube video import...")
        
        # Parse CSV
        videos = self.parse_csv(csv_content)
        print(f"📊 Parsed {len(videos)} videos from CSV")
        
        # Fetch lessons
        lessons = self.get_all_lessons()
        print(f"📚 Fetched {len(lessons)} lessons from database")
        
        # Match videos
        results = []
        for video in videos:
            match = self.match_video_to_lessons(video, lessons)
            results.append(match)
        
        # Categorize results
        high_confidence = [r for r in results if r.match_type == 'high']
        medium_confidence = [r for r in results if r.match_type == 'medium']
        low_confidence = [r for r in results if r.match_type == 'low']
        unmatched = [r for r in results if r.match_type == 'unmatched']
        
        print(f"✅ High confidence matches: {len(high_confidence)}")
        print(f"⚠️ Medium confidence matches: {len(medium_confidence)}")
        print(f"⚠️ Low confidence matches: {len(low_confidence)}")
        print(f"❌ Unmatched videos: {len(unmatched)}")
        
        # Insert into database
        self._insert_matches(high_confidence, auto_link=True)
        self._insert_matches(medium_confidence + low_confidence + unmatched, auto_link=False)
        
        return {
            'total': len(videos),
            'high_confidence': len(high_confidence),
            'medium_confidence': len(medium_confidence),
            'low_confidence': len(low_confidence),
            'unmatched': len(unmatched),
            'results': results
        }
    
    def _insert_matches(self, matches: List[MatchResult], auto_link: bool = False):
        """
        Insert matches into database.
        
        Args:
            matches: List of MatchResult objects
            auto_link: If True, create document + lesson_documents link
                      If False, insert into pending_youtube_videos
        """
        if not matches:
            return
        
        if not DATABASE_URL:
            print("⚠️ DATABASE_URL not set - skipping database insert")
            return
        
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            
            for match in matches:
                video = match.video
                
                if auto_link and match.lesson_id:
                    # Insert into documents table
                    cursor.execute("""
                        INSERT INTO documents (
                            doc_type, source_url, provider_video_id, title, 
                            season, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (provider_video_id) DO UPDATE
                        SET source_url = EXCLUDED.source_url,
                            title = EXCLUDED.title,
                            season = EXCLUDED.season,
                            metadata = EXCLUDED.metadata
                        RETURNING id
                    """, (
                        'youtube',
                        video.url,
                        video.video_id,
                        video.title,
                        video.season,
                        Json({'category': video.category, 'confidence': match.confidence_score})
                    ))
                    
                    document_id = cursor.fetchone()[0]
                    
                    # Insert into lesson_documents join table
                    cursor.execute("""
                        INSERT INTO lesson_documents (lesson_id, document_id, relationship_type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (lesson_id, document_id) DO NOTHING
                    """, (match.lesson_id, document_id, 'primary_resource'))
                    
                else:
                    # Insert into pending_youtube_videos
                    status = 'unmatched' if match.match_type == 'unmatched' else 'pending_review'
                    
                    cursor.execute("""
                        INSERT INTO pending_youtube_videos (
                            provider_video_id, source_url, title, season, category,
                            status, confidence_score, matched_lesson_id, raw_metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (provider_video_id) DO UPDATE
                        SET source_url = EXCLUDED.source_url,
                            title = EXCLUDED.title,
                            season = EXCLUDED.season,
                            category = EXCLUDED.category,
                            status = EXCLUDED.status,
                            confidence_score = EXCLUDED.confidence_score,
                            matched_lesson_id = EXCLUDED.matched_lesson_id,
                            raw_metadata = EXCLUDED.raw_metadata
                    """, (
                        video.video_id,
                        video.url,
                        video.title,
                        video.season,
                        video.category,
                        status,
                        match.confidence_score,
                        match.lesson_id,
                        Json({'match_type': match.match_type})
                    ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Inserted {len(matches)} {'linked documents' if auto_link else 'pending videos'}")
            
        except Exception as e:
            print(f"❌ Error inserting matches: {e}")
            if conn:
                conn.rollback()
