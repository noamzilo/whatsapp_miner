---
name: Lead Classification with DB-Backed Tagging
overview: ""
todos:
  - id: 234d1137-5db6-4048-bdd9-0b1c7d3c0b9e
    content: Create src/utils/logger.py with setup_logger() call and exported logger instance
    status: pending
  - id: d33d7aef-e944-43e6-adc0-0c28ad86d14a
    content: Rewrite local_manual_attempts.py with Phase 1 (find 10 leads) and Phase 2 (test same 10 + X) logic
    status: pending
  - id: 07b43099-bddb-4443-a784-b138fcb480e1
    content: Update imports in whatsapp_message_classifier.py and other files to use new centralized logger
    status: pending
  - id: bd161002-e842-4c32-8a2c-43ebc1049889
    content: Delete message_classification_logger.py file
    status: pending
isProject: false
---

# Lead Classification with DB-Backed Tagging

## Database Schema Design (Normalized)

### Create `taggers` dimension table:

```sql
taggers:
  - id (PK, Integer)
  - tagger_type (Enum: 'human', 'model', NOT NULL)
  - identifier (Text, NOT NULL)  # 'human_tagger' or model name like 'gpt-4o-mini'
  - UNIQUE(tagger_type, identifier)
```

### Create `message_tags` table:

```sql
message_tags:
  - id (PK, Integer)
  - message_id (FK -> whatsapp_messages.id, NOT NULL)
  - is_lead (Boolean, NOT NULL)
  - lead_category_id (FK -> lead_categories.id, NULLABLE)
  - tagger_id (FK -> taggers.id, NOT NULL)
  - tagged_at (Timestamp, NOT NULL, default=now())
  - confidence_score (Float, NOT NULL, default=1.0)  # Always 1.0 for humans
  - notes (Text, NULLABLE)
  - UNIQUE(message_id, tagger_id, tagged_at)
```

Benefits: Multiple taggers, track evolution, modular tagger management, compare accuracy

## Phase 1: Centralized Logger

Create `src/utils/logger.py`:

- Call `setup_logger()` once at module level
- Export single logger instance
- Update imports in `whatsapp_message_classifier.py` and `local_manual_attempts.py`
- Delete `message_classification_logger.py`

## Phase 2: Local DB Setup & Verification

Docker compose uses TWO files (standard Docker Compose pattern):

- Base: `docker/docker-compose.yml` - service definitions
- Overlay: `docker/docker-compose.dev.yml` - dev overrides (adds local DB, volumes)

Command: `docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up`

After startup, verify snapshot loaded correctly:

- Query: `SELECT COUNT(*) FROM whatsapp_messages`
- Expected: > 11000 rows

DB connection already working via `get_session_local()` - don't modify.

## Phase 3: Migration for Tagging Tables

Create `m0015_create_message_tagging_tables.py`:

- Create `tagger_type_enum` ('human', 'model')
- Create `taggers` table with unique constraint
- Create `message_tags` table with FKs and indexes
- Add indexes: `message_id`, `tagger_id`, `tagged_at`
- Seed `taggers` table with human_tagger: INSERT ('human', 'human_tagger')

Create SQLAlchemy models:

- `src/db/models/tagger.py`
- `src/db/models/message_tag.py`

## Phase 4: Interactive CLI for Human Tagging

Create `src/message_classification/manual/interactive_tagger.py`:

**Startup:**

- Get or create human tagger: `tagger_type='human'`, `identifier='human_tagger'`
- Query only messages NOT already tagged by this human tagger:
  ```sql
  SELECT * FROM whatsapp_messages 
  WHERE id NOT IN (
    SELECT message_id FROM message_tags 
    WHERE tagger_id = <human_tagger_id>
  )
  ```


**Display Features:**

- Show 10 previous messages (same group only via `group_id` filter)
- Highlight quoted messages: show quoted message text inline
- Alternating colors for consecutive messages (use terminal colors)
- Show: sender, timestamp, message text

**Commands:**

- `y` - mark as lead, prompt for category (required)
- `n` - mark as not lead
- `u` - mark as lead with NO category (uncategorized lead)
- `s` - skip this message (don't tag)
- `q` - quit and save
- `p` - previous message
- `j <id>` - jump to message ID

**Data saved:**

- Insert into `message_tags` with `tagger_id` (human_tagger), `confidence_score=1.0`

## Phase 5: Auto-Tagging with Accuracy Tracking

Create `src/message_classification/config.py`:

```python
ACTIVE_MODEL_NAME = "gpt-4o-mini"
```

Update `src/message_classification/whatsapp_message_classifier.py`:

- Import `ACTIVE_MODEL_NAME` from config
- Use in model initialization

Update `local_manual_attempts.py`:

**Query strategy:**

- Load X messages human-tagged as leads (from human_tagger)
- Load Y messages human-tagged as not leads (from human_tagger)

**Classification:**

- Use `WhatsappMessageClassifier` 
- Get or create model tagger: `type='model'`, `identifier=ACTIVE_MODEL_NAME`

**Save results:**

- Insert into `message_tags` with model's tagger_id and confidence

**CSV Export (Single Source of Truth):**

Save results to `classification_results.csv` with columns:

- message_id
- message_text (full text)
- context_messages (full context: 10 previous messages formatted)
- human_is_lead
- model_is_lead
- human_category
- model_category
- match (boolean)
- category_match (boolean)

**Tabular Display (Derived from CSV):**

After writing CSV, read it back and display table with previews:

```
Message ID | Text Preview        | Human Tag | Model Tag | Match  | Category Match
-----------|---------------------|-----------|-----------|--------|---------------
123        | "Looking for..."    | lead      | lead      | ✓      | ✓
456        | "Hello everyone"    | not_lead  | lead      | ✗ WRONG| -
789        | "Need dentist"      | lead      | lead      | ✓      | ✓
```

Text preview truncated to 30 chars for display only

## Technical Notes

- All DB access via `get_session_local()` - already configured, don't modify
- Use `@log_in_out` decorator only
- Keep code FLAT, no deep nesting
- No docstrings, no comments (except functionally required)
- Only update code, don't run anything