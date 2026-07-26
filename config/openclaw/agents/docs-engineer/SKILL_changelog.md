# Skill: CHANGELOG Documentation

You maintain the CHANGELOG file after successful implementation and QA validation.

## Triggered By
Kata advances to `documenting` status after QA passes

## Format (Keep a Changelog)
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Feature X for doing Y (#kata-<id>)

### Changed
- Improved Z behavior (#kata-<id>)

### Fixed
- Bug in W module (#kata-<id>)

### Removed
- Deprecated feature V (#kata-<id>)
```

## Rules
1. One entry per kata
2. Reference kata ID in parentheses: `(#kata-<id>)`
3. Group by type: Added, Changed, Fixed, Removed, Deprecated, Security
4. Date-stamp releases when a version is tagged
5. No external links (offline constraint)
6. Only add entries for changes that affect users or developers
