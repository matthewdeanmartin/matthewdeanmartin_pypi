# PEP XXXX – Identity Packages for Python

**Author:** Matthew Dean
Martin [matthewdeanmartin@users.noreply.github.com](mailto:matthewdeanmartin@users.noreply.github.com)
**BDFL-Delegate:** TBC
**Status:** Draft
**Type:** Standards Track
**Topic:** Packaging
**Created:** 2025-10-21
**Post-History:** 2025-10-21
**Resolution:** TBC

---

## Abstract

This PEP defines the *Identity Package*: a lightweight, verifiable artifact for establishing digital trust in
open-source ecosystems. An Identity Package encodes a maintainer’s identity links, contact policies, continuity plan,
cryptographic signatures, and optional funding data. It is *just enough identity for purpose* — not to verify
citizenship or personal documents, but to build confidence that a real, persistent actor controls their code and contact
channels.

Trust arises partly through **cryptography** (verifiable signatures, rel=me links) and partly through **expensive
signals** such as long-lived accounts, ongoing maintenance, and consistent publishing history.

---

## Motivation

Software ecosystems suffer from uncertainty about who maintains what. Inactive packages, impersonations, and abandoned
namespaces create risk. Yet full legal identity verification is neither practical nor desirable.

Instead, this PEP introduces an intermediate trust layer:

* Just enough identity disclosure for the purpose at hand.
* Strong cryptographic verifiability where possible.
* Clear social and continuity signals elsewhere.

---

## Rationale

* **Leverage existing infrastructure:** distributed via PyPI as a normal package.
* **Machine-first, human-auditable:** JSON manifest + detached signature.
* **Purpose-limited:** identity data sufficient only to establish trust, not legal verification.
* **Expensive signaling:** time, effort, and sustained contribution act as auxiliary proofs of authenticity.

---

## Specification

### 1. Package Layout

```
<distribution root>/
  pyproject.toml
  identity/
    identity.json
    identity.json.asc
    funding.yml               # optional GitHub-compatible format
  data/
    resume.json               # optional JSON Resume
    resume.vcf                 # optional vCard
```

### 2. Metadata

`pyproject.toml` **MUST** include:

```toml
[project]
name = "id-<handle>"
description = "Identity package for <person|org>"
classifiers = [
    "Framework :: Identity",
    "Topic :: Security :: Cryptography",
]
```

---

### 3. Manifest Schema (v1.1)

#### Required Sections

* `subject` — basic human-readable identity.
* `keys` — OpenPGP or similar cryptographic anchors.
* `evidence` — identity links (`rel_me` optional).
* `contact_policy` — matrix of acceptable communication modes.
* `continuity` — plan for handoff when inactive.

#### Optional Sections

* `funding` — sponsorship information (compatible with GitHub FUNDING.yml).
* `claimed_domains` — verifiable proof of domain control.
* `resume` — structured résumé or vCard.
* `extras` — arbitrary metadata.

---

### 4. Continuity Policy

A continuity block defines what happens when the maintainer disappears.

```json
"continuity": {
"inactivity_threshold_days": 365,
"handoff_policy": "foundation-stewardship",
"successors": [
{
"display_name": "Open Source Commons Foundation",
"contact": "steward@oscf.example",
"evidence_url": "https://oscf.example/projects"
}
]
}
```

If the maintainer is inactive beyond the threshold, the specified successor or steward may assume control.

---

### 5. Claimed Domains

Proof of control for owned domains can be provided through:

* DNS TXT record `_idpkg.<domain>`.
* HTTP file `/.well-known/idpkg.json` with a signed payload.

Example:

```json
"claimed_domains": [
{
"domain": "example.org",
"proofs": [
{"kind": "dns_txt", "value": "idpkg=package:id-example; fp=0123...ABC"}
]
}
]
```

---

### 6. Funding

Identity Packages can declare funding links directly or embed a `funding.yml` compatible file.

```json
"funding": {
"github": ["exampleuser"],
"open_collective": "exampleuser",
"custom": ["https://example.org/sponsor"],
"packaged_file": "identity/funding.yml"
}
```

The YAML file follows GitHub's format for backward compatibility.

---

### 7. Transparency of Intent

