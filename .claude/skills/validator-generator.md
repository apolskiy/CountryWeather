### `.claude/skills/validator-generator.md`
```markdown
# Skill: Validator Generator for CountryWeather Framework

## Context
Use this skill to convert raw JSON payloads into strict, typed schema validators residing in the `validators/` path.

## Inputs Required
* Sample JSON payload from the target API response.

## Execution Template
Generate a Python dataclass or structural validator that implements explicit key-checking and type-casting:

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CountrySchema:
    name: Dict[str, Any]
    capital: List[str]
    population: int
    currencies: Dict[str, Any]
    languages: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountrySchema":
        # Enforce structural integrity rules explicitly
        required_fields = ["name", "capital", "population", "currencies", "languages"]
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Missing mandatory schema field: '{field}'")
                
        return cls(
            name=data["name"],
            capital=data["capital"],
            population=int(data["population"]),
            currencies=data["currencies"],
            languages=data["languages"]
        )