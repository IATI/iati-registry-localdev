"""Classes that contain records in the corpus"""

import random
from datetime import datetime, timedelta


class FakeOrgAction:
    def __init__(self, reporting_org_id: str, person_id: str, created: datetime, action: str, user_agent: str):
        """Create a new organisation action

        Parameters
        ----------
        reporting_org_id : str
            ID of the reporting org that the action is about.
        person_id : str
            ID of the person that made the change.
        created : datetime
            When the action happened.
        action : str
            What action was carried out.
        user_agent : str
            What tool made the change.
        """
        self.reporting_org_id = reporting_org_id
        self.person_id = person_id
        self.created = created
        self.action = action
        self.user_agent = user_agent

    def __str__(self):
        return (
            f"OrgAction: created={self.created} person={self.person_id} "
            f"action={self.action} org={self.reporting_org_id} using={self.user_agent}"
        )


class FakeDatasetAction:
    def __init__(
        self, dataset_id: str, reporting_org_id: str, person_id: str, created: datetime, action: str, user_agent: str
    ):
        """Create a new dataset action

        Parameters
        ----------
        dataset_id : str
            ID of the dataset that the action is about.
        reporting_org_id : str
            ID of the reporting org that owns the dataset that the action is about.
        person_id : str
            ID of the person that made the change.
        created : datetime
            When the action happened.
        action : str
            What action was carried out.
        user_agent : str
            What tool made the change.
        """
        self.dataset_id = dataset_id
        self.reporting_org_id = reporting_org_id
        self.person_id = person_id
        self.created = created
        self.action = action
        self.user_agent = user_agent

    def __str__(self):
        return (
            f"DatasetAction: created={self.created} person={self.person_id} "
            f"action={self.action} dataset={self.dataset_id} org={self.reporting_org_id} using={self.user_agent}"
        )


class FakeOrg:
    def __init__(self, id: str, created: datetime):
        """Create a basic organisation

        Parameters
        ----------
        id : str
            ID for the organisation.
        created : datetime
            Creation date of the organisation.
        """
        self.id = id
        self.created = created
        self.people = []
        self.people_capacity = []
        self.datasets = []
        self.name = ""
        self.short_name = ""
        self.default_license_id = ""
        self.ui_url = ""
        self.url = ""
        self.org_type = ""
        self.exclusions_url = ""
        self.iati_id = ""
        self.contact_email = ""
        self.source_type = ""
        self.country = ""
        self.address = ""
        self.phone = ""
        self.fax = ""
        self.description = ""
        self.is_reporter = False
        self.locale = ""

    def __str__(self):
        return (
            f"Org <{self.id}>: created={self.created} "
            f"num_people={len(self.people)}  num_datasets={len(self.datasets)}"
        )

    def grow(self, person_id: str, capacity: str):
        """Grow the organisation by adding a person

        Parameters
        ----------
        person_id : str
            ID of the person to add.
        capacity : str
            Their capacity (admin, editor, member).
        """
        self.people.append([person_id])
        self.people_capacity.append(capacity)


class FakePerson:
    def __init__(self, id: str, created: datetime, capacity: str, leaving_waiting_time: float):
        """Create a person

        Parameters
        ----------
        id : str
            ID of the person to create
        created : datetime
            When the person was created
        capacity : str
            Their capacity (admin, editor, member).
        leaving_waiting_time : float
            Roughly how long (in days) we expect them to stay at the organisation.
        """
        self.id = id
        self.created = created
        self.capacity = capacity
        self.leaving_waiting_time = leaving_waiting_time
        self.inactive_date = None

        self.short_user_name = ""
        self.name = ""
        self.email = ""
        self.mailing_list = False

        self.in_person_name = ""
        self.online_name = ""
        self.preferred_language = ""
        self.country = ""
        self.country_code = ""
        self.locale = ""
        self.time_zone = ""
        self.first_registration_use_cases = []

    def __str__(self):
        return (
            f"Person <{self.id}>: capacity={self.capacity} created={self.created} inactive_date={self.inactive_date}"
        )

    def set_inactive_date(self, rnd: random.Random):
        """Randomly select the date that they leave their organisation

        Parameters
        ----------
        rnd : random.Random
            Random number generator to use in working out the date.
        """
        self.inactive_date = self.created + timedelta(days=rnd.expovariate(1.0 / self.leaving_waiting_time))


class FakeDataset:
    def __init__(self, id: str, short_name: str, created: datetime, creator_id: str, reporting_org_id: str):
        """Create a dataset

        Parameters
        ----------
        id : str
            ID of the dataset to create.
        short_name : str
            Short name of the dataset.
        created : datetime
            Creation date of the dataset.
        creator_id : str
            ID of the person who created it.
        reporting_org_id : str
            ID of the reporting org that owns the dataset.
        """
        self.id = id
        self.short_name = short_name
        self.created = created
        self.creator_id = creator_id
        self.reporting_org_id = reporting_org_id

        self.license_id = ""
        self.source_type = ""
        self.title = ""
        self.url = ""

    def __str__(self):
        return (
            f"Dataset <{self.id}> short_name={self.short_name}: created={self.created} "
            f"creator={self.creator_id} reporting_org={self.reporting_org_id}"
        )
