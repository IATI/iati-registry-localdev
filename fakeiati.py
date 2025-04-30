"""Tool to generate a fake IATI corpus for development and testing purposes"""

import argparse

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

    print("Setting up faker and parsing model parameter file... ", end="")
    corpus = FakeCorpus(
        args.params_filename,
        seed=args.seed,
        safe_emails=args.safe_emails,
        safe_urls=args.safe_urls,
        fake_uuids=args.fake_uuids,
    )
    print("done")

    print("Generating multi-organisation people... ", end="")
    corpus.create_multi_org_people(args.num_orgs)
    print("done")

    for _ in tqdm(range(args.num_orgs), desc="Generating organisations"):
        corpus.generate()

    if not args.no_suitecrm:
        print("Generating CSV files for SuiteCRM... ", end="")
        generate_csv_suitecrm(corpus)
        print("done.")


def generate_csv_suitecrm(corpus):
    with open("suitecrm_orgs.csv", "w") as fh:
        fh.write(
            '"Name","ID","Website","Description","Date Created","Short Name","Data Portal URL",'
            '"Reporting Source Type","HQ Country","Default Publishing Licence","IATI Organisation Type",'
            '"IATI Identifier","Address","Exclusions Policy URL","Email Address",'
            '"Office Phone","Fax","Approved to publish"\n'
        )
        for id in corpus.orgs:
            org = corpus.orgs[id]
            created = org.created.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f'"{org.name}",{id},{org.url},"{org.description}",{created},{org.short_name},{org.ui_url},')
            fh.write(f'"{org.source_type}","{org.country}","{org.default_license_id}","{org.org_type}",')
            fh.write(f'{org.iati_id},"{org.address}",{org.exclusions_url},{org.contact_email},')
            fh.write(f'{org.phone},{org.fax},{"1" if org.is_reporter else "0"}\n')

    with open("suitecrm_people.csv", "w") as fh:
        fh.write(
            '"Last Name","ID","Email Address","Date Created","In-Person Name",'
            '"Preferred Language","Country","Online Name","Mailing List Subscriber","Organisation ID"\n'
        )
        for id in corpus.people:
            person = corpus.people[id]
            person_org_id = ""
            created = person.created.strftime("%Y-%m-%d %H:%M:%S")
            if len(corpus.people_org_mapping[id]) > 0:
                person_org_id = corpus.people_org_mapping[id][0]
            fh.write(f'"{person.name}",{id},{person.email},{created},')
            fh.write(f'"{person.in_person_name}",{person.preferred_language},')
            fh.write(f"{person.country_code},{person.online_name},")
            fh.write(f'"{1 if person.mailing_list else 0}", {person_org_id}\n')

    with open("suitecrm_datasets.csv", "w") as fh:
        fh.write(
            '"Name","ID","Date Created","Licence ID for the dataset","URL Update Date","Metadata Update Date",'
            '"Short name for the dataset","Source type","Dataset URL","Organisation ID","People ID"\n'
        )
        for id in corpus.datasets:
            dataset = corpus.datasets[id]
            created = dataset.created.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f'"{dataset.title}",{id},')
            fh.write(f'{created},{dataset.license_id},"","",')
            fh.write(f'"{dataset.short_name}",{dataset.source_type},{dataset.url},')
            fh.write(f"{dataset.reporting_org_id},{dataset.creator_id}\n")

    with open("suitecrm_org_actions.csv", "w") as fh:
        fh.write('"ID","Date Created","Action Type","User Application","Changed By Id","Changed Organisation Id"\n')
        for id in corpus.org_actions:
            action = corpus.org_actions[id]
            created = action.created.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(
                f'{id},{action.created},"{action.action}","{action.user_agent}",'
                f"{action.person_id},{action.reporting_org_id}\n"
            )

    with open("suitecrm_dataset_actions.csv", "w") as fh:
        fh.write('"ID","Date Created","Action Type","User Application","Action Performed By Id","Dataset Changed Id"\n')
        for id in corpus.dataset_actions:
            action = corpus.dataset_actions[id]
            created = action.created.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(
                f'{id},{action.created},"{action.action}","{action.user_agent}",'
                f"{action.person_id},{action.dataset_id}\n"
            )


if __name__ == "__main__":
    main()
