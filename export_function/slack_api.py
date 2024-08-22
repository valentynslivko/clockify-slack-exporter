import json
import logging
import os
import re
from datetime import datetime
from typing import Union

import arrow
from clockify_api import (
    ZEN_WORKSPACE_ID,
    ClientName,
    ClockifyManager,
    ClockifyTimeEntry,
    SlackProjectName,
    ClockifyProjectName,
)
from dotenv import load_dotenv
from slack_sdk import WebClient

logging.basicConfig(level=logging.INFO)

load_dotenv()

SPARKASSE_CHANNEL_ID = os.environ["SPARKASSE_CHANNEL_ID"]
PAVEL_CHANNEL_ID = os.environ["PAVEL_CHANNEL_ID"]
TRAVERSE_CHANNEL_ID = os.environ["TRAVERSE_CHANNEL_ID"]
MY_ID = os.environ["MY_SLACK_ID"]

slack_client = WebClient(token=os.environ.get("SLACK_OAUTH_TOKEN"))
bot_client = WebClient(os.environ["SLACK_BOT_TOKEN"])


def json_encoder(obj, redis_ts=None):
    if isinstance(obj, arrow.Arrow):
        return obj.for_json().format()
    if isinstance(obj, datetime):
        return arrow.get(obj).for_json().format()
    if isinstance(redis_ts, arrow.Arrow):
        return redis_ts.for_json().format()
    if isinstance(redis_ts, datetime):
        return arrow.get(redis_ts).for_json().format()


class SlackManager:
    def __init__(self, oldest_msg_ts: str, latest_msg_ts: str) -> None:
        json.JSONEncoder.default = json_encoder
        self.oldest_msg_ts = oldest_msg_ts
        self.latest_msg_ts = latest_msg_ts
        self.clockify = ClockifyManager()

    def get_all_messages_by_me_from_slack_channel(
        self, channel_id: str, slack_channel_id: str
    ):
        oldest_msg = arrow.get(self.oldest_msg_ts).timestamp()
        latest_msg = arrow.get(self.latest_msg_ts).timestamp()
        response = slack_client.conversations_history(
            channel=channel_id, limit=999, oldest=oldest_msg, latest=latest_msg
        ).data
        if not response["messages"]:
            bot_client.chat_postMessage(
                channel=slack_channel_id,
                text="No messages were found in the current interval",
            )
        chat_messages = response["messages"]
        my_msgs = []
        for message in chat_messages:
            user_id = message["user"]
            if user_id == MY_ID:
                my_msgs.append(
                    {
                        "ts": arrow.get(datetime.fromtimestamp(float(message["ts"]))),
                        "text": message["text"],
                    }
                )

        return my_msgs

    def fetch_by_timeframe(self, project_name: str, slack_channel_id: str):
        my_messages = None
        print(f"{project_name=}")

        if project_name == "Stefan":
            my_messages = self.get_all_messages_by_me_from_slack_channel(
                SPARKASSE_CHANNEL_ID, slack_channel_id=slack_channel_id
            )

        if project_name == "Filip and Pavel":
            my_messages = self.get_all_messages_by_me_from_slack_channel(
                PAVEL_CHANNEL_ID, slack_channel_id=slack_channel_id
            )

        if (
            project_name == SlackProjectName.traverse.value
        ):  # name from the interactive slack menu, not enums
            my_messages = self.get_all_messages_by_me_from_slack_channel(
                TRAVERSE_CHANNEL_ID, slack_channel_id=slack_channel_id
            )
        message_map_by_ts = {}
        for msg in my_messages:
            date: str = arrow.get(msg["ts"]).format(
                "YYYY-MM-DD"
            )  # Extract the date part of the "ts" value
            if date not in message_map_by_ts:
                message_map_by_ts[date] = []
            message_map_by_ts[date].append({"ts": msg["ts"], "value": msg["text"]})

        entries_to_write_to_clockify = []
        for day, messages in message_map_by_ts.items():
            if len(messages) == 1:
                message = messages[0]
                print(f"{message=}")
                start_time_pattern = r"\s[0-9]+\:[0-9]+\n"
                start_time: re.Match = re.search(start_time_pattern, message["value"])
                if start_time:
                    day_date = arrow.get(day).format("YYYY-MM-DD")
                    clean_start_time = start_time.group().lstrip().strip("\n")
                    start_time_str = f"{day_date} {clean_start_time}"
                    start_time_dt = arrow.get(start_time_str, "YYYY-MM-DD H:m")
                    entries_to_write_to_clockify.append(
                        {
                            "day": day,
                            "start": arrow.get(start_time_dt),
                            "end": message["ts"],
                        }
                    )

                continue
            if len(messages) == 2:
                start_ts = messages[-1]["ts"]
                end_ts = messages[0]["ts"]
                if project_name == "Stefan":
                    entries_to_write_to_clockify.append(
                        {"day": day, "start": start_ts, "end": end_ts}
                    )
                    continue

                if project_name == "Fillip and Pavel":
                    entries_to_write_to_clockify.append(
                        {"day": day, "start": start_ts, "end": end_ts}
                    )
                    continue

                if project_name == SlackProjectName.traverse.value:
                    entries_to_write_to_clockify.append(
                        {"day": day, "start": start_ts, "end": end_ts}
                    )
                    continue

            if len(messages) == 4:
                start_ts = messages[-1]["ts"]
                pause_ts = messages[-2]["ts"]
                resume_ts = messages[1]["ts"]
                end_ts = messages[0]["ts"]
                entries_to_write_to_clockify.append(
                    {"day": day, "start": start_ts, "end": pause_ts}
                )
                entries_to_write_to_clockify.append(
                    {"day": day, "start": resume_ts, "end": end_ts}
                )
                continue

            else:
                bot_client.chat_postMessage(
                    channel=slack_channel_id,
                    text=f"Data for *{day} from project: {project_name} needs manual review*",
                    mrkdwn=True,
                )
        return entries_to_write_to_clockify

    def submit_to_clockify(
        self,
        project_name: Union[ClientName, SlackProjectName],
        slack_channel_id: str,
    ):
        projects_map = self.clockify.get_my_active_workspaces()
        print(f"{projects_map=}")
        entries = self.fetch_by_timeframe(project_name.value, slack_channel_id)
        print("entries: ", entries)
        dates_to_report_to_user = []
        for entry in entries:
            entry: dict[str, arrow.Arrow]
            time_entry = ClockifyTimeEntry(
                start=arrow.get(entry["start"], tzinfo="Europe/Kiev").for_json(),
                end=arrow.get(entry["end"], tzinfo="Europe/Kiev").for_json(),
                billable=True,
                projectId=projects_map[ClockifyProjectName.traverse.value],
            )
            self.clockify.add_time_entry(ZEN_WORKSPACE_ID, time_entry)
            logging.info(
                f"Added time entry for project: {project_name.value}, {entry['day']}"
            )
            dates_to_report_to_user.append(entry["day"])

        if dates_to_report_to_user:
            bot_client.chat_postMessage(
                channel=slack_channel_id,
                text=f'Successfully inserted data for the following dates: {", ".join(dates_to_report_to_user)}',
            )


# if __name__ == "__main__":
#     slack = SlackManager(
#         oldest_msg_ts="2023-07-01T00:00",
#         latest_msg_ts=arrow.utcnow().for_json(),
#     )
#     slack.submit_to_clockify(project_name=ClientName.stefan)
# slack.fetch_by_timeframe(project_name=ClientName.stefan)
