import json
import urllib.parse

import arrow
import uvicorn
from clockify_api import ClientName, SlackProjectName
from fastapi import FastAPI, Request, status
from slack_api import MY_ID, SlackManager, bot_client

app = FastAPI()


@app.post("/export", status_code=status.HTTP_200_OK)
async def handle_slack(request: Request):
    request_body = await request.body()
    print(request_body)
    metadata_map = {
        item.split("=")[0]: item.split("=")[1]
        for item in request_body.decode().split("&")
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
        bot_client.chat_postMessage(channel=metadata_map["channel_id"], **error_resp)
        return

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
    return


@app.post("/interactivity", status_code=status.HTTP_200_OK)
async def handle_interactivity(request: Request):
    request_body = await request.body()
    # print(request_body)
    url_decoded_body = urllib.parse.unquote(request_body)
    json_body = json.loads(url_decoded_body.replace("payload=", ""))
    with open("slack_interactive.json", "w+") as f:
        f.write(json.dumps(json_body, indent=4))
    channel_id = json_body["channel"]["id"]
    state: dict[dict] = json_body["state"]
    selected_dates_list = list(state["values"].values())
    selected_dates_by_user = {
        "from": selected_dates_list[0]["datepicker-action"]["selected_date"],
        "to": selected_dates_list[1]["datepicker-action"]["selected_date"],
    }
    try:
        selected_project: str = selected_dates_list[-1]["static_select-action"][
            "selected_option"
        ]["value"]
    except TypeError:
        bot_client.chat_postMessage(
            channel=channel_id, text="*Error: You must select the customer/project*"
        )
        return

    if selected_dates_by_user["from"] < selected_dates_by_user["to"]:
        bot_client.chat_postMessage(
            channel=channel_id,
            text="'Date to' value cannot be in future from 'Date from'",
        )

    if not selected_dates_by_user["from"] or not selected_dates_by_user["to"]:
        return
    if json_body["actions"][0].get("action_id") == "submit":
        slack = SlackManager(
            selected_dates_by_user["to"], selected_dates_by_user["from"]
        )
        if selected_project == "Stefan":
            slack.submit_to_clockify(ClientName.stefan, slack_channel_id=channel_id)

        if selected_project.replace("+", " ") == "Fillip and Pavel":
            slack.submit_to_clockify(ClientName.fillip, slack_channel_id=channel_id)

        if selected_project == "traverse":
            slack.submit_to_clockify(
                SlackProjectName.traverse, slack_channel_id=channel_id
            )

    return


if __name__ == "__main__":
    uvicorn.run("app:app", port=8989, reload=True)
