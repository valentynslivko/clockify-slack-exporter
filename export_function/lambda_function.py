import json
import arrow
import urllib.parse

from slack_api import MY_ID, bot_client


def lambda_handler(event, context):
    # request_body = await request.body()
    print("lambda event data: ", event["body"])

    try:
        # Parse the URL-encoded body
        body = urllib.parse.parse_qs(event["body"])
        metadata_map = {
            item.split("=")[0]: item.split("=")[1]
            for item in urllib.parse.parse_qs(body).decode().split("&")
        }
        error_resp = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "You are not allowed to use this app. Contact @Valentyn Slivko for sauce code to adjust for your needs",  # noqa
                        "emoji": True,
                    },
                }
            ]
        }

        if metadata_map["user_id"] != MY_ID:
            bot_client.chat_postMessage(
                channel=metadata_map["channel_id"], **error_resp
            )
            return {"statusCode": 403, "body": json.dumps("Forbidden")}

        datepicker_element = {
            "blocks": [
                {
                    "type": "input",
                    "element": {
                        "type": "datepicker",
                        "initial_date": arrow.utcnow().format("YYYY-MM-DD"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True,
                        },
                        "action_id": "datepicker-action",
                    },
                    "label": {"type": "plain_text", "text": "Date to", "emoji": True},
                },
                {
                    "type": "input",
                    "element": {
                        "type": "datepicker",
                        "initial_date": arrow.now(tz="Europe/Kiev")
                        .replace(day=1)
                        .format("YYYY-MM-DD"),  # beginning of the month
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True,
                        },
                        "action_id": "datepicker-action",
                    },
                    "label": {"type": "plain_text", "text": "Date from", "emoji": True},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Select customer",
                    },
                    "accessory": {
                        "type": "static_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select project",
                            "emoji": True,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Stefan",
                                    "emoji": True,
                                },
                                "value": "Stefan",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "Filip and Pavel",
                                    "emoji": True,
                                },
                                "value": "Filip and Pavel",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "TraverseAI",
                                    "emoji": True,
                                },
                                "value": "traverse",
                            },
                        ],
                        "action_id": "static_select-action",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Submit dates",
                                "emoji": True,
                            },
                            "value": "submit_dates",
                            "action_id": "submit",
                        }
                    ],
                },
            ]
        }
        bot_client.chat_postMessage(
            channel=metadata_map["channel_id"], **datepicker_element
        )
        return {"statusCode": 200, "body": json.dumps("good")}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}
