# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.14.1] - 2023-11-25

### Fixed

- `methods/sync/when` clause not applied when parent arguments are missing.

## [0.14] - 2023-11-14

### Changed

- By default ignore `variable` resource inherited properties that do not have a description;

### Fixed

- `create` command calls a duplicate of `cli_update` function;
- Improved `Update` method debug messages;
- Use default value if value is null;
- Do not convert null values to string;
- Parse an existing path even if it is not full;
- Virtual path inherited out of order;
- Refactored `Resource.trigger()` method;

## [0.13] - 2023-10-08

### Added

- Added CODEOWNERS file;
- Added `events/{event}/{command}/{resource}/internal` config key;
- Added `onbeforesave` event.

### Changed

- Removed `properties\{name}\conflits_with` config key;
- `conflits_with` config key renamed to `conflicts_with`;
- Removed `properties\{name}\onbeforesaving` config key.

### Fixed

- Apply `when` condition when getting primary key arguments;
- Apply `when` condition when converting infrastructure settings to arguments;
- Inheritance must not include non-inheritable primary key arguments;
- Resolve the object's primary key before applying sync filters;
- Allow translating values to `null`.

## [0.12] - 2023-10-02

### Added

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

[unreleased]: https://github.com/nuncard/tfadm/compare/v0.14.1...HEAD
[0.14.1]: https://github.com/nuncard/tfadm/compare/v0.14...v0.14.1
[0.14]: https://github.com/nuncard/tfadm/compare/v0.13...v0.14
[0.13]: https://github.com/nuncard/tfadm/compare/v0.12...v0.13
[0.12]: https://github.com/nuncard/tfadm/compare/v0.11.0...v0.12
[0.11.0]: https://github.com/nuncard/tfadm/releases/tag/v0.11.0
