# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

### Added

- Added the Unreleased section to CHANGELOG.md;
- Handle exceptions raised by the `compile_expression` Jinja function.

### Changed

- Changed `version` in project metadata from static to dynamic.

### Fixed

- Trigger events using user arguments plus computed inheritance;
- Don't ignore default values when updating an object that doesn't exist.

## [0.11.0] - 2023-09-17

### Added

- First release.

[unreleased]: https://github.com/nuncard/tfadm/compare/v0.11.0...dev
[0.11.0]: https://github.com/nuncard/tfadm/releases/tag/v0.11.0
