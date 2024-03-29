import asyncio
import json
import motor
from beanie import init_beanie

from models import User, Submission
from settings import lru_cache, get_settings, cluster_by_id

'''
This script generates a report for the number of discoverable submissions, funding identifiers and clusters.

Example call:

docker exec dspback python management/submission_report.py
'''

def get_keywords(submission: Submission):
    as_json = json.loads(submission.metadata_json)
    if submission.repo_type.name == "HYDROSHARE":
        return as_json["subjects"]
    if submission.repo_type.name == "ZENODO":
        return as_json["metadata"]["keywords"]
    return as_json["keywords"]

async def initiaize_beanie():
    db = motor.motor_asyncio.AsyncIOMotorClient(get_settings().mongo_url)
    await init_beanie(
        database=db[get_settings().mongo_database], document_models=[User, Submission]
    )
    return db[get_settings().mongo_database]

async def main():
    db = await initiaize_beanie()

    submission_count_by_repository = {}
    test_submission_count_by_repository = {}
    submission_count_by_cluster = {}
    discoverable_documents_count = 0
    table = [["id", "repository", "discoverable", "title", "keywords", "funding", "cluster", "submission_date"]]
    for submission in await Submission.all().to_list():
        discoverable = False
        if "test" == submission.title.lower() or "asdf" in submission.title:
            submission_count = test_submission_count_by_repository.get(str(submission.repo_type), 0)
            test_submission_count_by_repository[str(submission.repo_type)] = submission_count + 1
        else:
            submission_count = submission_count_by_repository.get(str(submission.repo_type), 0)
            submission_count_by_repository[str(submission.repo_type)] = submission_count + 1

        discovery_document = await db["discovery"].find_one({"repository_identifier": submission.identifier})
        funding_identifiers = []
        clusters = []
        if discovery_document:
            discoverable = True
            discoverable_documents_count = discoverable_documents_count + 1
            for cluster in discovery_document.get("clusters", []):
                cluster_count = submission_count_by_cluster.get(cluster, 0)
                submission_count_by_cluster[cluster] = cluster_count + 1
            if "funding" in discovery_document:
                for funding in discovery_document["funding"]:
                    funding_identifier = funding.get("identifier", None)
                    funding_identifiers.append(funding_identifier)
                    for cluster_funding_id, cluster in cluster_by_id.items():
                        if cluster_funding_id in funding_identifier:
                            clusters.append(cluster)
        submission_row = [submission.identifier, submission.repo_type.name, discoverable, submission.title, get_keywords(submission), funding_identifiers, clusters, submission.submitted]
        table.append(submission_row)
    import csv
    with open('/app/output/report.csv', "w") as f:
        filewriter = csv.writer(f)
        for row in table:
            filewriter.writerow(row)






if __name__ == "__main__":
    asyncio.run(main())
