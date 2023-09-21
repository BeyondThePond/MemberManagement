from __future__ import annotations

import csv
import re
from datetime import datetime

from alumni.fields import (
    AlumniCategoryField,
    ClassField,
    CountryField,
    DegreeField,
    GenderField,
    MajorField,
    TierField,
)
from alumni.models import Alumni, SetupCompleted
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.db import transaction
from registry.views.setup import make_user
from registry.forms import RegistrationMixin

from typing import TYPE_CHECKING
from typing import Dict, List, Optional

if TYPE_CHECKING:
    from argparse import ArgumentParser

from alumni.utils import CSVParser


class RegistrationValidator(RegistrationMixin):
    def add_error(self, field: str, error: Exception):
        raise error


class AlumniParser(CSVParser):
    """A CSVParser for Alumni"""

    registration: RegistrationValidator

    def __init__(self):
        super().__init__()
        self.registration = RegistrationValidator()

        self.register(["birthday_de"], "birthday", self._parse_birthday_de)
        self.register(["birthday_us"], "birthday", self._parse_birthday_us)
        self.register(["title"], "gender", self._parse_title)
        self.register(["name_1_3"], "given_name", self._parse_given_name)
        self.register(["name_1_3"], "middle_name", self._parse_middle_name)

        self.register(["name_1"], "given_name", self._parse_required)
        self.register(["name_2"], "family_name", self._parse_required)
        self.register(["name_3"], "middle_name", self._parse_optional)

        self.register(["nationality_1"], "nationality_1", self._parse_country)
        self.register(["nationality_2"], "nationality_2", self._parse_country)

        self.register(["email"], "email", self._parse_email)
        self.register(["class"], "year", self._parse_class)
        self.register(["year"], "year", self._parse_year)
        self.register(["degree"], "degree", self._parse_degree)
        self.register(["major"], "major", self._parse_major)

    def _parse_birthday_de(self, birthday_de) -> datetime:
        return datetime.strptime(birthday_de, "%d.%m.%Y")

    def _parse_birthday_us(self, birthday_us) -> datetime:
        return datetime.strptime(birthday_us, "%m/%d/%y")

    def _parse_title(self, title: str) -> GenderField:
        title = title.lower().strip()
        if title == "mr.":
            return GenderField.MALE
        elif title == "ms.":
            return GenderField.FEMALE

        return GenderField.UNSPECIFIED

    def _parse_email(self, value: str) -> str:
        value = self._parse_required(value.strip())
        self.registration._validate_email(value)
        return value

    def _parse_given_name(self, value: str) -> str:
        value = self._parse_required(value.strip())
        return value.split(" ")[0]

    def _parse_middle_name(self, value: str) -> str:
        value = self._parse_required(value.strip())
        return " ".join(value.split(" ")[1:])

    def _parse_required(self, value: str) -> str:
        if value == "":
            raise Exception("Missing required value")
        return value

    def _parse_optional(self, value: str) -> Optional[str]:
        if value == "":
            return None
        return value

    COUNTRY_ALTS: Dict[str, CountryField] = {
        "USA": "United States of America",
        "Swaziland": "Eswatini",
        "Palestine": "Palestine, State of",
        "Islamabad (Pakistan)": "Pakistan",
        "Kolda (Senegal)": "Senegal",
        "Czech Republic": "Czechia",
    }

    def _parse_country(self, country: str) -> Optional[CountryField]:
        if country == "":
            return None

        # map alternate countries
        if country in self.__class__.COUNTRY_ALTS:
            country = self.__class__.COUNTRY_ALTS[country]

        # lookup the country
        for (key, desc) in CountryField.COUNTRY_CHOICES:
            if country == desc:
                return key

        # and throw for unknown countries
        raise Exception("Unknown Country: {}".format(country))

    def _parse_class(self, clz: str) -> ClassField:
        matches = list(re.findall(r"\d\d", clz))
        if len(matches) != 1:
            raise Exception(
                "Expected class {} to have exactly one year information, but got {} matches".format(
                    clz, len(matches)
                )
            )

        year = int(matches[0]) + 2000
        for (value, _) in ClassField.CHOICES:
            if value == year:
                return year

        return ClassField.OTHER

    def _parse_year(self, year: str) -> ClassField:
        matches = list(re.findall(r"\d\d\d\d", year))
        if len(matches) != 1:
            raise Exception(
                "Expected year {} to have exactly one year information, but got {} matches".format(
                    year, len(matches)
                )
            )

        year = int(matches[0])
        for (value, _) in ClassField.CHOICES:
            if value == year:
                return year

        return ClassField.OTHER

    DEGREE_ALTS: Dict[str, DegreeField] = {
        "Doctor of Philosophy": "PhD",
    }

    def _parse_degree(self, degree: str) -> DegreeField:
        # map alternate degree names
        if degree in self.__class__.DEGREE_ALTS:
            degree = self.__class__.DEGREE_ALTS[degree]

        # lookup the degree
        org_degree = degree
        degree = degree.lower()
        for (key, description) in DegreeField.CHOICES:
            if description.lower() == degree:
                return key
        raise Exception("Unknown degree: {}".format(org_degree))

    MAJOR_ALTS: Dict[str, MajorField] = {
        "Global Economics and Management": "Global Economics and Management (GEM)",
        "Biochemistry and Cell Biology": "Biochemistry and Cell Biology (BCCB)",
        "Psychologie": "Psychology",
        "International Relations: Politics and History": "International Politics and History (IPH)",
        "Medicinal Chemistry and Chemical Biology": "Medical Chemistry and Chemical Biology",
        "Cell Biology": "Biochemistry and Cell Biology (BCCB)",
        "Physics and Computer Science": "Physics",  # TODO: Support multiple mayors!
        "Geosciences": "Geosciences and Astrophysics",
        # TODO: Support multiple mayors!
        "Integrated Social Sciences & Global Economics and Management": "Integrated Social Sciences",
    }

    def _parse_major(self, major: str) -> Optional[MajorField]:
        major = major.strip()
        if major == "":
            return None

        # map alternate major names
        if major in self.__class__.MAJOR_ALTS:
            major = self.__class__.MAJOR_ALTS[major]

        org_major = major
        major = major.lower()
        for (key, description) in MajorField.CHOICES:
            if description.lower() == major:
                return key

        raise Exception("Unknown major: {0!r}".format(org_major))


