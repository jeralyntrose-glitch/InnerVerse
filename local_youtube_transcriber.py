#!/usr/bin/env python3
"""
InnerVerse - Local YouTube Transcriber
Run this on your laptop to transcribe YouTube videos without IP blocks!
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if required tools are installed"""
    print("🔍 Checking requirements...\n")
    
    missing = []
    
    # Check Python



    
    try:
        import openai
        print("✅ Python openai package installed")
    except ImportError:
        missing.append("openai")
        print("❌ Python openai package missing")
    
    # Check yt-dlp
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ yt-dlp installed (version {result.stdout.decode().strip()})")
        else:
            missing.append("yt-dlp")
            print("❌ yt-dlp not working")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        missing.append("yt-dlp")
        print("❌ yt-dlp not found")
    
    # Check ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ ffmpeg installed")
        else:
            missing.append("ffmpeg")
            print("❌ ffmpeg not working")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        missing.append("ffmpeg")
        print("❌ ffmpeg not found")
    
    try:
        from reportlab.lib.pagesizes import letter
        print("✅ ReportLab installed")
    except ImportError:
        missing.append("reportlab")
        print("❌ ReportLab missing")
    
    try:
        from pydub import AudioSegment
        print("✅ pydub installed")
    except ImportError:
        missing.append("pydub")
        print("❌ pydub missing")
    
    if missing:
        print(f"\n❌ Missing: {', '.join(missing)}")
        print("\nRun this command to install missing packages:")
        print(f"pip install {' '.join([p for p in missing if p not in ['yt-dlp', 'ffmpeg']])}")
        if 'yt-dlp' in missing:
            print("pip install yt-dlp")
        if 'ffmpeg' in missing:
            print("\nFor ffmpeg, visit: https://ffmpeg.org/download.html")
        return False
    
    print("\n✅ All requirements met!\n")
    return True

