# Data model

The profile data lives in a single TOML file (`pypi_profile.toml`). Everything the CLI, server,
and static builder do is derived from parsing that file into a tree of Pydantic models defined in
`pypi_profile/models.py`.

## Why Pydantic?

Pydantic is a data validation library. You describe what your data should look like using Python
classes, and Pydantic checks that the actual data matches — raising a clear error if it does not.
It also fills in default values for optional fields and converts data types automatically (for
example, turning a string into an enum member).

The alternative would be reading the raw dictionary from `tomllib` and doing manual checks
everywhere. Pydantic centralises all of that.

## The top-level model

`ProfileData` in `models.py` is the root. Every section of the TOML maps to one of its fields:

```python
class ProfileData(BaseModel):
    profile: ProfileSection = ProfileSection()
    identity: IdentitySection = IdentitySection()
    humans: list[HumanEntry] = []
    profiles: list[ProfileLink] = []
    contact_methods: list[ContactMethod] = []
    packages: list[PackageEntry] = []
    projects: list[ProjectEntry] = []
    work_experience: list[WorkEntry] = []
    hiring: HiringSection = HiringSection()
    contracting: ContractingSection = ContractingSection()
    succession: SuccessionSection = SuccessionSection()
    contact_preferences: ContactPreferences = ContactPreferences()
    verification: VerificationSection = VerificationSection()
```

Every field has a default value, so a minimal TOML file (even an empty one) produces a valid
`ProfileData` object. Fields that are missing from the TOML are filled with their defaults.

## Loading a profile

```python
from pathlib import Path
from pypi_profile.loader import load_profile

profile = load_profile(Path("pypi_profile.toml"))

# profile is a ProfileData object
print(profile.profile.display_name)      # from [profile]
print(profile.identity.pypi_username)    # from [identity]
print(len(profile.packages))            # number of [[packages]] entries
```

`load_profile` does three things:

1. Reads the file with `tomllib` (binary mode, as required by the spec).
1. If the file is `pyproject.toml`, extracts the `[tool.pypi-profile]` sub-table.
1. Passes the dict to `ProfileData.model_validate(raw)`.

## Section-by-section reference

### `[profile]` — `ProfileSection`

```toml
[profile]
kind = "individual"
display_name = "Jane Smith"
summary = "Python developer and package maintainer."
```

`kind` must be one of the `PrincipalKind` literals: `individual`, `team`, `company`, `llc`,
`foundation`, `collective`, `project`, `other`. It is used by the UI to choose the right label
and icon.

### `[identity]` — `IdentitySection`

```toml
[identity]
legal_name = "Jane A. Smith"
display_name = "Jane Smith"
pypi_username = "jane-smith"
pronouns = "she/her"
timezone = "America/New_York"
location = "Boston, MA, USA"
```

`pypi_username` is the canonical identifier used throughout the tool — it appears in proof tokens,
in hub URLs (`/profiles/jane-smith`), and in the package name convention
(`pypi-profile-jane-smith`).

### `[[humans]]` — `HumanEntry`

Used for team or organisation profiles to list members:

```toml
[[humans]]
id = "jane-smith"
display_name = "Jane Smith"
role = "Lead maintainer"
bio = "Works on the core library."
```

`id` should match a PyPI username. The `id` field is required; all others are optional.

### `[[profiles]]` — `ProfileLink`

Each external account the profile owner wants to link to:

```toml
[[profiles]]
kind = "github"
label = "GitHub"
url = "https://github.com/jane-smith"
verification = "self_asserted"
rel_me = true
stored_proof = ""
```

`kind` is a free string (`github`, `mastodon`, `gitlab`, `twitter`, `linkedin`, `website`, etc.).
`verification` must be a `ClaimStatus` literal: `self_asserted`, `verified`, `unverified`,
`invalid`, `expired`, or `unknown`. It is updated by the verifier.

`stored_proof` holds the `pypi-profile-proof: ...` token written by `update-proofs`. When this
field is non-empty, the static site can show a `verified` badge without making a live HTTP request.

`rel_me = true` tells the template engine to render the anchor as `<a href="..." rel="me">`, which
is used by Mastodon and some other platforms for identity verification.

### `[[contact_methods]]` — `ContactMethod`

