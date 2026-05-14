# JSON Resume — Authoring Guide for LLMs

This document teaches you how to write a valid `resume.json` that passes schema
validation used by `pypi-profile` (the `schema-resume-validator` Python package,
which wraps the JSON Resume schema).

______________________________________________________________________

## Schema version

This project validates against the JSON Resume schema as implemented by
`schema-resume-validator`. The schema differs from the original v1.0.0 spec in
one important way: **work entry `location` is an object, not a string.**

______________________________________________________________________

## Top-level structure

```json
{
  "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
  "basics": { ... },
  "work": [ ... ],
  "volunteer": [],
  "education": [],
  "awards": [],
  "certificates": [],
  "publications": [],
  "skills": [ ... ],
  "languages": [ ... ],
  "interests": [],
  "references": [],
  "projects": [ ... ]
}
```

All top-level arrays are optional and may be empty (`[]`). Never omit a key
with `null` — use `[]` for arrays and omit optional string fields entirely
rather than setting them to `""` when the value would fail format validation.

______________________________________________________________________

## `basics`

```json
"basics": {
  "name": "Jane Smith",
  "label": "Python Developer",
  "image": "",
  "email": "jane@example.com",
  "phone": "",
  "url": "https://github.com/janesmith",
  "summary": "One paragraph summary.",
  "location": {
    "address": "",
    "postalCode": "",
    "city": "Arlington",
    "countryCode": "US",
    "region": "Virginia"
  },
  "profiles": [
    {
      "network": "GitHub",
      "username": "janesmith",
      "url": "https://github.com/janesmith"
    }
  ]
}
```

**Rules:**

- `location` is an **object** with `city`, `region`, `countryCode` (ISO-3166-1
  ALPHA-2, e.g. `"US"`), `address`, `postalCode`. All sub-fields are optional
  strings.
- `url` in `basics` must be a valid URI or omitted. Never `""`.
- `image`, `email`, `phone`, `summary` are plain strings and may be `""`.

______________________________________________________________________

## `work` entries

```json
{
  "name": "Acme Corp",
  "position": "Senior Engineer",
  "startDate": "2021-03",
  "endDate": "2024-09",
  "summary": "Led backend platform team.",
  "highlights": [
    "Reduced API latency by 40%",
    "Migrated 20 services to Kubernetes"
  ],
  "location": {
    "city": "McLean",
    "region": "Virginia",
    "countryCode": "US"
  }
}
```

**Rules:**

- `location` is an **object** (same shape as `basics.location`), **not a
  string**. This is the most common mistake.
- `startDate` and `endDate` must match `YYYY-MM-DD`, `YYYY-MM`, or `YYYY`.
  They cannot be `""`. **Omit `endDate` entirely for current positions.**
- `url` must be a valid URI or omitted. Never `""`.
- `highlights` is an array of strings; omit or use `[]` if none.
- `name` is the company/organization name.
- `description` (optional string) is the organization description, rarely used.

**Current job pattern — omit `endDate`:**

```json
{
  "name": "Booz Allen Hamilton",
  "position": "DevOps Engineer",
  "startDate": "2025-02",
  "summary": "...",
  "location": { "city": "McLean", "region": "Virginia", "countryCode": "US" }
}
```

**Past job pattern:**

```json
{
  "name": "Previous Corp",
  "position": "Developer",
  "startDate": "2019-01",
  "endDate": "2024-12",
  "summary": "...",
  "location": { "city": "Arlington", "region": "Virginia", "countryCode": "US" }
}
```

______________________________________________________________________

## `education` entries

```json
{
  "institution": "State University",
  "area": "Computer Science",
  "studyType": "Bachelor",
  "startDate": "1994-09",
  "endDate": "1998-05",
  "score": "",
  "courses": []
}
```

Same date rules as `work`. Omit `endDate` if still enrolled.

______________________________________________________________________

## `skills` entries

```json
{
  "name": "Python",
  "level": "Expert",
  "keywords": ["packaging", "FastAPI", "pytest"]
}
```

`level` is a free string (no enum). Common values: `"Beginner"`, `"Intermediate"`,
`"Advanced"`, `"Expert"`, `"Master"`.

______________________________________________________________________

## `projects` entries

```json
{
  "name": "my-tool",
  "description": "A CLI tool for X.",
  "highlights": [],
  "keywords": ["python", "cli"],
  "startDate": "2023-01",
  "url": "https://github.com/me/my-tool",
  "roles": ["creator"],
  "entity": "me",
  "type": "application"
}
```

- `url` must be a valid URI or omitted — never `""`.
- `startDate`/`endDate` follow the same date pattern.

______________________________________________________________________

## `certificates` entries

```json
{
  "name": "AWS Solutions Architect",
  "date": "2022-06",
  "issuer": "Amazon Web Services",
  "url": "https://www.credly.com/badges/..."
}
```

______________________________________________________________________

## `languages` entries

```json
{
  "language": "English",
  "fluency": "Native speaker"
}
```

______________________________________________________________________

## Date format

The regex that all date fields must satisfy:

```
^([1-2][0-9]{3}-[0-1][0-9]-[0-3][0-9]|[1-2][0-9]{3}-[0-1][0-9]|[1-2][0-9]{3})$
```

| Format | Example | Use when |
|--------|---------|----------|
| `YYYY` | `2023` | Year only |
| `YYYY-MM` | `2023-06` | Month precision (most common for jobs) |
| `YYYY-MM-DD` | `2023-06-15` | Full date (certificates, awards) |

**Never use:**

- `""` (empty string) — omit the field instead
- `"present"` — omit `endDate` for current positions
- `"2025-2"` — month must be zero-padded: `"2025-02"`

______________________________________________________________________

## URI fields

Fields typed as `"format": "uri"` (`url` in `work`, `projects`, `certificates`,
`basics`, `profiles`) must be a syntactically valid URI or **omitted entirely**.

```json
// WRONG — fails URI format
"url": ""

// CORRECT — omit the field
// (no "url" key at all)

// CORRECT — valid URI
"url": "https://github.com/me/repo"
```

______________________________________________________________________

## Common mistakes to avoid

| Mistake | Fix |
|---------|-----|
| `"location": "Arlington, VA"` in `work` | Use `{"city": "Arlington", "region": "Virginia", "countryCode": "US"}` |
| `"endDate": ""` | Omit `endDate` entirely |
| `"url": ""` | Omit `url` entirely |
| `"endDate": "present"` | Omit `endDate` entirely |
| `"startDate": "2025-2"` | Zero-pad month: `"2025-02"` |
| `"highlights": null` | Use `[]` or omit |

______________________________________________________________________

## Validating in this project

```bash
uv run python -c "
import json
from pathlib import Path
from schema_resume import validate_resume
raw = json.loads(Path('data/resume.json').read_text())
result = validate_resume(raw)
print('valid:', result['valid'])
for e in result.get('errors', []):
    print(e)
"
```

Or via the importer (warns on validation failure):

```bash
uv run pypi-profile init --from-json-resume data/resume.json --output /tmp/test.toml
```
