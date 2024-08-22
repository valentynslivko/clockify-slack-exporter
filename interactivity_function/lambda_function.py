import urllib.parse
import json
from slack_api import bot_client, SlackManager
from clockify_api import ClientName, SlackProjectName


def lambda_handler(event, context):
    # print(request_body)
    print(event)
    url_decoded_body = urllib.parse.unquote(event)
    json_body = json.loads(url_decoded_body.replace("payload=", ""))
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

    return {"statusCode": 200, "body": json.dumps("good")}
