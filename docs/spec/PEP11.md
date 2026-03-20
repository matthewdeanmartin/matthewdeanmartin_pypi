# PEP XXXX – Identity Packages for Python (rev 1.1)

**Delta since 1.0 (normative overview)**

* Add `continuity` block (successor maintainers, inactivity thresholds, hand-off channels).
* Add `claimed_domains` with verifiable proofs.
* Add `funding` block (keys compatible with GitHub `FUNDING.yml`) and optional packaged `identity/funding.yml`.
* Extend `contact_policy` with explicit “transparency of intent” signals (maintenance state, support model, telemetry policy).
* Increment `schema_version` to `1.1`.

## New/Updated Sections (normative)

### 3. Manifest Schema (v1.1)

`identity/identity.json` **MUST** set `"schema_version": "1.1"` and MAY include the new fields below. All 1.0 fields remain valid.

```json
{
  "$schema": "https://example.python.org/peps/xxxx/identity-package.schema.json",
  "type": "object",
  "required": ["schema_version", "subject", "evidence", "contact_policy"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.1" },

    "subject": { ... },               // unchanged from 1.0
    "keys": { ... },                  // unchanged from 1.0
    "evidence": { ... },              // unchanged from 1.0

    "claimed_domains": {
      "type": "array",
      "description": "Domains the subject claims to control with attached proofs.",
      "items": {
        "type": "object",
        "required": ["domain", "proofs"],
        "properties": {
          "domain": { "type": "string", "pattern": "^[A-Za-z0-9.-]+$" },
          "proofs": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "required": ["kind", "value"],
              "properties": {
                "kind": {
                  "type": "string",
                  "enum": ["dns_txt", "http_well_known", "file", "dnssec_ds"]
                },
                "value": { "type": "string" },
                "verified_at": { "type": "string", "format": "date-time" }
              }
            }
          }
        }
      }
    },

    "funding": {
      "type": "object",
      "description": "FUNDING.yml-compatible keys; consumers MAY render a Sponsor UI.",
      "properties": {
        "github":          { "oneOf": [{ "type": "string" }, { "type": "array", "items": { "type": "string" } }] },
        "patreon":         { "type": "string" },
        "open_collective": { "type": "string" },
        "ko_fi":           { "type": "string" },
        "tidelift":        { "oneOf": [{ "type": "string" }, { "type": "array", "items": { "type": "string" } }] },
        "liberapay":       { "type": "string" },
        "community_bridge":{ "type": "string" },
        "custom":          { "oneOf": [{ "type": "string" }, { "type": "array", "items": { "type": "string", "format": "uri" } }] },
        "packaged_file":   { "type": "string", "description": "Relative path to an embedded funding.yml, e.g., identity/funding.yml" }
      },
      "additionalProperties": false
    },

    "contact_policy": {
      "type": "object",
      "required": ["matrix", "security"],
      "properties": {
        "matrix": { ... },            // from 1.0 (charity_offers, job_offers, etc.)
        "security": { ... },          // from 1.0
        "global_opt_out": { ... },    // from 1.0

        "transparency": {
          "type": "object",
          "description": "Explicit intent/disclosure signals.",
          "properties": {
            "maintenance_status": {
              "type": "string",
              "enum": ["active", "security-fixes-only", "seeking-maintainers", "frozen", "archived"]
            },
            "support_policy": {
              "type": "string",
              "enum": ["best-effort", "community-only", "paid-support", "no-support"]
            },
            "support_channels": {
              "type": "array",
              "items": { "type": "string" }
            },
            "commercial_support_url": { "type": "string", "format": "uri" },
            "responsiveness_sla_days": { "type": "integer", "minimum": 0 },

            "telemetry": {
              "type": "object",
              "properties": {
                "collects_telemetry": { "type": "boolean", "default": false },
                "opt_in_default":      { "type": "boolean", "default": true },
                "policy_url":          { "type": "string", "format": "uri" }
              }
            }
          }
        }
      }
    },

    "continuity": {
      "type": "object",
      "description": "Plan for stewardship if the subject becomes inactive.",
      "required": ["inactivity_threshold_days", "handoff_policy"],
      "properties": {
        "inactivity_threshold_days": { "type": "integer", "minimum": 30 },
        "successors": {
          "type": "array",
          "description": "Preferred successor maintainers or organizations in priority order.",
          "items": {
            "type": "object",
            "required": ["display_name"],
            "properties": {
              "display_name": { "type": "string" },
              "contact": { "type": "string" },
              "evidence_url": { "type": "string", "format": "uri" }
            }
          }
        },
        "handoff_policy": {
          "type": "string",
          "enum": [
            "transfer-on-threshold",       // auto-consent after threshold
            "consent-required",            // explicit consent needed
            "foundation-stewardship"       // handoff to named foundation
          ]
        },
        "handoff_channels": {
          "type": "array",
          "items": { "type": "string" }
        },
        "notes": { "type": "string" }
      }
    },

    "resume": { ... },                // from 1.0
    "extras": { ... }                 // from 1.0
  }
}
```

#### Verification guidance (informative)

