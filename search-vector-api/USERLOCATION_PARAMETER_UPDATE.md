# UserLocation Parameter Update

## Summary

Added a new `userLocation` parameter to the search API to support structured user location data with geographic coordinates and metadata. This complements the existing `location` string parameter.

## Changes Made

### 1. API Schema (`src/resources/search.py`)

#### Added UserLocationSchema

```python
class UserLocationSchema(Schema):
    """Schema for validating user location data."""
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    city = fields.Str(required=False)
    region = fields.Str(required=False)
    country = fields.Str(required=False)
    timestamp = fields.Int(required=False)
```

#### Updated SearchRequestSchema

Added `userLocation` as a nested field:

```python
userLocation = fields.Nested(UserLocationSchema, data_key="userLocation", required=False)
```

### 2. Documentation Updates

Updated the following files to document the new parameter:

- **DOCUMENTATION.md**: Added comprehensive userLocation documentation with examples
- **README.md**: Added userLocation to API examples and parameter descriptions
- **test-api.http**: Added example HTTP request with userLocation

### 3. Parameter Comparison

| Parameter | Type | Purpose | Usage |
|-----------|------|---------|-------|
| `userLocation` | Object | Structured user geographic data with coordinates | Future location-aware filtering and ranking |
| `location` | String | Geographic context string | Currently appended to query for semantic matching |

Both parameters are optional and can be used independently or together.

## API Usage Examples

### Example 1: Using userLocation only

```json
{
  "query": "environmental assessments near me",
  "userLocation": {
    "latitude": 48.4284,
    "longitude": -123.3656,
    "city": "Victoria",
    "region": "British Columbia",
    "country": "Canada",
    "timestamp": 1696291200000
  }
}
```

### Example 2: Using location string only

```json
{
  "query": "environmental assessments",
  "location": "Langford British Columbia"
}
```

### Example 3: Using both parameters

```json
{
  "query": "recent environmental assessments",
  "userLocation": {
    "latitude": 48.4284,
    "longitude": -123.3656,
    "city": "Victoria",
    "region": "British Columbia"
  },
  "location": "Langford British Columbia",
  "projectStatus": "recent",
  "years": [2023, 2024, 2025]
}
```

## UserLocation Object Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `latitude` | Float | Yes | Geographic latitude coordinate (-90 to 90) |
| `longitude` | Float | Yes | Geographic longitude coordinate (-180 to 180) |
| `city` | String | No | City name |
| `region` | String | No | Region, province, or state name |
| `country` | String | No | Country name |
| `timestamp` | Integer | No | Unix timestamp in milliseconds when location was captured |

## Current Behavior

- **userLocation**: Currently passed to the API but not yet used for filtering or ranking. Reserved for future location-aware features.
- **location**: Currently appended to the search query string for semantic matching.

## Future Enhancements

Potential uses for the structured userLocation data:

- Distance-based search result ranking
- Geographic boundary filtering
- Location-aware result prioritization
- Proximity-based relevance scoring
- Regional search optimization

## Backward Compatibility

✅ **Fully backward compatible** - All changes are additive:

- Existing API calls without userLocation continue to work
- No breaking changes to request or response formats
- Optional parameter with no required fields except latitude/longitude when provided

## Testing

Test the new parameter using the examples in `test-api.http`:

```http
POST http://localhost:8080/api/vector-search
Content-Type: application/json

{
  "query": "recent environmental assessments",
  "userLocation": {
    "latitude": 48.4284,
    "longitude": -123.3656,
    "city": "Victoria",
    "region": "British Columbia",
    "country": "Canada"
  },
  "location": "Langford British Columbia",
  "projectStatus": "recent",
  "years": [2023, 2024, 2025]
}
```

## Files Modified

1. `src/resources/search.py` - Added UserLocationSchema and userLocation field
2. `DOCUMENTATION.md` - Added userLocation documentation and examples
3. `README.md` - Added userLocation to API usage examples
4. `test-api.http` - Added example HTTP request with userLocation

## Next Steps

To implement location-aware search features:

1. Add location distance calculation logic
2. Implement geographic boundary filtering
3. Add proximity-based result ranking
4. Update search service to use userLocation data
5. Add location-specific metrics to search results
