"""The data contract of one line of the BAAC « caractéristiques » file.

Every rule of this module comes from the ONISR notice « Description des bases de données
annuelles des accidents corporels de la circulation routière, années de 2005 à 2024 »
(21 October 2025). This module is the only place where those rules live.

com, atm, col and adr must be in the header (it proves this is the « caractéristiques » file)
but their values are not checked: the contract leaves them to an extension.
"""

import datetime as dt
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# The 15 columns every input file must have (their order is free, extra columns are ignored).
REQUIRED_COLUMNS = (
    "Num_Acc",
    "jour",
    "mois",
    "an",
    "hrmn",
    "lum",
    "dep",
    "com",
    "agg",
    "int",
    "atm",
    "col",
    "adr",
    "lat",
    "long",
)

# Nomenclatures of the notice, with its labels (codes 1 to n, consecutive).
LUM_LABELS = {
    1: "plein jour",
    2: "crépuscule ou aube",
    3: "nuit sans éclairage public",
    4: "nuit avec éclairage public non allumé",
    5: "nuit avec éclairage public allumé",
}
AGG_LABELS = {1: "hors agglomération", 2: "en agglomération"}
INT_LABELS = {
    1: "hors intersection",
    2: "intersection en X",
    3: "intersection en T",
    4: "intersection en Y",
    5: "intersection à plus de 4 branches",
    6: "giratoire",
    7: "place",
    8: "passage à niveau",
    9: "autre intersection",
}


class Accident(BaseModel):
    """One valid line of the file. Built from the strings of a CSV row (keys = column names)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    # Patterns use [0-9], never \d: in Pydantic's regex engine, \d also matches non-ASCII digits.
    num_acc: Annotated[str, Field(alias="Num_Acc", pattern=r"^[0-9]{12}$")]
    jour: int
    mois: int
    an: int
    hrmn: Annotated[str, Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
    lum: Annotated[int, Field(ge=min(LUM_LABELS), le=max(LUM_LABELS))]
    dep: Annotated[str, Field(pattern=r"^(2A|2B|[0-9]{2,3})$")]
    agg: Annotated[int, Field(ge=min(AGG_LABELS), le=max(AGG_LABELS))]
    intersection: Annotated[int, Field(alias="int", ge=min(INT_LABELS), le=max(INT_LABELS))]
    lat: Annotated[float, Field(ge=-90, le=90)]
    long: Annotated[float, Field(ge=-180, le=180)]

    @model_validator(mode="before")
    @classmethod
    def strip_values(cls, data: Any) -> Any:
        """The files write `" -1"`: every value loses its surrounding spaces first."""
        if isinstance(data, dict):
            return {key: v.strip() if isinstance(v, str) else v for key, v in data.items()}
        return data

    @field_validator("lat", "long", mode="before")
    @classmethod
    def decimal_comma(cls, value: Any) -> Any:
        """The file follows the French usage: `48,86638600`."""
        return value.replace(",", ".") if isinstance(value, str) else value

    @model_validator(mode="after")
    def cross_columns(self) -> Self:
        """Rules that read several columns: the date, the year of Num_Acc."""
        try:
            dt.date(self.an, self.mois, self.jour)
        except ValueError as error:
            raise ValueError(
                f"jour/mois/an: {self.jour:02d}/{self.mois:02d}/{self.an} is not a date ({error})"
            ) from error
        if self.num_acc[:4] != f"{self.an:04d}":
            raise ValueError(f"Num_Acc: {self.num_acc} does not start with an ({self.an})")
        return self
