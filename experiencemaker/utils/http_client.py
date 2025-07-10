import http
import time
from typing import Any

import requests
from loguru import logger
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from experiencemaker.enumeration.http_enum import HttpEnum


class HttpClient(BaseModel):
    url: str = Field(default="")
    keep_alive: bool = Field(default=False, description="if true, use session to keep long connection")
    timeout: int = Field(default=300, description="request timeout, second")

    return_default_if_error: bool = Field(default=True)
    request_start_time: float = Field(default_factory=time.time)
    request_time_cost: float = Field(default=0.0, description="request time cost")

    retry_sleep_time: float = Field(default=0.5, description="interval time for retry")
    retry_time_multiplier: float = Field(default=2.0, description="retry time multiplier")
    retry_max_count: int = Field(default=1, description="maximum number of retries")

    _client: Any = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        self._client = requests.Session() if self.keep_alive else requests
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        self.request_time_cost: float = time.time() - self.request_start_time

    def close(self):
        if isinstance(self._client, requests.Session):
            self._client.close()

    def _request(self,
                 data: str = None,
                 json_data: dict = None,
                 headers: dict = None,
                 stream: bool = False,
                 http_enum: HttpEnum | str = HttpEnum.POST):

        if isinstance(http_enum, str):
            http_enum = HttpEnum(http_enum)

        if http_enum is HttpEnum.POST:
            response: requests.Response = self._client.post(url=self.url,
                                                            data=data,
                                                            json=json_data,
                                                            headers=headers,
                                                            stream=stream,
                                                            timeout=self.timeout)

        elif http_enum is HttpEnum.GET:
            response: requests.Response = self._client.get(url=self.url,
                                                           data=data,
                                                           json=json_data,
                                                           headers=headers,
                                                           stream=stream,
                                                           timeout=self.timeout)

        else:
            raise NotImplementedError

        if response.status_code != http.HTTPStatus.OK:
            raise RuntimeError(f"request failed! content={response.json()}")

        return response

    def parse_result(self, response: requests.Response | Any = None, **kwargs):
        return response.json()

    def return_default(self, **kwargs):
        return None

    def request(self,
                data: str | Any = None,
                json_data: dict = None,
                headers: dict = None,
                http_enum: HttpEnum | str = HttpEnum.POST,
                **kwargs):

        retry_sleep_time = self.retry_sleep_time
        for i in range(self.retry_max_count):
            try:
                response = self._request(data=data, json_data=json_data, headers=headers, http_enum=http_enum)
                result = self.parse_result(response=response,
                                           data=data,
                                           json_data=json_data,
                                           headers=headers,
                                           http_enum=http_enum,
                                           **kwargs)
                return result

            except Exception as e:
                logger.exception(f"{self.__class__.__name__} {i}th request failed with args={e.args}")

                if i == self.retry_max_count - 1:
                    if self.return_default_if_error:
                        return self.return_default()
                    else:
                        raise e

                retry_sleep_time *= self.retry_time_multiplier
                time.sleep(retry_sleep_time)

        return None

    def request_stream(self,
                       data: str = None,
                       json_data: dict = None,
                       headers: dict = None,
                       http_enum: HttpEnum | str = HttpEnum.POST,
                       **kwargs):

        retry_sleep_time = self.retry_sleep_time
        for i in range(self.retry_max_count):
            try:
                response = self._request(data=data,
                                         json_data=json_data,
                                         headers=headers,
                                         stream=True,
                                         http_enum=http_enum)
                request_context = {}
                for iter_idx, line in enumerate(response.iter_lines()):
                    yield self.parse_result(line=line,
                                            request_context=request_context,
                                            index=iter_idx,
                                            data=data,
                                            json_data=json_data,
                                            headers=headers,
                                            http_enum=http_enum,
                                            **kwargs)

                return None

            except Exception as e:
                logger.exception(f"{self.__class__.__name__} {i}th request failed with args={e.args}")

                if i == self.retry_max_count - 1:
                    if self.return_default_if_error:
                        return self.return_default()
                    else:
                        raise e

                retry_sleep_time *= self.retry_time_multiplier
                time.sleep(retry_sleep_time)

        return None
