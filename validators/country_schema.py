"""Typed schema validators for the REST Countries API (v5).

Provides :class:`CountryName`, :class:`CountrySchema`, and
:class:`CountryPopulationSchema` dataclasses that parse and type-validate
raw JSON country objects returned by ``api.restcountries.com`` (v5). All
parsing occurs through :meth:`from_dict` factory methods that perform explicit
field-presence checks before construction.

These validators operate on a single country object — i.e. one element of the
``data.objects`` list returned by the v5 API (see
:meth:`utils.api_client.ApiClient.get_objects`), not the enclosing envelope.

The v5 object model differs from the legacy v3.1 model in several ways that are
normalised here so downstream tests keep a stable shape:

* ``name.common/official`` is now nested under ``names``.
* ``cca2`` is now ``codes.alpha_2``.
* ``capital`` (list of strings) is now ``capitals`` (list of objects).
* ``currencies`` and ``languages`` are now lists of objects, not maps.
* ``flags`` (image URLs) is now ``flag`` (a dict of emoji/description fields).
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
        """Construct a :class:`CountryName` from a raw v5 ``names`` payload dict.

        Args:
            data (Dict[str, Any]): The ``names`` sub-object from a REST
                Countries v5 country object. Must contain ``"common"`` and
                ``"official"`` keys.

        Returns:
            CountryName: A fully populated and type-cast instance.

        Raises:
            KeyError: If ``"common"`` or ``"official"`` is absent from
                *data*.
        """
        for field in ("common", "official"):
            if field not in data:
                raise KeyError(f"Missing mandatory field in 'names': '{field}'")
        return cls(
            common=str(data["common"]),
            official=str(data["official"]),
        )


@dataclass
class CountrySchema:
    """Full structural validator for a single REST Countries v5 country object.

    Attributes:
        name (CountryName): Parsed name sub-object containing common and
            official country name strings (sourced from ``names``).
        capital (List[str]): List of capital city names (sourced from the
            ``name`` field of each entry in ``capitals``).
        population (int): Total population count.
        currencies (List[Dict[str, Any]]): List of currency objects, each
            containing ``code``, ``name``, and ``symbol`` fields.
        languages (List[Dict[str, Any]]): List of language objects, each
            containing ``name`` and ISO/BCP-47 code fields.
        region (str): Broad geographic region, e.g. ``"Europe"``.
        cca2 (str): ISO 3166-1 alpha-2 two-letter country code (sourced from
            ``codes.alpha_2``).
        flag (Dict[str, Any]): Flag descriptor with keys such as ``emoji``,
            ``description``, ``html_entity``, and ``unicode``.
    """

    name: CountryName
    capital: List[str]
    population: int
    currencies: List[Dict[str, Any]]
    languages: List[Dict[str, Any]]
    region: str
    cca2: str
    flag: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountrySchema":
        """Construct a :class:`CountrySchema` from a raw v5 country object.

        Validates that all required top-level fields are present before
        delegating nested construction to :meth:`CountryName.from_dict`.

        Args:
            data (Dict[str, Any]): A single country object from the
                ``data.objects`` list of a REST Countries v5 response.

        Returns:
            CountrySchema: A fully populated and type-cast instance.

        Raises:
            KeyError: If any required field is absent from *data*, from the
                ``codes`` sub-object, or from a nested capital entry.
        """
        required = ("names", "capitals", "population", "currencies", "languages", "region", "codes", "flag")
        for field in required:
            if field not in data:
                raise KeyError(f"Missing mandatory schema field: '{field}'")
        if "alpha_2" not in data["codes"]:
            raise KeyError("Missing mandatory field in 'codes': 'alpha_2'")
        return cls(
            name=CountryName.from_dict(data["names"]),
            capital=[str(entry["name"]) for entry in data["capitals"]],
            population=int(data["population"]),
            currencies=[dict(item) for item in data["currencies"]],
            languages=[dict(item) for item in data["languages"]],
            region=str(data["region"]),
            cca2=str(data["codes"]["alpha_2"]),
            flag=dict(data["flag"]),
        )


@dataclass
class CountryPopulationSchema:
    """Minimal validator for fields-filtered country responses.

    Used when the API query restricts returned fields to the common name and
    population only (e.g. ``response_fields=names.common,population``).
    Full-field responses should use :class:`CountrySchema` instead.

    Attributes:
        name_common (str): The common English name of the country.
        population (int): Total population count.
    """

    name_common: str
    population: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CountryPopulationSchema":
        """Construct a :class:`CountryPopulationSchema` from a raw v5 payload dict.

        Only the common name and population are required, so this validator
        accepts the slimmed payload produced by
        ``response_fields=names.common,population`` without demanding the
        official name.

        Args:
            data (Dict[str, Any]): A single country object containing at least
                ``"names"`` (with a ``"common"`` key) and ``"population"``.

        Returns:
            CountryPopulationSchema: A fully populated and type-cast instance.

        Raises:
            KeyError: If ``"names"`` or ``"population"`` is absent from
                *data*, or if ``"common"`` is absent from the ``names``
                sub-object.
        """
        for field in ("names", "population"):
            if field not in data:
                raise KeyError(f"Missing mandatory schema field: '{field}'")
        if "common" not in data["names"]:
            raise KeyError("Missing mandatory field in 'names': 'common'")
        return cls(
            name_common=str(data["names"]["common"]),
            population=int(data["population"]),
        )