* **Domains:**

  * `dns_txt` (recommended): a TXT record under `_idpkg.<domain>` containing a tuple, e.g.
    `idpkg=package:id-matthewdeanmartin; fp=0123...ABC; since=2025-10-21`
  * `http_well_known`: serve `/.well-known/idpkg.json` with `{ "package": "...", "fingerprint": "..." }` and (optionally) its detached signature `idpkg.json.asc`.
  * `file`: a public page or file on the domain with the same tuple; less robust but acceptable.
  * `dnssec_ds`: presence of DS records (strengthens DNS proofs; not sufficient alone).
* Verifiers SHOULD validate at least one proof method per domain.

### 4. CLI Entry Point (updates)

Add subcommands (optional, recommended):

* `idpkg domains verify` – resolve and validate `claimed_domains[*].proofs`.
* `idpkg funding show` – print normalized funding map or the packaged `identity/funding.yml`.
* `idpkg policy show` – include `transparency` details.

### 5. Funding Metadata

* JSON `funding` mirrors GitHub `FUNDING.yml` keys for interoperability.
* If `packaged_file` is present, the wheel/sdist **SHOULD** include that file (e.g., `identity/funding.yml`).
* Renderers MUST prefer the JSON values when both JSON and YAML are shipped; YAML is provided for tool compatibility only.

### 7. Contact Policy Semantics (expansion)

* `contact_policy.transparency.maintenance_status` and `support_policy` inform user expectations and triage.
* `telemetry` explicitly discloses collection and defaults.
* If `maintenance_status="seeking-maintainers"`, verifiers MAY elevate visibility of `maintainer_apply` contact path.

### 8. Versioning

* Consumers that only understand 1.0 MUST safely ignore unknown 1.1 fields.

---

## Compact Example (v1.1)

```json
{
  "schema_version": "1.1",
  "subject": { "kind": "person", "display_name": "Jane Q. Dev" },

  "keys": [{
    "kind": "openpgp",
    "fingerprint": "0123456789ABCDEF0123456789ABCDEF01234567",
    "urls": ["https://keybase.io/janeqdev"]
  }],

  "evidence": [
    {"url": "https://github.com/janeqdev", "rel_me": true, "kind": "github"},
    {"url": "https://fosstodon.org/@jane", "rel_me": true, "kind": "mastodon"},
    {"url": "https://jane.example", "rel_me": false, "kind": "website"}
  ],

  "claimed_domains": [{
    "domain": "jane.example",
    "proofs": [
      {"kind": "dns_txt", "value": "idpkg=package:id-janeqdev; fp=0123456789ABCDEF0123456789ABCDEF01234567; since=2025-10-21"}
    ]
  }],

  "funding": {
    "github": ["janeqdev"],
    "open_collective": "janeqdev",
    "custom": ["https://jane.example/sponsor"],
    "packaged_file": "identity/funding.yml"
  },

  "contact_policy": {
    "matrix": {
      "charity_offers":   {"allowed": false},
      "job_offers":       {"allowed": false},
      "name_transfer":    {"allowed": true, "instructions": "Email subject: 'package name transfer'."},
      "maintainer_apply": {"allowed": true, "channels": [{"kind": "email", "address": "oss@jane.example"}]},
      "bug_reports":      {"allowed": true,  "channels": [{"kind": "webform", "address": "https://github.com/janeqdev/project/issues"}]}
    },
    "security": {
      "channel": { "kind": "email", "address": "security@jane.example" },
      "encryption_required": true,
      "policy_url": "https://jane.example/security",
      "response_sla_days": 7
    },
    "global_opt_out": ["job_offers", "charity_offers"],
    "transparency": {
      "maintenance_status": "security-fixes-only",
      "support_policy": "community-only",
      "support_channels": ["https://github.com/janeqdev/project/discussions"],
      "responsiveness_sla_days": 14,
      "telemetry": {
        "collects_telemetry": false,
        "opt_in_default": true,
        "policy_url": "https://jane.example/telemetry"
      }
    }
  },

  "continuity": {
    "inactivity_threshold_days": 365,
    "handoff_policy": "foundation-stewardship",
    "successors": [
      { "display_name": "Open Source Commons Foundation", "contact": "steward@oscf.example", "evidence_url": "https://oscf.example/projects" }
    ],
    "handoff_channels": ["security@jane.example", "steward@oscf.example"]
  },

  "resume": { "json_resume": "data/resume.json", "vcard": "data/resume.vcf" }
}
```

**Packaged `identity/funding.yml` (optional):**

```yaml
github: [janeqdev]
open_collective: janemqdev
custom:
  - https://jane.example/sponsor
```

---

## Implementation Notes (brief)

* **Verifiers**

  * MUST ignore unknown keys (forward compatibility).
  * SHOULD validate domain proofs (`dns_txt` first) and display a per-domain result.
  * SHOULD prefer JSON `funding` over YAML when both exist.

* **CLI (reference)**

  * `idpkg verify` unchanged (signature over `identity.json`).
  * `idpkg domains verify` resolves `_idpkg.<domain>` TXT; fetches `/.well-known/idpkg.json` if declared.
  * `idpkg funding show` merges JSON + YAML, with JSON precedence; prints normalized list.

---

## Rationale for Each Addition

* **Continuity:** prevents “abandonware ambiguity,” enables predictable stewardship paths.
* **Domain Claims:** anchors identity to owned namespaces; strengthens link evidence.
* **Funding:** interoperable with GitHub UI while remaining platform-agnostic.
* **Transparency:** reduces surprises (support levels, maintenance state, telemetry posture).
