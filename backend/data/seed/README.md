# Knowledge-base seed data

Drop your verified catalog here as `catalog.json` (gitignored DBs are built from
it). The format is shown in [`catalog.example.json`](catalog.example.json).

## Format

```jsonc
{
  "sources":  [ { "key", "title", "url?", "source_type", "published_date?",
                  "retrieved_date?", "confidence?", "verification_status?", "content_hash?" } ],
  "services": [ {
     "slug", "name_en", "category", "description",
     "variants": [ { "condition_label", "description?",
        "requirements": [ { "document_name", "is_mandatory?", "source_key", "notes?" } ],
        "fees":         [ { "label", "amount_lkr", "source_key", "notes?" } ] } ],
     "offices":            [ { "name", "office_type", "district", "address?", "hours?", "contact?" } ],
     "district_variations":[ { "district", "source_key", "notes?" } ],
     "chunks":             [ { "content", "source_key", "chunk_index?" } ]
  } ]
}
```

- `source_type` ∈ `gazette | circular | portal | experience`
- `office_type` ∈ `DS | Pradeshiya | DRP | other`
- `verification_status` ∈ `verified | auto_gathered | pending` (seed data is usually `verified`)
- `amount_lkr` is a string to preserve decimal precision (e.g. `"1500.00"`)
- every `source_key` must match a `sources[].key` in the same file
- `chunks[].content` is the free text embedded for semantic retrieval

## Loading

```python
from pathlib import Path
from app.adapters.embeddings.bge import BgeEmbeddingProvider
from app.adapters.knowledge.chroma_sqlite import ChromaSqliteStore
from app.adapters.knowledge.seed import KnowledgeSeeder

store = ChromaSqliteStore(Path("data/govguide.sqlite3"), Path("data/chroma"))
seeder = KnowledgeSeeder(store, BgeEmbeddingProvider())
print(seeder.load_from_json(Path("data/seed/catalog.json")))
```

A thin CLI wrapper will be added in a later stage.
