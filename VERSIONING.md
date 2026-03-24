# Versioning Guide

This repository uses Semantic Versioning for public releases.

## Version Source of Truth

- Repository release version: `README.md` -> `当前版本`
- Change history: `README.md` -> `Changelog`
- Git release tag format: `vMAJOR.MINOR.PATCH`

Example:

```text
README current version -> 0.1.0
git tag name           -> v0.1.0
```

## Increment Rules

### MAJOR

Increase `MAJOR` for backward-incompatible changes, including:

- breaking changes to the skill input contract in [`SKILL.md`](./SKILL.md)
- incompatible schema changes documented in [`SCHEMA.md`](./SCHEMA.md)
- stage removal or output filename changes that break existing automation
- removal or incompatible renaming of public runner flags

### MINOR

Increase `MINOR` for backward-compatible feature evolution, including:

- new pipeline stages or optional outputs
- new config fields with backward-compatible defaults
- new environment templates, runner scripts, or integration modes
- substantial documentation expansion for newly supported workflows

### PATCH

Increase `PATCH` for backward-compatible fixes and maintenance, including:

- bug fixes
- prompt or scoring adjustments that do not break contracts
- documentation corrections
- retry, logging, or operational improvements without contract breaks

## Release Checklist

Before creating a release tag:

1. Update `README.md` -> `当前版本`.
2. Add a dated entry under `README.md` -> `Changelog`.
3. Confirm the README and linked docs still match the real scripts and config defaults.
4. Create a release commit.
5. Create an annotated tag matching the version in README.
6. Push the commit and tag together.

## Suggested Git Commands

```powershell
git add README.md VERSIONING.md
git rm CHANGELOG.md VERSION
git commit -m "docs: fold release metadata into readme"
git push origin main
```

## Notes

- Do not create a release tag without updating the version section in `README.md`.
- If the code contract changes but the release scope is unclear, bias toward a higher version, not a lower one.
- `schema_version` in [`SCHEMA.md`](./SCHEMA.md) is a contract version, not the same thing as the repository release version.
