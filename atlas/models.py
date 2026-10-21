from __future__ import annotations

import warnings
import re

from django.db import models, transaction

from alumni.models import Alumni
from alumni.fields import CountryField

from registry.alumni import AlumniComponentMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional, List, Dict, Any
    from django_countries.fields import Country


@Alumni.register_component(5)
class AtlasSettings(AlumniComponentMixin, models.Model):
    member: Alumni = models.OneToOneField(
        Alumni, related_name="atlas", on_delete=models.CASCADE
    )

    included: bool = models.BooleanField(
        default=False,
        blank=True,
        help_text="Include me in the Alumni Atlas. By selecting this checkbox, your location (approximated by your zip code), your city, and other information about you will be visible on the atlas interface to other users. ",
    )
    reducedAccuracy: bool = models.BooleanField(
        default=False,
        blank=True,
        help_text="When showing me on the map, reduce accuracy from zip code level to administrative division (i.e. city/region) level. ",
    )

    birthdayVisible: bool = models.BooleanField(
        default=False, blank=True, help_text="Show Birthday on my Alumni Atlas Profile"
    )

    contactInfoVisible: bool = models.BooleanField(
        default=False,
        blank=True,
        help_text="Show Social Media and Contact information (like @jacobs-alumni email) on the Alumni Atlas Profile Page. ",
    )

    secret: Optional[str] = models.TextField(
        null=True,
        blank=True,
        help_text="Secret Search Text that the member can be found with",
    )

    @classmethod
    def component_exists(cls, alumni: Alumni) -> bool:
        return True


class GeoLocation(models.Model):
    """Represents a (cached) GeoLocation"""

    country: Country = CountryField()
    zip: str = models.CharField(max_length=10)

    group1: str = models.TextField()
    group2: str = models.TextField()
    group3: str = models.TextField()

    lat: float = models.FloatField()
    lon: float = models.FloatField()

    class Meta:
        unique_together = ("country", "zip")

    def reduced_accuracy(self) -> GeoLocation:
        """Returns an instance in roughly the same location, but with reduced accuracy"""
        if self.group1 and self.group2 and self.group3:
            return GeoLocation.objects.filter(
                country=self.country,
                group1=self.group1,
                group2=self.group2,
                group3=self.group3,
            ).first()
        if self.group1 and self.group2:
            return GeoLocation.objects.filter(
                country=self.country, group1=self.group1, group2=self.group2
            ).first()
        if self.group1:
            return GeoLocation.objects.filter(
                country=self.country, group1=self.group1
            ).first()
        else:
            return self

    @classmethod
    def getLocInstance(
        cls, country: Optional[str], zip: Optional[str]
    ) -> Optional[GeoLocation]:
        try:
            return cls.objects.get(
                country=country, zip=cls.normalize_zip(zip, country.code)
            )
        except cls.DoesNotExist:
            # warnings.warn('No location for combination: {} {}'.format(
            #    country.code, cls.normalize_zip(zip, country.code)))
            return None

    @classmethod
    def getLoc(
        cls, country: Optional[str], zip: Optional[str], reduced_accuracy: bool = True
    ) -> Union[Tuple[float, float], Tuple[None, None]]:
        instance = cls.getLocInstance(country, zip)
        if instance is None:
            return None, None
        if reduced_accuracy:
            instance = instance.reduced_accuracy()
        return instance.lat, instance.lon

    @classmethod
    def updateData(cls, data: List[Dict[str, Any]]):
        with transaction.atomic():
            cls.objects.all().delete()
            cls.objects.bulk_create(data)

    @classmethod
    def normalize_zip(
        self, zip: Optional[str], country: Optional[str]
    ) -> Optional[str]:

        # when no zip is given we can't normalize anything
        if zip is None:
            return None

        lowerzip = zip.lower()
        norm = re.sub(r"[^0-9a-z]", "", lowerzip)

        # Canada: First three characters
        if country == "CA":
            norm = norm[0:3]
        # Great Briatin: First four characters
        elif country == "GB":
            norm = norm[0:4]
        # Netherlands: digits only
        elif country == "NL":
            norm = re.sub(r"[^0-9]", "", norm)
        return norm

    def __str__(self) -> str:
        return "GeoLocation of {} in {}".format(self.zip, self.country)
