from flask import Flask, request
import requests
import json
import traceback
import logging
import os
import re

from app.notionApi import userChoiceHandler
from app.middleware import handleTextMessages


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
MESGENGER_API = (
    "https://graph.facebook.com/v13.0/me/messages?access_token=" + PAGE_ACCESS_TOKEN
)

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
        return handleTextMessages(event["message"]["text"], senderId, MESGENGER_API, sendTextMessage)

    elif "attachments" in event["message"]:
        message_attachments = event["message"]["attachments"]
        return sendTextMessage(senderId, "Message with attachment received")


def callSendApi(messageData):
    recipientId = messageData["recipient"]["id"]

    try:
        # req = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=messageData)
        response = requests.post(MESGENGER_API, json=messageData).json()
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
    programType = payload.split(" - ")[1]
    programId = payload.split(" - ")[2]

    logging.info(
        "received postback from {recipient} with payload {payload}".format(
            recipient=recipient_id, payload=payload
        )
    )

    if payload.startswith("1 -"):
        programStatus = "A voir"
    elif payload.startswith("2 -"):
        programStatus = "En cours"
    else:
        programStatus = "Terminé"

    if userChoiceHandler(
        programStatus, DATABASE_ID, HALL_TV_TOKEN, programId, programType
    ):
        return sendTextMessage(
            sender_id,
            f" 5 sur 5 ! Tu peux retrouver ton programe {programStatus} dans Notion !",
        )

    return sendTextMessage(
        sender_id,
        "Désolé, une erreur s'est produite, l'action n'a pas été prise en compte",
    )
