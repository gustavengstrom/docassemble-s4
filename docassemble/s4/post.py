from docassemble.base.util import get_config
from docassemble.base.util import log
from docassemble.base.util import DAFile, DADateTime
from docassemble.base.functions import interview_url, user_info, get_uid
from datetime import datetime
import psycopg2
import json
import requests
import os
import base64
from urllib.parse import urlparse
from urllib.parse import parse_qs


def get_ticket_aux_data(ticket_id: str):
    django_hostname = os.environ["DJANGOHOSTNAME"]
    try:
        url = "https://{}/webhooks/get_ticket_aux_data/?id={}".format(
            ticket_id, django_hostname
        )
        response = requests.get(url)
        if response.status_code != 200:
            log(f"An error occured: {response.content}", "console")
        else:
            log(
                f"Success retrieving ticket data. Content: {response.content}",
                "console",
            )
        return response.status_code, response.content
    except Exception as e:
        log(f"A connection error occured when submitting the interview: {e}", "console")
        return 400


def validate_session(token):

    django_hostname = os.environ["DJANGOHOSTNAME"]
    data = {}
    data["token"] = token
    data["session_id"] = get_uid()
    data["survey_url"] = interview_url(style="short", local=True).split("?")[0]
    try:
        json_data = json.dumps(data)
        url = f"https://{django_hostname}/webhooks/validate-da-session/"
        log(f"Validating data at: {url}")
        # "http://django:8000/webhooks/validate-da-session/"
        response = requests.post(
            url,
            data=json_data,
            headers={"Content-type": "application/json", "Accept": "text/plain"},
        )
        if response.status_code != 200:
            log(f"An error occured: {response.content}", "console")
        return response.status_code, response.content
    except Exception as e:
        log(f"A connection error occured when submitting the interview: {e}", "console")
        return 400, None


def store_interview_results(data):
    """Post interview to django backend."""
    django_hostname = os.environ["DJANGOHOSTNAME"]
    respondent_user_info = user_info()
    for item in data["survey_data"]:
        if isinstance(item["value"], DADateTime):
            item["value"] = item["value"].format_date("yyyy-MM-dd")

    data["docassemble_email"] = respondent_user_info.email
    data["docassemble_user_id"] = respondent_user_info.id
    survey_absolute_url = interview_url(style="short", local=True)
    data["survey_url"] = survey_absolute_url.split("?")[0]
    parsed_url = urlparse(survey_absolute_url)
    data["session_id"] = parse_qs(parsed_url.query)["session"][0]
    data["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        json_data = json.dumps(data)
        url = f"https://{django_hostname}/webhooks/docassemble_receiver/"
        log(f"Submitting data to: {url}")
        # "http://django:8000/webhooks/docassemble_receiver/"
        response = requests.post(
            url,
            data=json_data,
            headers={"Content-type": "application/json", "Accept": "text/plain"},
        )
        if response.status_code != 200:
            log(f"An error occured: {response.content}", "console")
        return response.status_code, response.content
    except Exception as e:
        log(f"A connection error occured when submitting the interview: {e}", "console")
        return 400, None