```toml
[[contact_methods]]
kind = "email"
label = "Professional email"
value = "jane@example.com"
audience = ["hiring", "consulting"]
visibility = "public"
```

`audience` is a free-form list of strings describing who should use this contact method. Nothing
enforces the values, but the UI displays them as tags. `visibility` controls how the value is
rendered: `public` shows it plainly, `obfuscated` renders it with simple obfuscation, `link` turns
it into a link without showing the raw value.

### `[[packages]]` — `PackageEntry`

```toml
[[packages]]
name = "my-package"
role = "maintainer"
state = "active"
summary = "Does something useful."
url = "https://pypi.org/project/my-package/"
```

`role` must be one of the `PackageRole` literals. The full list is in `models.py`; common values
are `author`, `maintainer`, `co-maintainer`, `contributor`, `owner`. `state` must be one of the
`PackageState` literals: `active`, `maintained`, `archived`, `deprecated`, `abandoned`, and
several others covering the full lifecycle of a package.

### `[[projects]]` — `ProjectEntry`

For non-PyPI projects (a GitHub repo, a deployed service, a research project):

```toml
[[projects]]
name = "My Research Tool"
url = "https://github.com/jane-smith/research-tool"
role = "creator"
state = "experimental"
summary = "A prototype for exploring X."
```

### `[[work_experience]]` — `WorkEntry`

```toml
[[work_experience]]
organization = "Acme Corp"
title = "Senior Engineer"
start_date = "2020-03"
end_date = "present"
summary = "Built the data pipeline."
```

`start_date` and `end_date` are free strings. The tool does not parse them, so any format works,
but `YYYY-MM` is conventional.

### `[hiring]` — `HiringSection`

```toml
[hiring]
open_to_work_since = "2026-01-01"
employment_types = ["full-time", "contract"]
work_model = ["remote", "hybrid"]
jurisdiction = ["US"]
speaking = true
sponsorship = false
```

When `open_to_work_since` is non-empty the hiring page shows the profile as actively available.
`speaking` and `sponsorship` indicate availability for conference talks and visa sponsorship
respectively.

### `[contracting]` — `ContractingSection`

```toml
[contracting]
legal_entity = "Jane Smith Consulting LLC"
engagement_types = ["hourly", "retainer"]
```

### `[succession]` — `SuccessionSection`

```toml
[succession]
policy = "If unreachable for 60 days, contact the successor below."
last_reviewed = "2026-04-01"

[[succession.contacts]]
name = "Bob Jones"
contact = "bob@example.com"
scope = ["my-package", "my-other-package"]
relationship = "co-maintainer"
verification = "self_asserted"
```

This section is for documenting a succession plan so that packages do not become abandoned if the
current maintainer is unable to continue.

### `[contact_preferences]` — `ContactPreferences`

```toml
[contact_preferences]
do_contact_about = ["hiring", "speaking", "package-maintenance"]
do_not_contact_about = ["cryptocurrency", "unsolicited freelance offers"]
```

Both fields are free-form string lists. The UI renders them as a simple list on the contact page.

### `[verification]` — `VerificationSection`

```toml
[verification]
public_key = "RWRCcrgceTEEEvIzBBielJiZ6n//kkEFQ5..."
preferred_signature_backend = "minisign"
```

`public_key` is the base64-encoded minisign public key produced by `pypi-profile keygen`. This key
is used by the verifier to check claim signatures. Publishing your profile package to PyPI with
this key embedded is how others can verify your signed claims without trusting you directly.

## Serialisation

`ProfileData.model_dump()` converts the whole tree back to a plain dict, which FastAPI serialises
to JSON for the `/api/profile.json` endpoint. This is standard Pydantic and requires no extra code.

```python
import json
profile = load_profile(Path("pypi_profile.toml"))
print(json.dumps(profile.model_dump(), indent=2))
```

## Validation errors

When `model_validate` fails (e.g. `kind = "unicorn"` is not a valid `PrincipalKind`) Pydantic
raises a `ValidationError` with a clear message pointing to the field and the allowed values. The
CLI catches this and prints a human-readable error.

If you are debugging a parse failure, you can do:

```python
from pydantic import ValidationError
from pypi_profile.models import ProfileData

try:
    ProfileData.model_validate({"profile": {"kind": "unicorn"}})
except ValidationError as exc:
    print(exc)
```
