"""Typed schema validators for the REST Countries API (v3.1).

Provides :class:`CountryName` and :class:`CountrySchema` dataclasses that
parse and type-validate raw JSON payloads returned by ``restcountries.com``.
All parsing occurs through :meth:`from_dict` factory methods that perform
explicit field-presence checks before construction.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class CountryName:
    """Structured representation of a country's name fields.

    Attributes:
        common (str): The common English name of the country,
            e.g. ``"Germany"``.
        official (str): The official English name of the country,
            e.g. ``"Federal Republic of Germany"``.
    """

    common: str
    official: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountryName":
        """Construct a :class:`CountryName` from a raw API payload dict.

        Args:
            data (Dict[str, Any]): The ``name`` sub-object from a REST
                Countries API response. Must contain ``"common"`` and
                ``"official"`` keys.

        Returns:
            CountryName: A fully populated and type-cast instance.

        Raises:
            KeyError: If ``"common"`` or ``"official"`` is absent from
                *data*.
        """
        for field in ("common", "official"):
            if field not in data:
                raise KeyError(f"Missing mandatory field in 'name': '{field}'")
        return cls(
            common=str(data["common"]),
            official=str(data["official"]),
        )


@dataclass
class CountrySchema:
    """Full structural validator for a single REST Countries API result object.

    Attributes:
        name (CountryName): Parsed name sub-object containing common and
            official country name strings.
        capital (List[str]): List of capital city names.
        population (int): Total population count.
        currencies (Dict[str, Any]): Map of ISO 4217 currency codes to dicts
            containing ``name`` and ``symbol`` fields.
        languages (Dict[str, Any]): Map of BCP 47 language codes to language
            name strings.
        region (str): Broad geographic region, e.g. ``"Europe"``.
        cca2 (str): ISO 3166-1 alpha-2 two-letter country code.
        flags (Dict[str, str]): Map of format keys (``"png"``, ``"svg"``,
            ``"alt"``) to their corresponding URL or description strings.
    """

    name: CountryName
    capital: List[str]
    population: int
    currencies: Dict[str, Any]
    languages: Dict[str, Any]
    region: str
    cca2: str
    flags: Dict[str, str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountrySchema":
        """Construct a :class:`CountrySchema` from a raw API payload dict.

        Validates that all required top-level fields are present before
        delegating nested construction to :meth:`CountryName.from_dict`.

        Args:
            data (Dict[str, Any]): A single country object from the REST
                Countries API response array.

        Returns:
            CountrySchema: A fully populated and type-cast instance.

        Raises:
            KeyError: If any required field is absent from *data*, or if a
                nested required field is absent from the ``name`` sub-object.
        """
        required = ("name", "capital", "population", "currencies", "languages", "region", "cca2", "flags")
        for field in required:
            if field not in data:
                raise KeyError(f"Missing mandatory schema field: '{field}'")
        return cls(
            name=CountryName.from_dict(data["name"]),
            capital=[str(c) for c in data["capital"]],
            population=int(data["population"]),
            currencies=dict(data["currencies"]),
            languages=dict(data["languages"]),
            region=str(data["region"]),
            cca2=str(data["cca2"]),
            flags=dict(data["flags"]),
        )
