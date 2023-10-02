# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.12] - 2023-10-02

### Added

- Added the Unreleased section to CHANGELOG.md;
- Handle exceptions raised by the `compile_expression` Jinja function.

### Changed

- Changed `version` in project metadata from static to dynamic.

### Fixed

- Trigger events using user arguments plus computed inheritance;
- Don't ignore default values when updating an object that doesn't exist;
- Minor bugs fixed and some refactorings.

## [0.11.0] - 2023-09-17

### Added

- First release.

[unreleased]: https://github.com/nuncard/tfadm/compare/v0.12...HEAD
[0.12]: https://github.com/nuncard/tfadm/compare/v0.11.0...v0.12
[0.11.0]: https://github.com/nuncard/tfadm/releases/tag/v0.11.0