def transcribe_youtube(youtube_url, output_folder=None):
    """Download and transcribe a YouTube video"""
    
    # Default to iCloud Drive if available, otherwise use local transcriptions folder
    if output_folder is None:
        # Check for iCloud Drive (Mac)
        icloud_path = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/InnerVerse Transcriptions")
        local_path = "transcriptions"
        
        if os.path.exists(os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")):
            output_folder = icloud_path
            print(f"📱 Using iCloud Drive: {output_folder}\n")
        else:
            output_folder = local_path
            print(f"💾 Using local folder: {output_folder}\n")
    from openai import OpenAI
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from pydub import AudioSegment
    from datetime import datetime
    from zoneinfo import ZoneInfo
    import tempfile
    import time
    
    # Get OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables!")
        print("\nSet it with:")
        print("  Mac/Linux: export OPENAI_API_KEY='your-key-here'")
        print("  Windows:   set OPENAI_API_KEY=your-key-here")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Create output folder
    Path(output_folder).mkdir(exist_ok=True)
    
    print(f"🎥 Processing: {youtube_url}\n")
    
    # Check for cookies file
    cookies_file = None
    possible_cookie_paths = [
        "youtube_cookies.txt",
        os.path.expanduser("~/Desktop/youtube_cookies.txt"),
        os.path.join(os.path.dirname(__file__), "youtube_cookies.txt")
    ]
    
    for path in possible_cookie_paths:
        if os.path.exists(path):
            cookies_file = path
            print(f"🍪 Using cookies from: {path}\n")
            break
    
    # Step 1: Get video info
    print("📋 Getting video info...")
    try:
        info_cmd = ["yt-dlp", "--print", "%(title)s|||%(duration)s"]
        if cookies_file:
            info_cmd.extend(["--cookies", cookies_file])
        info_cmd.append(youtube_url)
        
        info_result = subprocess.run(
            info_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if info_result.returncode != 0:
            print(f"❌ Failed to get video info: {info_result.stderr}")
            return
        
        info_parts = info_result.stdout.strip().split("|||")
        video_title = info_parts[0] if len(info_parts) > 0 else "YouTube Video"
        video_duration = int(info_parts[1]) if len(info_parts) > 1 and info_parts[1].isdigit() else 0
        
        print(f"📺 Title: {video_title}")
        print(f"⏱️  Duration: {video_duration // 60} minutes {video_duration % 60} seconds\n")
        
    except Exception as e:
        print(f"❌ Error getting video info: {e}")
        return
    
    # Step 2: Download audio
    print("🎵 Downloading audio...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = os.path.join(temp_dir, "audio.mp3")
        
        try:
            download_cmd = [
                "yt-dlp",
                "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "--referer", "https://www.youtube.com/",
            ]
            
            if cookies_file:
                download_cmd.extend(["--cookies", cookies_file])
            
            download_cmd.extend([
                "-x",
                "--audio-format", "mp3",
                "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000 -b:a 32k",
                "-o", audio_path,
                youtube_url
            ])
            
            download_result = subprocess.run(
                download_cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if download_result.returncode != 0:
                print(f"❌ Download failed: {download_result.stderr}")
                return
            
            if not os.path.exists(audio_path):
                print("❌ Audio file not created")
                return
            
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {file_size_mb:.1f} MB\n")
            
        except subprocess.TimeoutExpired:
            print("❌ Download timed out (30 min limit)")
            return
        except Exception as e:
            print(f"❌ Download error: {e}")
            return
        
        # Step 3: Transcribe with Whisper
        print("🎤 Transcribing with Whisper API...")
        print("   (This costs ~$0.006 per minute of audio)\n")
        
        try:
            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Get audio duration for cost estimate
            audio = AudioSegment.from_file(audio_path)
            duration_minutes = len(audio) / (1000 * 60)
            estimated_cost = duration_minutes * 0.006
            
            print(f"💰 Estimated cost: ${estimated_cost:.3f}")
            
            # If file is under 25MB, transcribe directly
            if file_size < 25 * 1024 * 1024:
                print(f"📝 File size {file_size_mb:.1f}MB - transcribing directly\n")
                
                with open(audio_path, "rb") as audio_file:
                    transcript_response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                        timeout=600
                    )
                
                transcript = transcript_response if isinstance(transcript_response, str) else transcript_response.text
            
            # If file is >25MB, split into chunks and transcribe
            else:
                print(f"📝 File size {file_size_mb:.1f}MB - splitting into chunks\n")
                
                chunk_length_ms = 10 * 60 * 1000  # 10 minutes per chunk
                total_chunks = (len(audio) + chunk_length_ms - 1) // chunk_length_ms
                
                transcriptions = []
                
                for i in range(0, len(audio), chunk_length_ms):
                    chunk = audio[i:i + chunk_length_ms]
                    chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
                    chunk.export(chunk_path, format="mp3")
                    
                    chunk_num = i // chunk_length_ms + 1
                    print(f"  📝 Transcribing chunk {chunk_num}/{total_chunks}...")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        chunk_response = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=chunk_file,
                            response_format="text",
                            timeout=600
                        )
                    
                    chunk_transcript = chunk_response if isinstance(chunk_response, str) else chunk_response.text
                    transcriptions.append(chunk_transcript)
                    
                    os.remove(chunk_path)
                
                transcript = " ".join(transcriptions)
                print()
            
            print(f"✅ Transcription complete! ({len(transcript)} characters)\n")
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return
    
    # Step 4: Generate PDF
    print("📄 Generating PDF...")
    
    safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:100]
    timestamp = int(time.time())
    pdf_filename = f"{safe_title}_{timestamp}.pdf"
    pdf_path = os.path.join(output_folder, pdf_filename)
    
    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#000000',
            spaceAfter=12,
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
        )
        
        # Get current time in Hawaii timezone
        hawaii_now = datetime.now(ZoneInfo("Pacific/Honolulu"))
        timestamp_text = hawaii_now.strftime("Transcribed on %B %d, %Y at %I:%M %p")
        
        story = []
        story.append(Paragraph(video_title, title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(timestamp_text, subtitle_style))
        story.append(Paragraph(f"Source: {youtube_url}", subtitle_style))
        story.append(Spacer(1, 24))
        
        paragraphs = transcript.split('\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), styles['BodyText']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        
        print(f"✅ PDF saved: {pdf_path}\n")
        print(f"📂 Open folder: {os.path.abspath(output_folder)}")
        
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        return

def main():
    print("=" * 60)
    print("🧠 InnerVerse - Local YouTube Transcriber")
    print("=" * 60)
    print()
    
    if not check_requirements():
        return
    
    # Get YouTube URL
    if len(sys.argv) > 1:
        youtube_url = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        youtube_url = input("🎥 Enter YouTube URL: ").strip()
        
        if not youtube_url:
            print("❌ No URL provided")
            return
        
        # Ask where to save
        print("\n📁 Where do you want to save the PDF?")
        print("   1. iCloud Drive (auto-detected)")
        print("   2. Choose custom folder")
        print("   3. Current directory (transcriptions/)")
        
        choice = input("\nYour choice (1/2/3, or press Enter for default): ").strip()
        
        if choice == "2":
            output_folder = input("Enter full folder path: ").strip()
            if output_folder:
                output_folder = os.path.expanduser(output_folder)
        elif choice == "3":
            output_folder = "transcriptions"
        else:
            output_folder = None  # Will auto-detect iCloud
    
    transcribe_youtube(youtube_url, output_folder)
    print("\n✨ Done!")

if __name__ == "__main__":
    main()
