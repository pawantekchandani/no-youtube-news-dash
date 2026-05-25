# Task List — Phase 5: Quality Layer

- `[x]` Install `sentence-transformers>=3.0.0` for embedding-based semantic deduplication
- `[x]` Implement semantic deduplication algorithm with rapidfuzz fallback (`src/newsdash/pipeline/dedupe.py`)
- `[x]` Integrate authority scoring (Tier 1 articles prioritized over Tier 2 within each topic)
- `[x]` Implement database model updates and "mark as read" state management
- `[x]` Create FastAPI post endpoint `/api/articles/{article_id}/read` to set read status (`src/newsdash/server/app.py`)
- `[x]` Update the dashboard UI template to grey out read articles (`src/newsdash/server/templates/dashboard.html`)
- `[x]` Calculate and display dynamic reading time estimates on each article card
- `[x]` Restart launchd background daemon and manually verify mark-as-read integration
