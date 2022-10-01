from flask import Flask, request
import requests
import json
import traceback
import logging
import os

from app.movieApi import searchProgram, getProgramData
from app.notionApi import userChoiceHandler

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)


# This is page access token that you get from facebook developer console.
try:
    PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
    WEBHOOK_TOKEN = os.environ["WEBHOOK_TOKEN"]
    MOVIES_API_KEY = os.environ["MOVIES_API_KEY"]
    DATABASE_ID = os.environ["DATABASE_ID"]
    HALL_TV_TOKEN = os.environ["HALL_TV_TOKEN"]


except KeyError:
    logging.error("Can't find all env variables")
    exit


# This is API key for facebook messenger.
API = "https://graph.facebook.com/v13.0/me/messages?access_token=" + PAGE_ACCESS_TOKEN
IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"

if __name__ == "__main__":
    app.run()


@app.route("/", methods=["GET"])
def fbverify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get(
        "hub.challenge"
    ):
        if not request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return "Verification token missmatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200


@app.route("/", methods=["POST"])
def fbwebhook():
    data = request.get_json()
    print(data)

    try:
        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    if messaging_event.get("message"):
                        logging.debug("Get message !")
                        return receivedMessage(messaging_event)
                    elif messaging_event.get("postback"):
                        logging.debug("Get postback !")
                        return receivedPostback(messaging_event)
                    else:  # uknown messaging_event
                        logging.error(
                            "Webhook received unknown messaging_event: "
                            + messaging_event
                        )
                        return sendTextMessage(
                            messaging_event["sender"]["id"],
                            "Sorry instruction not understood ",
                        )

        """
        elif postback is not None:
            print("YEAAAH !!!")
            received_postback(data['entry'][0]['messaging'][0])
        """

    except:
        # Here we store the file to our server who send by user from facebook messanger.
        try:
            mess = data["entry"][0]["messaging"][0]["message"]["attachments"][0][
                "payload"
            ]["url"]
            print("for url-->", mess)
            json_path = requests.get(mess)
            filename = mess.split("?")[0].split("/")[-1]
            open(filename, "wb").write(json_path.content)
        except:
            print("Noot Found-->")

    return "ok"


def receivedMessage(event):
    senderId = event["sender"]["id"]
    recipientId = event["recipient"]["id"]

    # could receive text or attachment but not both
    if "text" in event["message"]:
        messageText = event["message"]["text"]

        # TV show search
        if messageText.lower().startswith("tv -"):
            text = messageText.split(" - ")
            programType = text[0]
            query = text[1]

            results = searchProgram(programType, query)
            requestBody = buildTvSearchBody(senderId, results)
            print(requestBody)

            response = requests.post(API, json=requestBody).json()
            print(response.status_code)
            return response

        else:  # default case
            return sendTextMessage(senderId, "Echo: " + messageText)

    elif "attachments" in event["message"]:
        message_attachments = event["message"]["attachments"]
        return sendTextMessage(senderId, "Message with attachment received")


def buildTvSearchBody(senderId, results):

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
                        "payload": "1 - {programId}".format(programId=result["id"]),
                    },
                    {
                        "type": "postback",
                        "title": "En cours",
                        "payload": "2 - {programId}".format(programId=result["id"]),
                    },
                    {
                        "type": "postback",
                        "title": "Terminé",
                        "payload": "3 - {programId}".format(programId=result["id"]),
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


def callSendApi(messageData):
    """
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    """
    recipientId = messageData["recipient"]["id"]

    try:
        # req = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=messageData)
        response = requests.post(API, json=messageData).json()
        response.raise_for_status()
        logging.info(
            f"Message successfully sent to {recipientId}. status code : {response.status_code}"
        )
        return response

    except Exception as e:
        logging.error(
            f"Failled to send message to {recipientId}. status code : {response.status_code}"
        )
        logging.error(traceback.format_exc())
        return None


def sendTextMessage(recipientId, messageText):
    logging.info(
        "sending message to {recipient}: {text}".format(
            recipient=recipientId, text=messageText.encode("utf-8")
        )
    )
    messageData = {"recipient": {"id": recipientId}, "message": {"text": messageText}}

    return callSendApi(messageData)


def receivedPostback(event):
    sender_id = event["sender"]["id"]
    recipient_id = event["recipient"]["id"]
    payload = event["postback"]["payload"]
    programId = payload.split(" - ")[1]
    programStatus = ""

    logging.info(
        "received postback from {recipient} with payload {payload}".format(
            recipient=recipient_id, payload=payload
        )
    )

    if payload.startswith("1 -"):
        programStatus = "A voir"
    elif payload.startswith("2 -"):
        programStatus = "En cours"
    elif payload.startswith("3 -"):
        programStatus = "Terminé"

    if userChoiceHandler(programStatus, DATABASE_ID, HALL_TV_TOKEN, programId, "tv"):
        return sendTextMessage(
            sender_id,
            f" 5 sur 5 ! Tu peux retrouver ton programe {programStatus} dans Notion !",
        )

    return sendTextMessage(
        sender_id,
        "Désolé, une erreur s'est produite, l'action n'a pas été prise en compte",
    )
