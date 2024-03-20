import functools
import json
import requests
import enum
import pandas
import concurrent.futures
import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from dsp_reports.config import get_settings

router = APIRouter()

db = AsyncIOMotorClient(get_settings().mongo_url)

class AccessState(enum.Enum):
    PUBLIC = enum.auto()
    DISCOVERABLE = enum.auto()
    PUBLISHED = enum.auto()
    UNKNOWN = enum.auto()


def build_sysmeta_url(record: json):
    # "identifier": "http://www.hydroshare.org/resource/8160fe8ea17d46d783b521ab231236b5",
    #print(json.dumps(record, indent=2, default=str))
    identifier = record["url"].split("/")[-1].strip("hs.") # 8160fe8ea17d46d783b521ab231236b5    
    return f"https://www.hydroshare.org/hsapi/resource/{identifier}/sysmeta/"


def determine_access(sys_meta):
    if sys_meta["published"]:
        return AccessState.PUBLISHED
    if sys_meta["public"]:
        return AccessState.PUBLIC
    if sys_meta["discoverable"]:
        return AccessState.DISCOVERABLE


def load_url(url):
    return requests.get(url, timeout = 10)

def retrieve_access(urls):
    access_by_url = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_url = {executor.submit(load_url, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print("Erorr retrieving " + url)
                access_by_url[url] = AccessState.UNKNOWN.name
                data = None
            if data:
                access_state = determine_access(data.json())
                access_by_url[url] = access_state.name

    return access_by_url


async def build_report(request: Request):
    project = [
        {
            '$project': {
                'name': 1,
                'description': 1,
                'keywords': 1,
                'datePublished': 1,
                'dateCreated': 1,
                'provider': 1,
                'funding': 1,
                'clusters': 1,
                'url': 1,
                'legacy': 1,
                '_id': 0,
            }
        }
    ]

    json_response = await db[get_settings().mongo_database]["discovery"].aggregate(project).to_list(None)

    urls = []
    for row in json_response:
        row['provider'] = row['provider']['name']
        if 'funding' in row:
            funding_ids = []
            for funding in row['funding']:
                if 'identifier' in funding:
                    funding_ids.append(funding['identifier'])
            row['funding'] = funding_ids

        if row["provider"] == "HydroShare":
            '''
            We have to get the sysmeta from hydroshare to deteremine access, collecting urls to async grab and parse later
            '''
            urls.append(build_sysmeta_url(row))
        if row["provider"] == "EarthChem Library":
            '''
            This was my best guess for the earthchem states
            '''
            now = datetime.datetime.now()
            if row["datePublished"] > now:
                row["access"] = AccessState.DISCOVERABLE.name
            else:
                row["access"] = AccessState.PUBLISHED.name
        if row["provider"] == "Zenodo":
            '''
            * open: Open Access
            * embargoed: Embargoed Access
            * restricted: Restricted Access
            * closed: Closed Access

            I'm not completely sure the matching here is correct but I'm not too worried about it with only 1 zenodo submission
            '''
            document = await db[get_settings().mongo_database]["Submission"].find_one({"identifier": row["repository_identifier"]})
            access_right = document["metadata"]["access_right"]
            if access_right == "embargoed":
                row["access"] = AccessState.DISCOVERABLE.name
            elif access_right == "restricted":
                row["access"] = AccessState.DISCOVERABLE.name
            elif "doi" in row and row["doi"]:
                row["access"] = AccessState.PUBLISHED.name
            else:
                row["access"] = AccessState.PUBLIC.name
    
    access_by_url = retrieve_access(urls)
    for row in json_response:
        if row["provider"] == "HydroShare":
            try:
                row["access"] = access_by_url[build_sysmeta_url(row)]
            except Exception:
                row["access"] = AccessState.UNKNOWN.name
    return json_response


@router.get("/json")
async def report_json(request: Request):
    return await build_report(request)


@router.get("/csv")
async def csv(request: Request):
    json_response = await build_report(request)
    df = pandas.read_json(json.dumps(json_response, default=str))
    filename = "discover_report.csv"
    df.to_csv(filename)
    return FileResponse(filename, filename=filename, media_type='application/octet-stream')


def compare(c1: str, c2: str):
    if c1.startswith("CZO"):
        if c2.startswith("CZO"):
            return c1 < c2
        else:
            return 1
    if c2.startswith("CZO"):
        return -1
    return c1 < c2


@router.get("/clusters")
async def clusters(request: Request) -> list[str]:
    existing_clusters = await request.app.db[get_settings().mongo_database]["discovery"].find().distinct('clusters')
    return sorted(existing_clusters, key=functools.cmp_to_key(compare))
