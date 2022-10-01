import requests
import json
import traceback
import logging
import os
from app.movieApi import getProgramData


try:
    database_id = os.environ["DATABASE_ID"]
    hall_tv_token = os.environ["HALL_TV_TOKEN"]

except KeyError:
    logging.error("Can't find all env variables")
    exit


IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"


def getPages(databaseId, hall_tv_token, query):
    logging.info(f" Start getting page on database")
    url = f"https://api.notion.com/v1/databases/{databaseId}/query"
    headers = buildHeader(hall_tv_token)

    payload = {"page_size": 100}
    payload["filter"] = query

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logging.info(
            f" Sucessfully get pages from database. status code : {response.status_code}"
        )

        return response.json()["results"], True

    except Exception as e:
        logging.error(traceback.format_exc())
        return None


def readDatabase(databaseId, hall_tv_token):
    logging.info(f"Start reading database")
    readurl = f"https://api.notion.com/v1/databases/{databaseId}/query"
    headers = buildHeader(hall_tv_token)

    try:
        res = requests.post(readurl, headers=headers)
        res.raise_for_status()
        data = res.json()
        logging.info(f" Sucessfully read database. status code : {res.status_code}")

        with open("./db.json", "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False)

        return True

    except Exception as e:
        logging.error(traceback.format_exc())
        return False


def createPage(databaseId, hall_tv_token, data):
    logging.info(f"Start page creation")
    createUrl = "https://api.notion.com/v1/pages"
    headers = buildHeader(hall_tv_token)

    newPageData = {
        "parent": {"database_id": databaseId},
        "properties": data["properties"],
        # "icon" : {'type': 'emoji', 'emoji': data["icon"]} if data["icon"] else None
    }

    try:
        res = requests.post(createUrl, headers=headers, data=json.dumps(newPageData))
        res.raise_for_status()
        logging.info(
            f" Sucessfully create page in database. status code : {res.status_code}"
        )

        return json.loads(res.text)["id"]

    except Exception as e:
        logging.error(traceback.format_exc())
        return None


def buildHeader(hall_tv_token):

    return {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {hall_tv_token}",
    }


def updatePage(pageId, hall_tv_token, data):
    logging.info(f"Start page update {pageId}")
    updateUrl = f"https://api.notion.com/v1/pages/{pageId}"
    headers = buildHeader(hall_tv_token)
    updateData = dict()

    if "properties" in data:
        logging.info(f" Update page {pageId}'s properties")
        updateData["properties"] = data["properties"]

    if "icon" in data:
        logging.info(f" Update page {pageId}'s icon")
        updateData["icon"] = data["icon"]

    if "cover" in data:
        logging.info(f" Update page {pageId}'s cover")
        updateData["cover"] = data["cover"]

    if len(updateData.keys()) != 0:
        try:
            res = requests.patch(
                updateUrl, headers=headers, data=json.dumps(updateData)
            )
            logging.info(
                f" page updated successfully in database. status code : {res.status_code}"
            )
            return res

        except Exception as e:
            logging.error(traceback.format_exc())
            return None

    logging.info(f" Any update done on page {pageId}")
    return None


def buildNotionData(tmdbData, programStatus):
    logging.info("Building data for {tmdb_id}".format(tmdb_id=tmdbData["tmdb_id"]))
    properties = {
        "Note sur 5": {"select": {"name": "⭐️⭐️⭐️⭐️⭐️"}},
        "Type": {"select": {"name": "Série TV"}},
        "Éditeur": {"multi_select": [{"name": tmdbData["source"]}]},
        "Statut": {"select": {"name": programStatus}},
        "Nom": {
            "title": [
                {
                    "text": {"content": tmdbData["name"]},
                    "plain_text": tmdbData["name"],
                    "href": tmdbData["homepage_link"],
                }
            ]
        },
        "Tags": {
            "multi_select": [{"name": genre} for genre in tmdbData["tags"].split(", ")]
        },
        "Lien": {"url": tmdbData["homepage_link"]},
        "id": {
            "rich_text": [
                {
                    "text": {"content": tmdbData["tmdb_id"]},
                    "plain_text": tmdbData["tmdb_id"],
                }
            ]
        },
        "Résumé": {
            "rich_text": [
                {
                    "text": {"content": tmdbData["synopsis"]},
                    "plain_text": tmdbData["synopsis"],
                }
            ]
        },
    }

    logging.info("Finish build data")
    return properties


def addProgram(DATABASE_ID, HALL_TV_TOKEN, programId, media_type, programStatus):

    logging.info(f"Adding new serie {programId} in database")
    programData, _ = getProgramData(programId, media_type="tv")
    imageUrl = IMG_BASE_URL + programData["poster_path"]
    notionProperties = buildNotionData(programData, programStatus)
    programData = {
        "properties": notionProperties
        # "icon" : "👅"
    }

    pageId = createPage(DATABASE_ID, HALL_TV_TOKEN, programData)
    if pageId:
        logging.info(f"Updating page {pageId}'s cover")
        updatedData = {"cover": {"type": "external", "external": {"url": imageUrl}}}
        return updatePage(pageId, HALL_TV_TOKEN, updatedData)


def userChoiceHandler(programStatus, DATABASE_ID, HALL_TV_TOKEN, programId, media_type):

    query = {"property": "id", "rich_text": {"equals": programId}}

    logging.info(f"Handling user choice : {programStatus}")
    results, _ = getPages(DATABASE_ID, HALL_TV_TOKEN, query)
    resultsNumber = len(results)
    logging.info(f"Number of results for {programId}: {resultsNumber}")
    if resultsNumber < 1:
        logging.info(f"Creating program {programId} with status {programStatus}")
        return addProgram(
            DATABASE_ID, HALL_TV_TOKEN, programId, media_type, programStatus
        )

    elif resultsNumber == 1:
        logging.info(f"Updating program {programId}'s status to {programStatus}")

        updatedData = {
            "properties": {
                "Statut": {"select": {"name": programStatus}},
            },
        }

        return updatePage(results[0]["id"], HALL_TV_TOKEN, updatedData)

    else:
        logging.error("One page is duplicated")
        return None

    return False
