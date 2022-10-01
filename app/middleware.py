import re
import logging
import requests
from app.movieApi import searchProgram, getProgramData
from app.main import sendTextMessage


def handleTextMessages(messageText, senderId, MESGENGER_API):
    pattern = re.compile(r"[a-zA-Z]+ - ", re.IGNORECASE)

    if pattern.match(messageText):
        text = messageText.split(" - ")
        programType = text[0]
        query = text[1]

        if programType in ["tv", "movie"]:
            return handleTvMoviesRequests(senderId, programType, query, MESGENGER_API)
        else:
            return sendTextMessage(senderId, "Echo: " + messageText)

    else:
        return sendTextMessage(senderId, "Echo: " + messageText)

    return True


def handleTvMoviesRequests(senderId, programType, query, MESGENGER_API):
    requestBody = buildSearchBody(
        senderId, programType, searchProgram(programType, query)
    )
    response = requests.post(MESGENGER_API, json=requestBody).json()
    logging.info(response.status_code)

    return response


def buildSearchBody(senderId, results, programType):
    IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"

    elements = [
        dict(
            {
                "title": result["name"],
                "image_url": IMG_BASE_URL + result["poster_path"],
                "subtitle": result["original_name"],
                "default_action": {
                    "type": "web_url",
                    "url": "https://www.originalcoastclothing.com/",
                    "webview_height_ratio": "tall",
                },
                "buttons": [
                    {
                        "type": "postback",
                        "title": "A voir",
                        "payload": "1 - {programType} - {programId}".format(
                            programType=programType, programId=result["id"]
                        ),
                    },
                    {
                        "type": "postback",
                        "title": "En cours",
                        "payload": "2 - {programType} - {programId}".format(
                            programType=programType, programId=result["id"]
                        ),
                    },
                    {
                        "type": "postback",
                        "title": "Terminé",
                        "payload": "3 - {programType} - {programId}".format(
                            programType=programType, programId=result["id"]
                        ),
                    },
                ],
            }
        )
        for result in results
        if result["poster_path"] != None
    ]

    requestBody = {
        "recipient": {"id": senderId},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements,
                },
            }
        },
    }

    return requestBody
