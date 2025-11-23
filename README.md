# 🧠 InnerVerse

**AI-powered learning platform for MBTI and personality typology**

InnerVerse is a comprehensive learning management system that combines knowledge graph management, AI-powered content generation, and interactive tutoring to create personalized learning experiences in personality typology.

---

## ✨ Features

### 🎓 Learning Management
- **Structured Courses**: Create and manage multi-lesson courses with prerequisites
- **Progress Tracking**: Monitor student progress and completion rates
- **Interactive Lessons**: Rich multimedia content with embedded videos and transcripts

### 🤖 AI-Powered Features
- **Concept Extraction**: Automatically extract key concepts from documents using Claude AI
- **Knowledge Graph**: Build and visualize relationships between concepts
- **AI Tutoring**: Context-aware chatbot that understands lesson content
- **Content Generation**: Automatically generate lesson content from transcripts

### 📚 Content Management
- **Document Processing**: Upload and process PDFs, audio, and video content
- **YouTube Integration**: Import and transcribe YouTube videos
- **Vector Search**: Semantic search across all content using Pinecone
- **Batch Processing**: Process multiple documents efficiently

### 📊 Analytics & Insights
- **Usage Tracking**: Monitor API usage and costs
- **Content Atlas**: Visualize your content library
- **Quality Reports**: Track knowledge graph quality metrics

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (optional)
- API Keys for:
  - OpenAI (for embeddings)
  - Anthropic Claude (for AI features)
  - Pinecone (for vector search)

### Installation

#### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd InnerVerse
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Application: http://localhost:5000
   - API Docs: http://localhost:5000/docs
   - Health Check: http://localhost:5000/health

#### Option 2: Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd InnerVerse
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   # For development:
   pip install -e ".[dev]"
   ```

4. **Setup PostgreSQL**
   ```bash
   # Create database
   createdb innerverse
   
   # Run migrations
   alembic upgrade head
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Run the application**
   ```bash
   python app.py
   # Or with uvicorn:
   uvicorn app:app --reload --host 0.0.0.0 --port 5000
   ```

---

## 📋 Configuration

### Required Environment Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...
PINECONE_INDEX=mbti-knowledge-v2

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/innerverse

# Security
CSRF_SECRET_KEY=<generate-random-secret>
```

### Optional Environment Variables

See `.env.example` for complete configuration options including:
- Server settings (host, port)
- Rate limiting
- Logging configuration
- Proxy settings for YouTube downloads
- AI model selection

---

## 🏗️ Architecture

```
InnerVerse/
├── app.py                  # Main application entry point
├── src/
│   ├── core/              # Core infrastructure
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database connection pooling
│   │   ├── logging.py     # Structured logging
│   │   ├── security.py    # Security utilities
│   │   └── exceptions.py  # Custom exceptions
│   ├── api/               # API routes
│   │   ├── dependencies.py    # Shared dependencies
│   │   ├── health_routes.py   # Health checks
│   │   └── static_routes.py   # Static pages
│   ├── routes/            # Feature routes
│   │   ├── chat_routes.py           # AI chat endpoints
│   │   └── learning_paths_routes.py # Course management
│   └── services/          # Business logic
│       ├── chat_service.py          # Chat functionality
│       ├── knowledge_graph_manager.py
│       ├── concept_extractor.py
│       └── ...
├── static/                # Frontend assets
├── templates/             # HTML templates
├── data/                  # Data storage
├── database/              # Database schemas
└── tests/                 # Test suite
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_knowledge_graph.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy src/

# Security scan
bandit -r src/
```

---

## 📚 API Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:5000/docs
- **Health Check**: http://localhost:5000/health

### Key Endpoints

#### Learning Management
- `GET /api/courses` - List all courses
- `POST /api/courses` - Create new course
- `GET /api/courses/{course_id}` - Get course details
- `POST /api/courses/{course_id}/lessons` - Add lesson to course

#### AI Chat
- `POST /api/chat/lesson` - Chat with AI tutor about specific lesson
- `GET /api/chat/lesson/{lesson_id}/history` - Get chat history

#### Knowledge Graph
- `GET /api/knowledge-graph` - Get full knowledge graph
- `POST /api/knowledge-graph/node` - Add concept node
- `POST /api/extract-concepts` - Extract concepts from document

#### Document Management
- `POST /upload` - Upload and process document
- `GET /documents/report` - Get document statistics
- `DELETE /documents/{document_id}` - Delete document

---

## 🔧 Development

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Adding New Routes

1. Create route file in `src/api/` or `src/routes/`
2. Define router with `APIRouter()`
3. Add routes with decorators: `@router.get()`, `@router.post()`, etc.
4. Include router in `app.py`: `app.include_router(your_router)`

### Using Dependencies

```python
from fastapi import Depends
from src.api.dependencies import get_db, get_settings, get_kg_manager

@router.get("/example")
async def example(
    db=Depends(get_db),
    settings=Depends(get_settings),
    kg=Depends(get_kg_manager)
):
    # Your code here
    pass
```

---

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Start with Redis
docker-compose --profile with-redis up -d

# Start with Nginx
docker-compose --profile with-nginx up -d

# Access database
docker-compose exec postgres psql -U innerverse -d innerverse
```

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong `CSRF_SECRET_KEY`
- [ ] Set `COOKIE_SECURE=true` (requires HTTPS)
- [ ] Configure `ALLOWED_ORIGINS` for CORS
- [ ] Set `LOG_FORMAT=json` for structured logging
- [ ] Enable rate limiting: `RATE_LIMIT_ENABLED=true`
- [ ] Use connection pooling (already configured)
- [ ] Setup SSL/TLS certificates for HTTPS
- [ ] Configure backup strategy for PostgreSQL
- [ ] Setup monitoring and alerting
- [ ] Review and limit API keys permissions

### Recommended Infrastructure

- **Compute**: Docker container on AWS ECS, Google Cloud Run, or similar
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL)
- **Caching**: Redis (AWS ElastiCache, Google Cloud Memorystore)
- **Storage**: S3 or Google Cloud Storage for large files
- **Monitoring**: CloudWatch, Datadog, or Prometheus + Grafana

---

## 📖 Documentation

- [API Documentation](http://localhost:5000/docs) - Interactive API docs (when running)
- [Configuration Guide](.env.example) - Complete configuration reference
- [Database Schema](database/learning_paths_schema.sql) - Database structure

---

## 🤝 Contributing

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions/classes
- Keep functions focused and small
- Use meaningful variable names

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Run linting and tests: `pytest && ruff check .`
5. Commit with clear messages
6. Push and create Pull Request

---

## 📝 License

[Add your license here]

---

## 🙏 Acknowledgments

- **OpenAI** - GPT models and embeddings
- **Anthropic** - Claude AI for concept extraction and tutoring
- **Pinecone** - Vector database for semantic search
- **FastAPI** - Modern Python web framework

---

## 📞 Support

- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Discussions**: [GitHub Discussions](your-repo-url/discussions)
- **Email**: [your-email]

---

## 🗺️ Roadmap

- [ ] Real-time collaboration features
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Integration with Learning Management Systems (LMS)
- [ ] Gamification features
- [ ] Social learning features

---

**Built with ❤️ for personality typology education**

