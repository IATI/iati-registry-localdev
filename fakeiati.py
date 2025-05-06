"""Tool to generate a fake IATI corpus for development and testing purposes"""

import argparse
import csv
import json

from iati_faker_model import FakeCorpus
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(
        prog="FakeIATI",
        description="Generate a fake corpus of IATI data for development and testing",
        formatter_class=argparse.MetavarTypeHelpFormatter,
    )
    parser.add_argument("-n", default=100, type=int, dest="num_orgs", help="Number of organisation to generate")
    parser.add_argument("-s", default=8192, type=int, dest="seed", help="Seed for the random number generator")
    parser.add_argument(
        "--no-suitecrm",
        default=False,
        type=bool,
        dest="no_suitecrm",
        help="Don't generate CSV files for bulk import into SuiteCRM",
    )
    parser.add_argument(
        "--no-wso2",
        default=False,
        type=bool,
        dest="no_wso2",
        help="Don't generate JSON files for import into WSO2",
    )
    parser.add_argument(
        "-p",
        dest="params_filename",
        default="fake-model-parameters.toml",
        type=str,
        help="Filename of a model parameter TOML file",
    )
    parser.add_argument("--safe-emails", default=True, type=bool, help="Generate safe email addresses")
    parser.add_argument("--safe-urls", default=True, type=bool, help="Generate safe urls")
    parser.add_argument("--fake-uuids", default=False, type=bool, help="Generate clearly fake UUIDs for records")
    args = parser.parse_args()

    print("Setting up faker and parsing model parameter file")
    corpus = FakeCorpus(
        args.params_filename,
        seed=args.seed,
        safe_emails=args.safe_emails,
        safe_urls=args.safe_urls,
        fake_uuids=args.fake_uuids,
    )

    print("Generating multi-organisation people... ", end="")
    corpus.create_multi_org_people(args.num_orgs)
    print("done")

    for _ in tqdm(range(args.num_orgs), desc="Generating organisations"):
        corpus.generate()

    if not args.no_suitecrm:
        print("Generating CSV files for SuiteCRM... ", end="")
        generate_csv_suitecrm(corpus)
        print("done.")

    if not args.no_wso2:
        print("Generating JSON file for WSO2... ", end="")
        generate_identity_migration(corpus)
        print("done.")


