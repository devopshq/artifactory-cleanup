from abc import ABC, abstractmethod
import os
from dataclasses import dataclass
from typing import Optional, List

import requests

from artifactory_cleanup.errors import NotificationError


@dataclass
class SlackConfig:
    token: str
    channel_id: str


@dataclass
class TelegramConfig:
    token: str
    chat_id: str


class Notifier(ABC):
    @abstractmethod
    def send_file(self, filename: str, comment: Optional[str] = None):
        pass


class SlackNotifier(Notifier):
    def __init__(self, config: SlackConfig):
        self._config = config

    def _headers(self):
        return {"Authorization": f"Bearer {self._config.token}"}

    def send_file(self, filename: str, comment: Optional[str] = None):
        if not os.path.exists(filename):
            raise NotificationError(f"Report file not found: {filename}")

        file_size = os.path.getsize(filename)
        file_basename = os.path.basename(filename)
        metadata_response = requests.post(
            "https://slack.com/api/files.getUploadURLExternal",
            headers=self._headers(),
            data={
                "filename": file_basename,
                "length": file_size,
            },
            timeout=30,
        )
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        if not metadata.get("ok"):
            raise NotificationError(
                f"Slack upload URL request failed: {metadata.get('error', 'unknown error')}"
            )

        upload_url = metadata["upload_url"]
        file_id = metadata["file_id"]

        with open(filename, "rb") as report_file:
            upload_response = requests.post(
                upload_url,
                data=report_file,
                headers={"Content-Type": "application/octet-stream"},
                timeout=60,
            )
            upload_response.raise_for_status()

        complete_payload = {
            "files": [{"id": file_id, "title": file_basename}],
            "channel_id": self._config.channel_id,
        }
        if comment:
            complete_payload["initial_comment"] = comment

        complete_response = requests.post(
            "https://slack.com/api/files.completeUploadExternal",
            headers={
                **self._headers(),
                "Content-Type": "application/json; charset=utf-8",
            },
            json=complete_payload,
            timeout=30,
        )
        complete_response.raise_for_status()
        complete = complete_response.json()
        if not complete.get("ok"):
            raise NotificationError(
                f"Slack upload finalize failed: {complete.get('error', 'unknown error')}"
            )


class TelegramNotifier(Notifier):
    def __init__(self, config: TelegramConfig):
        self._config = config

    def send_file(self, filename: str, comment: Optional[str] = None):
        if not os.path.exists(filename):
            raise NotificationError(f"Report file not found: {filename}")

        url = f"https://api.telegram.org/bot{self._config.token}/sendDocument"
        data = {"chat_id": self._config.chat_id}
        if comment:
            data["caption"] = comment

        with open(filename, "rb") as report_file:
            response = requests.post(
                url,
                data=data,
                files={"document": report_file},
                timeout=60,
            )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise NotificationError(
                f"Telegram send failed: {payload.get('description', 'unknown error')}"
            )


class ReportNotifier:
    def __init__(
        self,
        slack: Optional[SlackConfig] = None,
        telegram: Optional[TelegramConfig] = None,
    ):
        self._notifiers: List[Notifier] = []
        if slack:
            self._notifiers.append(SlackNotifier(slack))
        if telegram:
            self._notifiers.append(TelegramNotifier(telegram))

    def send_file(self, filename: str, comment: Optional[str] = None):
        for notifier in self._notifiers:
            notifier.send_file(filename=filename, comment=comment)
