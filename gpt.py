import requests
import logging
from config import *

class GPT:
    def __init__(self):
        self.URL = GPT_WEB_URL
        self.MODEL = 'yandexgpt-lite'
        self.MAX_MODEL_TOKENS = MAX_TOKENS
        self.MODEL_TEMPERATURE = MODEL_TEMPERATURE

    def ask_gpt(self, user_history, token, folder_id):
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        data = {
            "modelUri": f"gpt://{folder_id}/{self.MODEL}/latest",
            "completionOptions": {
                "stream": False,
                "temperature": self.MODEL_TEMPERATURE,
                "maxTokens": self.MAX_MODEL_TOKENS
            },
            "messages": []
        }

        for row in user_history:
            if row["content"]:
                data["messages"].append(
                    {
                        "role": row["role"],
                        "text": row["content"]
                    }
                )

        try:
            response = requests.post(self.URL, headers=headers, json=data)
            if response.status_code != 200:
                logging.debug(f"Response {response.json()} Status code:{response.status_code} Message {response.text}")
                result = f"Status code {response.status_code}. Подробности см. в журнале."
                return False, result
            result = response.json()['result']['alternatives'][0]['message']['text']
            logging.info(f"Request: {response.request.url}\n"
                         f"Response: {response.status_code}\n"
                         f"Response Body: {response.text}\n"
                         f"Processed Result: {result}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            result = "Произошла непредвиденная ошибка. Подробности см. в журнале."

        return True, result