class SimulateException(Exception):
    pass


class Command(BaseCommand):
    help = "Import a CSV of generated users"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("files", nargs="*", help="Path to csv of users to import ")
        parser.add_argument(
            "--columns",
            default=",birthday_de,title,name_2,name_1,name_3,nationality_1,nationality_2,email,class,degree,major",
            help="Comma seperated list of fields to parse",
        )
        parser.add_argument(
            "--simulate",
            type=bool,
            help="Don't actually created any users, just simulate creating them",
        )
        parser.add_argument(
            "--no-stripe",
            type=bool,
            help="Skip creating stripe accounts. Use with care. ",
        )
        parser.add_argument(
            "--list-columns",
            action="store_true",
            dest="list_columns",
            help="List available columns and exit. ",
        )

    def handle(self, *args, **kwargs) -> None:
        # create the parser and required arguments
        parser = AlumniParser()
        required = ["given_name", "family_name", "email", "birthday", "nationality_1"]

        # list all columns if requested
        columns = kwargs["list_columns"]
        if columns:
            return self.list_columns(parser, required, *args, **kwargs)

        # else do the import!
        return self.do_import(parser, required, *args, **kwargs)

    def list_columns(self, parser: AlumniParser, required: List[str], *args, **kwargs):

        # fetch all available groups, and compute the maximum length
        groups = list(parser.groups())
        groups_len = max(map(lambda ct: len(ct[0]), groups))

        print("Available columns: ")
        for [column, targets] in groups:
            # add spacing for alignment
            column = column + " " * (groups_len - len(column))
            print("{}  (generated by {})".format(column, ",".join(targets)))

        print("")
        print("Required columns:")
        for r in required:
            print("{}".format(r))

    def do_import(self, parser: AlumniParser, required: List[str], *args, **kwargs):
        # Find the file to parse
        files = kwargs["files"]
        if len(files) != 1:
            raise Exception("expected exactly one file")

        # read the csv lines!
        lines: List[List[str]] = []
        with open(files[0], "r") as f:
            # open the csv file and skip the first line
            reader = csv.reader(f)
            reader.__next__()

            # store the rest of the lines
            lines = list(reader)

        columns = kwargs["columns"].split(",")

        # parse the actual fields!
        parsed, targets = parser.parse(
            columns,
            lines,
            required=required,
        )

        simulate = kwargs["simulate"]
        no_stripe = kwargs["no_stripe"]
        try:
            with transaction.atomic():
                # iterate over the users and create them, if they already exists, skip them!
                for person in parsed:
                    try:

                        # read names
                        given_name = person["given_name"]
                        middle_name = (
                            person["middle_name"] if "middle_name" in targets else None
                        )
                        if middle_name is None:
                            middle_name = ""
                        family_name = person["family_name"]

                        # read email
                        email = person["email"]
                        validate_email(email)

                        # read nationality
                        nationality = person["nationality_1"]
                        if "nationality_2" in targets:
                            nationality_2 = person["nationality_2"]
                            if nationality_2 is not None:
                                nationality = [nationality, nationality_2]

                        # read birthday
                        birthday = person["birthday"]

                        # read member type and tier
                        member_type = AlumniCategoryField.REGULAR
                        member_tier = TierField.STARTER
                        skip_stripe = simulate or no_stripe

                        # make the user and basic attributes
                        user = make_user(
                            given_name=given_name,
                            middle_name=middle_name,
                            family_name=family_name,
                            email=email,
                            nationality=nationality,
                            birthday=birthday,
                            member_type=member_type,
                            member_tier=member_tier,
                            skip_stripe=skip_stripe,
                        )

                        # Store that the user was autocreated
                        alumni: Alumni = user.alumni
                        alumni.approval.autocreated = True
                        alumni.approval.save()

                        # store the gender
                        if "gender" in targets:
                            alumni.sex = person["gender"]
                        alumni.save()

                        # store additional jacobs data
                        if "year" in targets:
                            alumni.jacobs.graduation = person["year"]
                        if "degree" in targets:
                            alumni.jacobs.degree = person["degree"]
                        if "major" in targets and person["major"] is not None:
                            alumni.jacobs.major = person["major"]
                        alumni.jacobs.save()

                        SetupCompleted.objects.create(member=alumni)

                        print("Created user {}".format(user.username))
                    except Exception as e:
                        print("Could not create user {}: {}".format(person, e))
                        continue

                if simulate:
                    raise SimulateException()
        except SimulateException:
            print("--simulate was provided, rolling back changes")
            return
