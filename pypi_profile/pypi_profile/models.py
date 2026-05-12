"""Pydantic data models for pypi-profile TOML schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

ClaimStatus = Literal[
    "self_asserted", "verified", "unverified", "invalid", "expired", "unknown"
]

PrincipalKind = Literal[
    "individual",
    "team",
    "company",
    "llc",
    "foundation",
    "collective",
    "project",
    "other",
]

PackageState = Literal[
    "active",
    "maintained",
    "stable",
    "experimental",
    "planning",
    "paused",
    "archived",
    "deprecated",
    "abandoned",
    "transferred",
    "seeking-maintainer",
    "security-only",
    "unmaintained-but-usable",
    "superseded",
    "private",
    "unknown",
]

PackageRole = Literal[
    "author",
    "creator",
    "owner",
    "maintainer",
    "co-maintainer",
    "contributor",
    "release-manager",
    "security-contact",
    "documentation-maintainer",
    "original-creator",
    "current-steward",
    "former-maintainer",
    "sponsor",
    "employer",
    "client",
    "vendor",
    "successor",
]


class ProfileSection(BaseModel):
    kind: PrincipalKind = "individual"
    display_name: str = ""
    summary: str = ""


class IdentitySection(BaseModel):
    legal_name: str = ""
    display_name: str = ""
    pypi_username: str = ""
    pronouns: str = ""
    timezone: str = ""
    location: str = ""


class HumanEntry(BaseModel):
    id: str
    display_name: str = ""
    role: str = ""
    bio: str = ""


class ProfileLink(BaseModel):
    kind: str
    label: str
    url: str
    verification: ClaimStatus = "self_asserted"


class ContactMethod(BaseModel):
    kind: str
    label: str
    value: str
    audience: list[str] = []
    visibility: Literal["public", "obfuscated", "link"] = "public"


class PackageEntry(BaseModel):
    name: str
    role: PackageRole = "maintainer"
    state: PackageState = "active"
    summary: str = ""
    url: str = ""


class ProjectEntry(BaseModel):
    name: str
    url: str = ""
    role: str = "creator"
    state: PackageState = "active"
    summary: str = ""


class WorkEntry(BaseModel):
    organization: str
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    summary: str = ""


class HiringSection(BaseModel):
    open_to_work_since: str = ""
    employment_types: list[str] = []
    work_model: list[str] = []
    jurisdiction: list[str] = []
    speaking: bool = False
    sponsorship: bool = False


class ContractingSection(BaseModel):
    legal_entity: str = ""
    engagement_types: list[str] = []


class SuccessionContact(BaseModel):
    name: str
    contact: str = ""
    scope: list[str] = []
    relationship: str = ""
    verification: ClaimStatus = "self_asserted"


class SuccessionSection(BaseModel):
    policy: str = ""
    last_reviewed: str = ""
    contacts: list[SuccessionContact] = []


class ContactPreferences(BaseModel):
    do_contact_about: list[str] = []
    do_not_contact_about: list[str] = []


class VerificationSection(BaseModel):
    public_key: str = ""
    preferred_signature_backend: str = "minisign"


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

    @field_validator("profile", mode="before")
    @classmethod
    def coerce_profile(cls, v: object) -> object:
        if isinstance(v, dict):
            return ProfileSection(**v)
        return v
