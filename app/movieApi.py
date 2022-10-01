import json
import requests
import traceback
import logging
import os


# This is page access token that you get from facebook developer console.
try:
    MOVIES_API_KEY = os.environ["MOVIES_API_KEY"]

except KeyError:
    logging.error("Can't find all env variables")
    exit


def searchProgram(programType, query):
    params = dict(api_key=MOVIES_API_KEY, language="fr-FR", query=query)
    urlSearch = f"https://api.themoviedb.org/3/search/{programType}"
    logging.info(f"start search for {programType} - {query}")

    try:
        req = requests.get(urlSearch, params)
        req.raise_for_status()
        data = json.loads(req.content)
        logging.info("search OK")
        return data["results"][:9]

    except requests.exceptions.HTTPError as errh:
        logging.info("Http Error:", errh)
        return None, errh


# Function to create program
def getProgramData(tmdb_id, media_type):
    params = dict(api_key=MOVIES_API_KEY, language="fr-FR")
    urlSearch = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"

    logging.info("Getting program data")
    try:
        req = requests.get(urlSearch, params)
        req.raise_for_status()
        data = json.loads(req.content)
        list_genres = [genre["name"] for genre in data["genres"]]

        if media_type == "tv":
            name = data["name"]
            release_date = data["first_air_date"]
            list_networks = [network["name"] for network in data["networks"]]

        elif media_type == "movie":
            name = data["title"]
            release_date = data["release_date"]
            list_networks = [
                production_company["name"]
                for production_company in data["production_companies"]
            ]

        else:
            logging.info("could not get program data")
            return None, False  # Raise an error or write log here

        logging.info("program info got successfully")
        return (
            dict(
                tmdb_id=tmdb_id,
                name=name,
                homepage_link=data["homepage"],
                source=", ".join(list_networks)[0:200],
                synopsis=data["overview"],
                poster_path=data["poster_path"],
                tags=", ".join(list_genres),
                release_date=release_date,
            ),
            True,
        )

    except requests.exceptions.HTTPError as errh:
        logging.error("Http Error:", errh)
        return None, errh
