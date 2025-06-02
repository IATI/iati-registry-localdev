"""Model to generate a fake IATI corpus for testing and development purposes"""

import collections
import math
import random
import tomllib
import uuid
from datetime import datetime, timedelta
from typing import List

import faker
import pycountry
import pytz

from .random import org_id, pareto, poisson, uniform_dates, uuid4
from .records import FakeDataset, FakeDatasetAction, FakeOrg, FakeOrgAction, FakePerson

# Get a mapping from countries to locales.  We manually remove
# "dk_DK" as dk does not seem to be an ISO 639-1 language code.
COUNTRY_LOCALE_MAPPING = {}
for locale in faker.config.AVAILABLE_LOCALES:
    if locale[:2] != "dk":
        if len(locale) > 2:
            country = locale[3:]
            if country not in COUNTRY_LOCALE_MAPPING.keys():
                COUNTRY_LOCALE_MAPPING[country] = []
            COUNTRY_LOCALE_MAPPING[country].append(locale)


class FakeCorpus:

    CAPACITY_CHOICES = ["admin", "editor", "member"]
    FIRST_REGISTRATION_USE_CASE_CHOICES = ["reporting", "membership", "api_access", "community"]

    def __init__(
        self,
        parameters_filename: str,
        seed: int = 8192,
        safe_emails: bool = True,
        safe_urls: bool = True,
        fake_uuids: bool = False,
    ):
        """Initialise a model generator object.

        Parameters
        ----------
        parameters_filename : str
            Filename for a model parameter TOML file.
        seed : int, optional
            Seed for the internal random number generators, by default 8192
        safe_emails : bool, optional
            Generate "safe" email addresses from example.* domains, default True.
        safe_urls : bool, optional
            Generate "safe" urls from example.* domains, default True.
        fake_uuids: bool, optional
            Generate fake UUIDs that can be clearly spotted as fake.
        """

        self._load_and_process_config(parameters_filename)

        # This is where we store the corpus.
        self.orgs = collections.OrderedDict({})
        self.people = collections.OrderedDict({})
        self.people_org_mapping = {}
        self.datasets = collections.OrderedDict({})
        self.dataset_actions = collections.OrderedDict({})
        self.org_actions = collections.OrderedDict({})
        self.multi_org_people_ids = []

        # Map countries in the model setup file to locale codes.
        self.locales = []
        for country in self.org_countries:
            if country in COUNTRY_LOCALE_MAPPING:
                for locale in COUNTRY_LOCALE_MAPPING[country]:
                    self.locales.append(locale)

        # Setup random number and faking generators.
        faker.Faker.seed(seed)
        self.faker = faker.Faker(self.locales)
        self.rnd = random.Random()
        self.rnd.seed(seed)
        self.seed = seed

        self._random_uuid = lambda rnd: str(uuid.UUID(int=rnd.getrandbits(128), version=4))
        if fake_uuids:
            self._random_uuid = lambda rnd: uuid4(rnd)

        # Runtime options.
        self.safe_urls = safe_urls
        self.safe_emails = safe_emails

    def _load_and_process_config(self, filename: str):
        """Load the configuration TOML file and process the data

        Parameters
        ----------
        filename : str
            Filename to load.
        """
        # Load the model parameters.
        try:
            fh = open(filename, "rb")
            self.parameters = tomllib.load(fh)
        except Exception as err:
            print(f"Cannot load parameters TOML file: {err}")
            raise

        # Remove countries from the configuration for which there isn't a Faker provider.
        countries_to_remove = []
        for country_code in self.parameters["orgs"]["countries"]:
            if country_code not in COUNTRY_LOCALE_MAPPING:
                countries_to_remove.append(country_code)
        [self.parameters["orgs"]["countries"].pop(x) for x in countries_to_remove]
        print("Countries not available in faker removed: ", countries_to_remove)

        # Unpack some of the model parameters - these are mostly dictionaries
        # that need separating into two lists for calling random.choices().
        self.org_countries = list(self.parameters["orgs"]["countries"].keys())
        self.org_country_weights = list(self.parameters["orgs"]["countries"].values())
        self.default_licenses = list(self.parameters["orgs"]["licenses"].keys())
        self.default_license_weights = list(self.parameters["orgs"]["licenses"].values())
        self.source_types = list(self.parameters["orgs"]["source_types"].keys())
        self.source_type_weights = list(self.parameters["orgs"]["source_types"].values())
        self.org_types = list(self.parameters["orgs"]["types"].keys())
        self.org_type_weights = list(self.parameters["orgs"]["types"].values())
        self.capacity_weights = {
            index + 1: [x["admin"], x["editor"], x["member"]]
            for index, x in enumerate(self.parameters["orgs"]["by_final_size"]["capacity_weights"])
        }
        self.num_activity_dataset_choices = [0, 1, ">1"]
        self.num_activity_dataset_weights = [
            self.parameters["datasets"]["activity"]["num_weight_zero"],
            self.parameters["datasets"]["activity"]["num_weight_one"],
            self.parameters["datasets"]["activity"]["num_weight_twoormore"],
        ]
        self.user_agents = list(self.parameters["actions"]["user_agents"].keys())
        self.user_agent_weights = list(self.parameters["actions"]["user_agents"].values())

    def _random_locale(self) -> str:
        """Randomly select a locale

        Returns
        -------
        str
            Locale string, in the format "en_GB".
        """
        country = self.rnd.choices(self.org_countries, weights=self.org_country_weights, k=1)[0]
        while country not in COUNTRY_LOCALE_MAPPING:
            country = self.rnd.choices(self.org_countries, weights=self.org_country_weights, k=1)[0]
        locale = self.rnd.choices(COUNTRY_LOCALE_MAPPING[country], k=1)[0]
        return locale

    def _random_user_agent(self) -> str:
        """Randomly select a user agent string.

        Returns
        -------
        str
        """
        return self.rnd.choices(self.user_agents, weights=self.user_agent_weights)[0]

    def _random_url(self, locale: str) -> str:
        """Generate a random url taking into account safe domain settings

        Parameters
        ----------
        locale : str
            Locale string for this url

        Returns
        -------
        str
        """
        if self.safe_urls:
            return "https://" + self.faker[locale].safe_domain_name() + "/" + self.faker[locale].slug()
        return "https://" + self.faker[locale].uri()

    def _random_email(self, locale: str, company: bool = False) -> str:
        """Generate a random email address taking into account safe domain settings

        Parameters
        ----------
        locale : str
            Locale string for this email address
        company : bool, optional
            If this should be a company email, by default False.

        Returns
        -------
        str
        """
        if self.safe_emails:
            return self.faker[locale].ascii_safe_email()
        if company:
            self.faker[locale].company_email()
        return self.faker[locale].ascii_email()

    def find_suitable_action_person(self, reporting_org_id: str, this_date: datetime) -> str:
        """Find a person ID in a reporting org to perform an action.

        Parameters
        ----------
        reporting_org_id : str
            ID of the reporting org
        this_date : datetime
            Date of the action

        Returns
        -------
        str
            UUID of the person
        """
        ids = []
        for index in range(len(self.orgs[reporting_org_id].people)):
            if (
                self.orgs[reporting_org_id].people_capacity[index] == "admin"
                or self.orgs[reporting_org_id].people_capacity[index] == "editor"
            ):
                for id in self.orgs[reporting_org_id].people[index]:
                    if self.people[id].created <= this_date and self.people[id].inactive_date > this_date:
                        ids.append(id)

        assert len(ids) > 0

        return self.rnd.choice(ids)

    def generate_fake_person(self, capacity: str, creation_date: datetime, locale: str):
        """Generate a fake person and add to the corpus

        Parameters
        ----------
        capacity : str
            CKAN user type category, "admin", "editor", or "member"
        creation_date : datetime
            When the person was created.
        locale : str
            Locale string.

        Returns
        -------
        str
            UUID for the added person.
        """
        id = self._random_uuid(self.rnd)
        person = FakePerson(id, creation_date, capacity, self.parameters["users"]["leaving_waiting_times"][capacity])
        person.set_inactive_date(self.rnd)

        short_user_name = ""
        while len(short_user_name) < 6:
            short_user_name += self.faker["en_GB"].words(1)[0]
        person.short_user_name = short_user_name
        person.name = self.faker[locale].name()
        person.in_person_name = self.faker[locale].first_name()
        person.online_name = person.in_person_name

        person.preferred_language = pycountry.languages.get(alpha_2=locale[:2]).name
        person.country_code = locale[3:]
        person.country = pycountry.countries.get(alpha_2=person.country_code).name
        person.locale = locale
        person.time_zone = self.rnd.choice(pytz.country_timezones[person.country_code])

        person.email = self.faker[locale].ascii_safe_email() if self.safe_emails else self.faker[locale].ascii_email()
        person.mailing_list = self.faker.boolean(
            chance_of_getting_true=self.parameters["users"]["mailing_list_chance"]
        )
        person.first_registration_use_cases = self.rnd.sample(
            self.FIRST_REGISTRATION_USE_CASE_CHOICES, k=self.rnd.randint(0, 3)
        )

        self.people_org_mapping[id] = []
        self.people[id] = person
        return id

    def generate_fake_org(self, creation_date: datetime, locale: str, make_reporting: bool = True):
        """Generate a fake organisation and add to the corpus

        Parameters
        ----------
        creation_date : datetime
            Creation date for the organisation.
        locale : str
            Locale string.
        make_reporting: bool, optional
            Make a reporting organisation, by default True.

        Returns
        -------
        str
            UUID for the organisation
        """
        id = self._random_uuid(self.rnd)
        org = FakeOrg(id, creation_date)
        org.locale = locale

        org.name = self.faker[locale].company()
        org.url = self._random_url(locale)
        org.contact_email = self._random_email(locale, company=True)
        org.country = locale[3:]
        if self.faker.boolean(chance_of_getting_true=self.parameters["orgs"]["address_chance"]):
            org.address = self.faker[locale].address()
        try:
            if self.faker.boolean(chance_of_getting_true=self.parameters["orgs"]["phone_chance"]):
                org.phone = self.faker[locale].phone_number()
            if self.faker.boolean(chance_of_getting_true=self.parameters["orgs"]["fax_chance"]):
                org.fax = self.faker[locale].phone_number()
        except AttributeError:
            pass

        if make_reporting:
            org.short_name = (org.name[:3].lower() + org.name[-3:].lower()).replace(" ", "")
            org.default_license_id = self.rnd.choices(
                self.default_licenses, weights=self.default_license_weights, k=1
            )[0]
            org.ui_url = self._random_url(locale)
            org.exclusions_url = self._random_url(locale)
            org.iati_id = org_id(locale, self.rnd)
            org.source_type = self.rnd.choices(self.source_types, weights=self.source_type_weights, k=1)[0]
            org.description = self.faker[locale].sentence()
            org.org_type = self.rnd.choices(self.org_types, weights=self.org_type_weights, k=1)[0]
            org.is_reporter = True

        self.orgs[id] = org
        return id

    def generate_fake_dataset(
        self, short_name: str, title: str, creation_date: datetime, reporting_org_id: str, locale: str
    ) -> str:
        """Generate a fake dataset and add to the corpus

        Parameters
        ----------
        short_name : str
            Short name of the dataset
        title : str
            Title of the dataset
        creation_date : datetime
            Creation date for the dataset
        reporting_org_id : str
            UUID for the reporting org
        locale : str
            Locale string

        Returns
        -------
        str
            UUID
        """

        id = self._random_uuid(self.rnd)
        creator_id = self.find_suitable_action_person(reporting_org_id, creation_date)
        dataset = FakeDataset(id, short_name, creation_date, creator_id, reporting_org_id)

        dataset.license_id = self.orgs[reporting_org_id].default_license_id
        dataset.source_type = self.orgs[reporting_org_id].source_type
        dataset.title = title
        dataset.url = self._random_url(locale) + ".xml"
        dataset.visibility = "public"

        self.datasets[id] = dataset
        self.orgs[reporting_org_id].datasets.append(id)
        return id

    def create_multi_org_people(self, num_orgs: int):
        """Creates a number of people who can be editors of multiple organisations

        The number of people is created in proportion to the number of organisations
        in the fake corpus.

        Parameters
        ----------
        num_orgs : int
            Number of organisations.
        """
        num_people = int(math.ceil(num_orgs * self.parameters["users"]["multi_org_users"]))
        for _ in range(num_people):
            id = self.generate_fake_person("editor", self.parameters["start_date"], self._random_locale())
            self.people[id].inactive_date = self.parameters["end_date"]
            self.multi_org_people_ids.append(id)

    def generate(self):
        """Performs a basic generation step of the model

        This method generates an organisation, grows it to its final size,
        accounts for people leaving and joining the organisation, associates
        any change records to the organisation, and adds datasets (org and
        activity files).
        """
        # Is this going to be a a reporting org.
        is_reporting_org = self.faker.boolean(chance_of_getting_true=self.parameters["orgs"]["reporting_org_chance"])

        # Create the bare bones of the organisation.
        org_creation_date = self.faker.date_time_between(self.parameters["start_date"], self.parameters["end_date"])

        # If this is an org with an hq country then we just pick a random locale.  But, instead,
        # if this is a multilaterial with no fixed country then for simplicity we just set this
        # to 489 (South America) and set the locale to es_CO.
        locale = self._random_locale()
        region = ""
        if self.faker.boolean(chance_of_getting_true=self.parameters["orgs"]["multilateral_chance"]):
            locale = "es_CO"
            region = "489"

        admin_person_creation_date = self.faker.date_time_between(
            org_creation_date - timedelta(days=28), org_creation_date
        )
        admin_person_id = self.generate_fake_person("admin", admin_person_creation_date, locale)
        org_id = self.generate_fake_org(org_creation_date, locale, make_reporting=is_reporting_org)
        self.orgs[org_id].region = region
        self.orgs[org_id].grow(admin_person_id, "admin")
        self.org_actions[self._random_uuid(self.rnd)] = FakeOrgAction(
            org_id, admin_person_id, org_creation_date, "Create", self._random_user_agent()
        )
        self.people_org_mapping[admin_person_id].append(org_id)

        # Having created the organisation we now add all the extras - people, datasets, actions
        # if this is a reporting org.
        if is_reporting_org:
            self._grow_organisation_to_final_size(org_id)
            self._create_organisational_churn(org_id)
            self._create_org_change_actions(org_id)
            self._create_dataset_org(org_id)
            self._create_dataset_activity(org_id)

    def _grow_organisation_to_final_size(self, reporting_org_id: str):
        """Grow an organisation by adding people

        Parameters
        ----------
        reporting_org_id : str
            ID of the organisation to grow
        """

        org_creation_date = self.orgs[reporting_org_id].created

        # Grow the organisation - we figure out the timescale and
        # final organisation size, then if the org has more than one
        # person we add all the extra people.
        growth_timescale = self.rnd.uniform(
            self.parameters["orgs"]["growth_timescale_min"], self.parameters["orgs"]["growth_timescale_max"]
        )
        org_final_size = self.rnd.choices(
            self.parameters["orgs"]["by_final_size"]["sizes"],
            weights=self.parameters["orgs"]["by_final_size"]["weights"],
            k=1,
        )[0]
        if org_final_size > 1:
            for this_size in range(2, org_final_size + 1):

                # The creation date comes from an exponential growth model, here
                # we get the number of days since organisation creation to when
                # the person was added to the organisation.
                days_since_org_creation = -math.log(1.0 - ((this_size - 0.5) / org_final_size)) * growth_timescale

                capacity = self.rnd.choices(self.CAPACITY_CHOICES, weights=self.capacity_weights[org_final_size], k=1)[
                    0
                ]

                # If this capacity is an editor then they could potentially be an editor for multiple
                # organisations.  If they are then get an id and add them, rather than creating a new
                # person.
                if capacity == "editor" and self.faker.boolean(
                    chance_of_getting_true=self.parameters["orgs"]["by_final_size"]["multi_org_editor"][
                        org_final_size - 1
                    ]
                ):
                    person_id = self.rnd.choice(self.multi_org_people_ids)
                else:
                    # Create a new person.
                    person_id = self.generate_fake_person(
                        capacity,
                        org_creation_date + timedelta(days_since_org_creation),
                        self.orgs[reporting_org_id].locale,
                    )

                self.orgs[reporting_org_id].grow(person_id, capacity)
                self.people_org_mapping[person_id].append(reporting_org_id)

    def _create_organisational_churn(self, reporting_org_id: str):
        """Account for org leavers/joiners

        All the people have been added to the organisation, now we need
        to figure out if any have left the organisation before the end
        of the corpus time and add replacements.

        Parameters
        ----------
        reporting_org_id : str
            ID of the org to modify.
        """

        # We need to do this iteratively because if someone leaves the organisation and we
        # add a replacement then that replacement may also leave before the end of the model
        # period.
        complete = False
        while not complete:
            complete = True
            for index in range(len(self.orgs[reporting_org_id].people)):
                last_person_id = self.orgs[reporting_org_id].people[index][-1]
                if self.people[last_person_id].inactive_date < self.parameters["end_date"]:
                    # This person has left the organisation so remove the org from the mapping between
                    # the person and the organisations.
                    self.people_org_mapping[last_person_id].remove(reporting_org_id)

                    # Create a replacement person.
                    person_id = self.generate_fake_person(
                        self.people[last_person_id].capacity,
                        self.people[last_person_id].inactive_date,
                        self.orgs[reporting_org_id].locale,
                    )
                    self.orgs[reporting_org_id].people[index].append(person_id)
                    self.people_org_mapping[person_id].append(reporting_org_id)
                    complete = False

    def _create_org_change_actions(self, reporting_org_id: str):
        """Add organisation modification actions to an organisation

        Parameters
        ----------
        reporting_org_id : str
            ID of the reporting org to modify
        """

        num_actions = poisson(
            1.0 / self.parameters["orgs"]["update_period"],
            (self.parameters["end_date"] - self.orgs[reporting_org_id].created).days,
            self.rnd,
        )
        action_dates = uniform_dates(
            num_actions, self.orgs[reporting_org_id].created, self.parameters["end_date"], self.rnd
        )
        for this_date in action_dates:
            action_person_id = self.find_suitable_action_person(reporting_org_id, this_date)
            self.org_actions[self._random_uuid(self.rnd)] = FakeOrgAction(
                reporting_org_id, action_person_id, this_date, "Update", self._random_user_agent()
            )

    def _create_dataset_org(self, reporting_org_id: str):
        """Generate an org file dataset for an organisation

        Parameters
        ----------
        reporting_org_id : str
            UUID of the reporting org.
        """

        # Create an org file for the organisation - if we decide the
        # reporting org has one.
        if self.faker.boolean(chance_of_getting_true=self.parameters["datasets"]["org"]["has_org_file_chance"]):
            dataset_id = self.generate_fake_dataset(
                self.orgs[reporting_org_id].short_name + "-org-file",
                self.orgs[reporting_org_id].name + " Organisation File",
                self.faker.date_time_between(self.orgs[reporting_org_id].created, self.parameters["end_date"]),
                reporting_org_id,
                self.orgs[reporting_org_id].locale,
            )
            self.dataset_actions[self._random_uuid(self.rnd)] = FakeDatasetAction(
                dataset_id,
                reporting_org_id,
                self.datasets[dataset_id].creator_id,
                self.datasets[dataset_id].created,
                "create",
                self._random_user_agent(),
            )

            # Add some changes to the org file.
            self._create_dataset_actions(
                self.datasets[dataset_id].created,
                self.parameters["datasets"]["org"]["update_period"],
                reporting_org_id,
                dataset_id,
                "update_metadata",
            )
            self._create_dataset_actions(
                self.datasets[dataset_id].created,
                self.parameters["actions"]["republish"]["org"]["period"],
                reporting_org_id,
                dataset_id,
                "republish",
            )

    def _create_dataset_activity(self, reporting_org_id: str):
        """Generate all the activity datasets for an organisation

        Parameters
        ----------
        reporting_org_id : str
            UUID for the organisation
        """

        num_datasets = self.rnd.choices(
            self.num_activity_dataset_choices, weights=self.num_activity_dataset_weights, k=1
        )[0]
        if num_datasets == ">1":
            num_datasets = int(
                pareto(
                    self.parameters["datasets"]["activity"]["num_pareto_x_m"],
                    self.parameters["datasets"]["activity"]["num_pareto_alpha"],
                    self.rnd,
                )
            )
        else:
            num_datasets = int(num_datasets)

        dataset_created_dates = uniform_dates(
            num_datasets, self.orgs[reporting_org_id].created, self.parameters["end_date"], self.rnd
        )
        for x in range(num_datasets):
            dataset_id = self.generate_fake_dataset(
                self.orgs[reporting_org_id].short_name + f"-activity-file-{x+1}",
                self.orgs[reporting_org_id].name + f" Activity File {x+1}",
                dataset_created_dates[x],
                reporting_org_id,
                self.orgs[reporting_org_id].locale,
            )

            self.dataset_actions[self._random_uuid(self.rnd)] = FakeDatasetAction(
                dataset_id,
                reporting_org_id,
                self.datasets[dataset_id].creator_id,
                self.datasets[dataset_id].created,
                "create",
                self._random_user_agent(),
            )

            # Add some actions.
            action_ids = self._create_dataset_actions(
                self.datasets[dataset_id].created,
                self.parameters["datasets"]["activity"]["update_period"],
                reporting_org_id,
                dataset_id,
                "update_metadata",
            )
            for action_id in action_ids:
                if self.faker.boolean(
                    chance_of_getting_true=self.parameters["datasets"]["activity"]["url_update_chance"]
                ):
                    self.dataset_actions[action_id].action = "update_url"

            if self.faker.boolean(
                chance_of_getting_true=self.parameters["actions"]["visibility"]["activity"]["chance"]
            ):
                action_ids = self._create_dataset_actions(
                    self.datasets[dataset_id].created,
                    self.parameters["actions"]["visibility"]["activity"]["period"],
                    reporting_org_id,
                    dataset_id,
                    "change_visibility",
                )
                if (len(action_ids) % 2) != 0:
                    self.datasets[dataset_id].visibility = "private"

            self._create_dataset_actions(
                self.datasets[dataset_id].created,
                self.parameters["actions"]["republish"]["activity"]["period"],
                reporting_org_id,
                dataset_id,
                "republish",
            )

    def _create_dataset_actions(
        self, start_date: datetime, period: float, reporting_org_id: str, dataset_id: str, action_type: str
    ) -> List[str]:
        """Create a set of activity dataset actions for a dataset

        This method creates a set of activity dataset actions and adds them
        to the records.

        Parameters
        ----------
        start_date : datetime
            When the dataset was created.
        period : float
            Period over which actions are expected.
        reporting_org_id : str
            Id for the reporting org.
        dataset_id : str
            Id for the dataset.

        Returns
        -------
        List[str]
            List of dataset action UUIDs.
        """
        num_actions = poisson(
            1.0 / period,
            (self.parameters["end_date"] - start_date).days,
            self.rnd,
        )
        action_dates = uniform_dates(num_actions, start_date, self.parameters["end_date"], self.rnd)
        action_ids = []
        for this_date in action_dates:
            action_person_id = self.find_suitable_action_person(reporting_org_id, this_date)
            action_id = self._random_uuid(self.rnd)
            self.dataset_actions[action_id] = FakeDatasetAction(
                dataset_id,
                reporting_org_id,
                action_person_id,
                this_date,
                action_type,
                self._random_user_agent(),
            )
            action_ids.append(action_id)

        return action_ids

    def list_orgs(self):
        """List all the organisations in the corpus."""
        for id in self.orgs:
            print(self.orgs[id])

    def list_people(self):
        """List all the people in the corpus."""
        for id in self.people:
            print(self.people[id])

    def list_datasets(self):
        """List all the datasets in the corpus."""
        for id in self.datasets:
            print(self.datasets[id])

    def list_org_actions(self):
        """List all the organisation actions in the corpus."""
        for action in self.org_actions:
            print(action)

    def list_dataset_actions(self):
        """List all the dataset actions in the corpus."""
        for action in self.dataset_actions:
            print(action)
