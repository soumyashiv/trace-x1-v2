# Database Schema

Postgres is used for case metadata and investigation-run snapshots only.
Raw blockchain transaction data is intentionally NOT duplicated into
Postgres — it's re-derived on demand through the provider abstraction
(and cached in Redis), so there is exactly one source of truth for chain
data (the provider) and the DB stays small.

See `backend/app/db/models.py` (SQLAlchemy) and `backend/app/db/schema.sql`
(raw DDL) for the authoritative definitions. Summary:

## `users`
| column | type | notes |
|---|---|---|
| id | uuid (str) | PK |
| username | varchar(64) | unique |
| password_hash | varchar(255) | bcrypt via passlib |
| role | varchar(32) | investigator / admin / viewer |
| created_at | timestamp | |

## `cases`
| column | type | notes |
|---|---|---|
| id | uuid (str) | PK |
| title | varchar(200) | |
| investigator_username | varchar(64) | FK → users.username |
| suspect_wallet | varchar(128) | indexed |
| chain | varchar(16) | MOCK / ETH / BTC / TRON |
| status | varchar(32) | open / closed / escalated |
| notes | text | |
| created_at | timestamp | |

## `investigation_runs`
| column | type | notes |
|---|---|---|
| id | uuid (str) | PK |
| case_id | uuid (str) | FK → cases.id, cascade delete |
| result_json | jsonb | full `InvestigationResult.to_dict()` snapshot |
| risk_score | double | denormalized for fast dashboard sorting |
| risk_level | varchar(16) | denormalized |
| generated_at | timestamp | |

## `audit_log`
| column | type | notes |
|---|---|---|
| id | uuid (str) | PK |
| username | varchar(64) | actor |
| action | varchar(64) | e.g. "case.create", "report.export" |
| resource | varchar(200) | e.g. case_id |
| detail | text | never contains raw request bodies / victim PII |
| ip_address | varchar(64) | |
| timestamp | timestamp | indexed |

## Entity-relationship

```
users 1───* cases 1───* investigation_runs
users 1───* audit_log   (by username, no FK constraint — logs must
                          survive user deletion)
```