Transparency declarations make it clear how maintainers engage with their users.

```json
"transparency": {
"maintenance_status": "security-fixes-only",
"support_policy": "community-only",
"telemetry": {
"collects_telemetry": false,
"policy_url": "https://example.org/telemetry"
}
}
```

Other possible flags:

* `maintenance_status`: active, seeking-maintainers, archived.
* `support_policy`: best-effort, community-only, paid-support, no-support.
* `telemetry`: discloses data collection and defaults.

These disclosures are *not legal contracts*, but social clarity signals.

---

### 8. Contact Policy

Defines what types of contact are welcome.

```json
"contact_policy": {
"matrix": {
"bug_reports": {"allowed": true, "channels": [{"kind": "webform", "address": "https://github.com/example/issues"}]},
"job_offers": {
"allowed": false
},
"maintainer_apply": {"allowed": true}
},
"security": {
"channel": {
"kind": "email", "address": "security@example.org"
},
"encryption_required": true
}
}
```

---

### 9. Trust Model

Trust in identity packages is multi-dimensional:

| Category              | Mechanism                                                   | Description                   |
|-----------------------|-------------------------------------------------------------|-------------------------------|
| **Cryptographic**     | Signatures, PGP fingerprints, rel=me reciprocity            | Verifiable by machines        |
| **Expensive signals** | Long-lived accounts, consistent release cadence, reputation | Costly to fake                |
| **Continuity**        | Declared successors and inactivity thresholds               | Reduces abandonment ambiguity |
| **Transparency**      | Explicit contact & intent policy                            | Builds social reliability     |

The goal is not perfect identity, but sufficient identity for confidence in authenticity and accountability.

---

### 10. Implementation Recommendations

* **Verifiers** MUST validate signatures and schema version.
* **Verifiers** SHOULD check DNS/HTTP proofs for claimed domains.
* **Verifiers** SHOULD respect `contact_policy` and `transparency` flags.
* **Publishers** SHOULD sign Git tags and use consistent PGP keys.

---

### 11. Example

```json
{
  "schema_version": "1.1",
  "subject": {
    "kind": "person",
    "display_name": "Jane Q. Dev"
  },
  "keys": [
    {
      "kind": "openpgp",
      "fingerprint": "0123456789ABCDEF0123456789ABCDEF01234567"
    }
  ],
  "evidence": [
    {
      "url": "https://github.com/janeqdev",
      "rel_me": true,
      "kind": "github"
    },
    {
      "url": "https://fosstodon.org/@jane",
      "rel_me": true,
      "kind": "mastodon"
    }
  ],
  "claimed_domains": [
    {
      "domain": "jane.dev",
      "proofs": [
        {
          "kind": "dns_txt",
          "value": "idpkg=package:id-janeqdev; fp=0123456789ABCDEF0123456789ABCDEF01234567"
        }
      ]
    }
  ],
  "funding": {
    "github": [
      "janeqdev"
    ],
    "open_collective": "janeqdev"
  },
  "contact_policy": {
    "matrix": {
      "job_offers": {
        "allowed": false
      },
      "bug_reports": {
        "allowed": true
      }
    },
    "security": {
      "channel": {
        "kind": "email",
        "address": "security@jane.dev"
      },
      "encryption_required": true
    },
    "transparency": {
      "maintenance_status": "active",
      "support_policy": "best-effort"
    }
  },
  "continuity": {
    "inactivity_threshold_days": 365,
    "handoff_policy": "foundation-stewardship"
  }
}
```

---

## Security Considerations

* Signatures bind the manifest to its author but cannot guarantee ownership of external sites. Verifiers should combine
  crypto validation with rel=me confirmation and historical account data.
* No use of government-issued IDs; all proofs are digital and voluntary.

---

## Privacy Considerations

Identity packages are not for doxxing. They reveal *only what the maintainer chooses*, and only what is necessary to
build functional trust for open-source collaboration.

---

## Summary

Identity Packages are purpose-limited trust artifacts. They let maintainers say:

> "Here is just enough verified identity for you to trust that this software and I are the same ongoing entity."

Through a mix of cryptographic signatures, verifiable links, declared contact boundaries, continuity policy, and
expensive social signals, they build trust without exposing personal data.
