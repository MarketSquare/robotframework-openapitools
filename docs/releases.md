# Release notes

## OpenApiTools v2.0.0

### Major changes and new features
- Request bodies now support all JSON types, not just `objects` (`dicts`).
    - This closes [issue #9: No body generated when root is a list](https://github.com/MarketSquare/robotframework-openapitools/issues/9).
    - The `Relations` still need to be reworked to align with this change.
- Refactored retrieving / loading of the OpenAPI spec.
    - This closes [issue #93: SSL error even if cert / verify is set](https://github.com/MarketSquare/robotframework-openapitools/issues/93).
- Added keywords to make it easier to work with the `RequestValues` object:
    - `Get Request Values Object` can be used to create a `RequestValues` instance from pre-defined values (where `Get Request Values` generates all values automatically).
    - `Perform Authorized Request` is functionally the same as exisiting `Authorized Request` keyword, but it accepts a `RequestValues` instance as argument.
    - `Validated Request` is functionally the same as the existing `Perform Validated Request` keyword, but it accepts the data as separate arguments instead of the `RequestValues`.
    - `Convert Request Values To Dict` can be used to get a (Python) dict represenation of a `RequestValues` object that can be used with e.g. the Collections keywords for working with dictionaries.
    - Thise closes [issue #98: Add keywords to simplify using Authorized Request and Perform Validated Request](https://github.com/MarketSquare/robotframework-openapitools/issues/98).
- Improved handling of `treat_as_mandatory` on a `PropertyValueConstraint`.
- Added support for using `IGNORE` as `invalid_value` on a `PropertyValueConstraint`.

### Bugfixes
- Added support for the `nullable` property in OAS 3.0 schemas when generating data.
    - This closes [issue #81: nullable not taken into account in get_valid_value](https://github.com/MarketSquare/robotframework-openapitools/issues/81).
- Support added for multiple instances of OpenApiLibCore within the same suite.
    -  This closes [issue #96: Multiple keywords with same name error when using multiple generated libraries](https://github.com/MarketSquare/robotframework-openapitools/issues/96).
- Fixed validation errors caused by `Content-Type` not being handled case-insensitive.
- Fixed an exception during validation caused by `charset` being included in the `Content-Type` header for `application/json`.

### Breaking changes
- Addressing [issue #95: Refactor: better name for Dto](https://github.com/MarketSquare/robotframework-openapitools/issues/95) introduces a number breaking renames:
    - `Dto` has been renamed to `RelationsMapping`.
    - `constraint_mapping` has been renamed to `relations_mapping` in a number of places.
    - `DTO_MAPPING` has been renamed to `RELATIONS_MAPPING`.
- The `RequestData` class that is returned by a number of keywords has been changed:
    - The `dto` property was removed.
    - The `valid_data` property was added.
    - The `relations_mapping` property was added.
- `invalid_property_default_response` library parameter renamed to `invalid_data_default_response`.

### Additional changes
- Special handling of `"format": "byte"` for `"type": "string"` (OAS 3.0) was removed.
    - While some logic related to this worked, the result was never JSON-serializable.
- The devcontainer setup was updated.
- The GitHub pipeline was updated to include Python 3.14.
- Updated minimum version markers for many dependencies.
- Annotations are now complete (as far as possible under Python 3.10).

<br><br><br>

## Previous versions

### OpenApiTools v1.0.5

#### Bugfixes
- `parameters` at path level are not taken into account at operation level.

---

### OpenApiTools v1.0.4

#### Bugfixes
- Prevent runtime exception for unsupported regex patterns in OAS.
- Prevent trailing underscores in generated keyword method names.

#### Additional changes
- `generate-library` CLI interaction now prompts for behavior that was previously only available by setting the environment variables `USE_SUMMARY_AS_KEYWORD_NAME` and `EXPAND_BODY_ARGUMENTS`.

---

### OpenApiTools v1.0.3

#### Bugfixes
- Fix runtime exception on ObjectSchemas without `properties` defined in the OAS.

#### Additional changes
- Python 3.14 compatibility tested and lock file updated.

---

### OpenApiTools v1.0.2

#### Bugfixes
- Multiple `PropertyValueConstraint` instances for the same `property_name` caused an exception.
- `Get Invalidated Parameters` now properly handles situations where `invalid_value` is set to `IGNORE`.

---

### OpenApiTools v1.0.1

#### Bugfixes
- `openapitools_docs` was missing from package distribution.

---

### OpenApiTools v1.0.0 (yanked)

#### Major changes and new features
- Added a CLI tool for library generation. See the `OpenApiLibGen` documentation for all the details.
- Support for nested `Dtos` in `Relation` constraints [(issue #49)](https://github.com/MarketSquare/robotframework-openapitools/issues/49).
- The core logic has been rewritten to use Pydantic models under the hood.
This rewrite has made the addition of the library generator possible and allows feature implementations in future releases that were previously (too) hard to implement.
- The documentation has been restructured / rewritten and should now be much more coherent and accessible.

#### Bugfixes
- No specific bugfixes have been made, but the core refactor of the application has solved a number of undocumented issues.

#### Breaking changes
- `PathPropertiesConstraint` is now a separate type of `Relation`. See the `Advanced Use` documentation for details.
- In a number of places, the terms `url`, `path` and `endpoint` were not correctly and / or consistently used. This has been corrected.
    - A `url` is a complete url which can be use e.g. in a browser or http request.
    - A `path` is a portion of an `url`.
    In the scope of OpenApiTools, a `path` corresponds to an entry in the paths section of an OpenAPI specification document.
    - From a standards / definition point of view "all endpoints are URLs, not all URLs are endpoints".
    An `endpoint` represents a specific function offered by an API.
    Due to this subtle difference, when the term endpoint is used in the OpenApiTools documentation, it refers to the combination of an `url` and a corresponding HTTP operation / verb as they are found under the path entries in an OpenAPI specification document.