def generate_csv_suitecrm(corpus):
    with open("suitecrm_orgs.csv", "w") as fh:
        field_names = [
            "ID",
            "Name",
            "Website",
            "Description",
            "Date Created",
            "Short Name",
            "Data Portal URL",
            "Reporting Source Type",
            "HQ Country",
            "Default Publishing Licence",
            "IATI Organisation Type",
            "IATI Identifier",
            "Address",
            "Exclusions Policy URL",
            "Email Address",
            "Office Phone",
            "Fax",
            "Approved to publish",
            "First Publishing Date",
            "Region",
        ]
        writer = csv.DictWriter(fh, field_names)
        writer.writeheader()
        for id in corpus.orgs:
            org = corpus.orgs[id]
            first_publish_date = (
                min([corpus.datasets[x].created for x in org.datasets]).strftime("%Y-%m-%d %H:%M:%S")
                if len(org.datasets) > 0
                else ""
            )
            data = {
                "ID": id,
                "Name": org.name,
                "Website": org.url,
                "Description": org.description,
                "Date Created": org.created.strftime("%Y-%m-%d %H:%M:%S"),
                "Short Name": org.short_name,
                "Data Portal URL": org.ui_url,
                "Reporting Source Type": org.source_type,
                "HQ Country": org.country if org.region == "" else "",
                "Default Publishing Licence": org.default_license_id,
                "IATI Organisation Type": org.org_type,
                "IATI Identifier": org.iati_id,
                "Address": org.address,
                "Exclusions Policy URL": org.exclusions_url,
                "Email Address": org.contact_email,
                "Office Phone": org.phone,
                "Fax": org.fax,
                "Approved to publish": "1" if org.is_reporter else "0",
                "First Publishing Date": first_publish_date,
                "Region": org.region,
            }

            writer.writerow(data)

    with open("suitecrm_people.csv", "w") as fh:
        field_names = [
            "ID",
            "Last Name",
            "Email Address",
            "Date Created",
            "In-Person Name",
            "Preferred Language",
            "Country",
            "Online Name",
            "Mailing List Subscriber",
            "Organisation ID",
        ]
        writer = csv.DictWriter(fh, field_names)
        writer.writeheader()
        for id in corpus.people:
            person = corpus.people[id]
            person_org_id = corpus.people_org_mapping[id][0] if len(corpus.people_org_mapping[id]) > 0 else ""
            data = {
                "ID": id,
                "Last Name": person.name,
                "Email Address": person.email,
                "Date Created": person.created.strftime("%Y-%m-%d %H:%M:%S"),
                "In-Person Name": person.in_person_name,
                "Preferred Language": person.preferred_language,
                "Country": person.country_code,
                "Online Name": person.online_name,
                "Mailing List Subscriber": 1 if person.mailing_list else 0,
                "Organisation ID": person_org_id,
            }
            writer.writerow(data)

    with open("suitecrm_datasets.csv", "w") as fh:
        field_names = [
            "ID",
            "Name",
            "Date Created",
            "Licence ID for the dataset",
            "URL Update Date",
            "Metadata Update Date",
            "Short name for the dataset",
            "Source type",
            "Dataset URL",
            "Organisation ID",
            "People ID",
            "Visibility",
        ]
        writer = csv.DictWriter(fh, field_names)
        writer.writeheader()
        for id in corpus.datasets:
            dataset = corpus.datasets[id]
            data = {
                "ID": id,
                "Name": dataset.title,
                "Date Created": dataset.created.strftime("%Y-%m-%d %H:%M:%S"),
                "Licence ID for the dataset": dataset.license_id,
                "URL Update Date": "",
                "Metadata Update Date": "",
                "Short name for the dataset": dataset.short_name,
                "Source type": dataset.source_type,
                "Dataset URL": dataset.url,
                "Organisation ID": dataset.reporting_org_id,
                "People ID": dataset.creator_id,
                "Visibility": dataset.visibility,
            }
            writer.writerow(data)

    with open("suitecrm_org_actions.csv", "w") as fh:
        field_names = [
            "ID",
            "Date Created",
            "Action Type",
            "User Application",
            "Changed By Id",
            "Changed Organisation Id",
        ]
        writer = csv.DictWriter(fh, field_names)
        writer.writeheader()
        for id in corpus.org_actions:
            action = corpus.org_actions[id]
            data = {
                "ID": id,
                "Date Created": action.created.strftime("%Y-%m-%d %H:%M:%S"),
                "Action Type": action.action,
                "User Application": action.user_agent,
                "Changed By Id": action.person_id,
                "Changed Organisation Id": action.reporting_org_id,
            }
            writer.writerow(data)

    with open("suitecrm_dataset_actions.csv", "w") as fh:
        field_names = [
            "ID",
            "Date Created",
            "Action Type",
            "User Application",
            "Action Performed By Id",
            "Dataset Changed Id",
        ]
        writer = csv.DictWriter(fh, field_names)
        writer.writeheader()
        for id in corpus.dataset_actions:
            action = corpus.dataset_actions[id]
            data = {
                "ID": id,
                "Date Created": action.created.strftime("%Y-%m-%d %H:%M:%S"),
                "Action Type": action.action,
                "User Application": action.user_agent,
                "Action Performed By Id": action.person_id,
                "Dataset Changed Id": action.dataset_id,
            }
            writer.writerow(data)


def generate_identity_migration(corpus):
    data = []
    for id in corpus.people:
        person = corpus.people[id]
        created = person.created.strftime("%Y-%m-%d %H:%M:%S")
        data.append(
            {
                "fullName": person.name,
                "email": person.email,
                "created": created,
                "crmId": id,
                "locale": person.locale,
                "country": person.country,
                "timeZone": person.time_zone,
                "userType": "reporter" if len(corpus.people_org_mapping[id]) > 0 else "standard",
                "inPersonName": person.in_person_name,
                "onlineName": person.online_name,
                "mailingList": person.mailing_list,
                "preferredLanguage": person.preferred_language,
                "registrationUseCases": person.first_registration_use_cases,
            }
        )
    with open("wso2_users.json", "w") as fh:
        json.dump(data, fh, indent=4)


if __name__ == "__main__":
    main()
