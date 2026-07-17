from collections.abc import Sequence
from typing import Any, Literal, Mapping, TypeAlias, overload
from enum import StrEnum
import openai
from openai import AsyncOpenAI, AsyncStream
from rag_packages.shared.ai.system_prompt import get_system_prompt
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionChunk,
)
from openai.types.chat.chat_completion_content_part_image_param import (
    ChatCompletionContentPartImageParam,
)
from openai.types.chat.chat_completion_content_part_text_param import (
    ChatCompletionContentPartTextParam,
)
from openai.types.responses import Response, ResponseInputParam, ResponseStreamEvent
from openai.types.responses.easy_input_message_param import EasyInputMessageParam
from openai.types.responses.response_input_image_param import ResponseInputImageParam
from openai.types.responses.response_input_text_param import ResponseInputTextParam
from openai.types.realtime import ConversationItem, ConversationItemParam

# from openai.auth import gcp_id_token_provider
# from openai.auth import azure_managed_identity_token_provider

# # Alternate client init
# client = OpenAI(
#     workload_identity={
#         "identity_provider_id": "idp-123",
#         "service_account_id": "sa-456",

#         # # ? using GCP Workload Identity Federation (requires google-auth package)
#         # "provider": gcp_id_token_provider(audience="https://api.openai.com/v1"),

#         # # ? using Azure Managed Identity (requires azure-identity package)
#         # "provider": azure_managed_identity_token_provider(
#         #     resource="https://management.azure.com/",
#         # ),
#     },
# )


# Default variable names: OPENAI_API_KEY, OPENAI_WEBHOOK_SECRET can be omitted when creating the openai client


class ActorRole(StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"


class ResponseMethod(StrEnum):
    RESPONSE = "response"
    CHAT_COMPLETION = "chat_completion"


ConversationMessage: TypeAlias = EasyInputMessageParam | ChatCompletionMessageParam
ConversationMessages: TypeAlias = Sequence[ConversationMessage]
ResponseContentPart: TypeAlias = ResponseInputTextParam | ResponseInputImageParam
ChatContentPart: TypeAlias = (
    ChatCompletionContentPartTextParam | ChatCompletionContentPartImageParam
)
OpenAIResponse: TypeAlias = Response | ChatCompletion
OpenAIStreamResponse: TypeAlias = (
    AsyncStream[ResponseStreamEvent] | AsyncStream[ChatCompletionChunk]
)


class OpenAIService:
    default_approved_websites = ["https://www.wikipedia.org/"]
    default_system_prompt = get_system_prompt(default_approved_websites)
    default_model = "gpt-5.5"
    default_realtime_model = "gpt-realtime-2"

    def __init__(
        self,
        api_key: str,
        config: Mapping[str, Any] | None = None,  # or change this to **client_kwargs
        system_prompt: str | None = None,
        approved_websites: list[str] | None = None,
        webhook_secret: str | None = None,
    ):
        self.api_key = api_key
        self.config = config or {}
        self.system_prompt = system_prompt or self.default_system_prompt
        self.approved_websites = approved_websites or self.default_approved_websites

        self.model = self.default_model
        self.realtime_model = self.default_realtime_model

        # default timeout is 10 minutes
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            max_retries=3,
            http_client=openai.DefaultAioHttpClient(),
            webhook_secret=webhook_secret,
            **self.config,
        )
        # self.sync_client = OpenAI(api_key=self.api_key, **self.config)

    def _build_response_content(
        self,
        prompt: str,
        file_url: str | None,
        b64_file: str | None,
        b64_file_mime_type: str | None = None,
    ) -> list[ResponseContentPart]:
        content: list[ResponseContentPart] = [{"type": "input_text", "text": prompt}]

        if file_url:
            content.append(
                {
                    "type": "input_image",
                    "image_url": file_url,
                    "detail": "auto",
                }
            )

        if b64_file:
            mime_type = b64_file_mime_type or "image/png"
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{b64_file}",
                    "detail": "auto",
                }
            )

        return content

    def _build_chat_content(
        self,
        prompt: str,
        file_url: str | None,
        b64_file: str | None,
        b64_file_mime_type: str | None = None,
    ) -> str | list[ChatContentPart]:
        if not file_url and not b64_file:
            return prompt

        content: list[ChatContentPart] = [{"type": "text", "text": prompt}]

        mime_type = b64_file_mime_type or "image/png"

        image_url = file_url or f"data:{mime_type};base64,{b64_file}"
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_url, "detail": "auto"},
            }
        )
        return content

    def _filter_prev_conversation(
        self,
        prev_conversation: ConversationMessages | None,
    ) -> list[ConversationMessage]:
        if not prev_conversation:
            return []

        return [
            item
            for item in prev_conversation
            if item is not None
            and item.get("role") != ActorRole.SYSTEM
            and item.get("role") != ActorRole.DEVELOPER
        ]

    # TODO: update this to properly handle conversation messages as lists without a prompt provided separately
    def _build_response_messages(
        self,
        prompt: str,
        prev_conversation: ResponseInputParam | None,
        instructions: str | None,
        file_url: str | None,
        b64_file: str | None,
        b64_file_mime_type: str | None = None,
    ) -> ResponseInputParam:
        messages: list[EasyInputMessageParam] = [
            {"role": ActorRole.SYSTEM, "content": self.system_prompt},
        ]

        if instructions:
            messages.append({"role": ActorRole.DEVELOPER, "content": instructions})

        messages.extend(self._filter_prev_conversation(prev_conversation))

        messages.append(
            {
                "role": ActorRole.USER,
                "content": self._build_response_content(
                    prompt, file_url, b64_file, b64_file_mime_type
                ),
            }
        )
        return messages

    # TODO: cascade conversation message list change from _build_chat_messages here
    def _build_chat_messages(
        self,
        prompt: str,
        prev_conversation: Sequence[ChatCompletionMessageParam] | None,
        instructions: str | None,
        file_url: str | None,
        b64_file: str | None,
        b64_file_mime_type: str | None = None,
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": ActorRole.SYSTEM, "content": self.system_prompt},
        ]

        if instructions:
            messages.append({"role": ActorRole.DEVELOPER, "content": instructions})

        messages.extend(self._filter_prev_conversation(prev_conversation))

        messages.append(
            {
                "role": ActorRole.USER,
                "content": self._build_chat_content(
                    prompt, file_url, b64_file, b64_file_mime_type
                ),
            }
        )
        return messages

    @overload
    async def create_response(
        self,
        prompt: str = "",
        conversation: ResponseInputParam | None = None,
        prev_conversation: ResponseInputParam | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        b64_file_mime_type: str | None = None,
        stream: Literal[False] = False,
        response_method: Literal[ResponseMethod.RESPONSE] = ResponseMethod.RESPONSE,
    ) -> Response: ...

    @overload
    async def create_response(
        self,
        prompt: str = "",
        conversation: Sequence[ChatCompletionMessageParam] | None = None,
        prev_conversation: Sequence[ChatCompletionMessageParam] | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        b64_file_mime_type: str | None = None,
        stream: Literal[False] = False,
        response_method: Literal[
            ResponseMethod.CHAT_COMPLETION
        ] = ResponseMethod.CHAT_COMPLETION,
    ) -> ChatCompletion: ...

    @overload
    async def create_response(
        self,
        prompt: str = "",
        conversation: ResponseInputParam | None = None,
        prev_conversation: ResponseInputParam | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        b64_file_mime_type: str | None = None,
        stream: Literal[True] = True,
        response_method: Literal[ResponseMethod.RESPONSE] = ResponseMethod.RESPONSE,
    ) -> AsyncStream[ResponseStreamEvent]: ...

    @overload
    async def create_response(
        self,
        prompt: str = "",
        conversation: Sequence[ChatCompletionMessageParam] | None = None,
        prev_conversation: Sequence[ChatCompletionMessageParam] | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        b64_file_mime_type: str | None = None,
        stream: Literal[True] = True,
        response_method: Literal[
            ResponseMethod.CHAT_COMPLETION
        ] = ResponseMethod.CHAT_COMPLETION,
    ) -> AsyncStream[ChatCompletionChunk]: ...

    # TODO: cascade conversation message list change from _build_chat_messages here
    async def create_response(
        self,
        prompt: str = "",
        conversation: ConversationMessages | None = None,
        prev_conversation: ConversationMessages | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        b64_file_mime_type: str | None = None,
        stream: bool = False,
        response_method: ResponseMethod = ResponseMethod.RESPONSE,
    ) -> OpenAIResponse | OpenAIStreamResponse:

        if not prompt and not conversation:
            raise ValueError("Either a prompt or existing conversation is required!")

        if file_url and b64_file:
            raise ValueError("Provide either file_url or b64_file, not both.")

        match response_method:
            case ResponseMethod.RESPONSE:
                response_input = (
                    list(conversation)
                    if conversation is not None
                    else self._build_response_messages(
                        prompt=prompt,
                        prev_conversation=prev_conversation,
                        instructions=instructions,
                        file_url=file_url,
                        b64_file=b64_file,
                        b64_file_mime_type=b64_file_mime_type,
                    )
                )
                response = await self.client.responses.create(
                    model=self.model,
                    input=response_input,
                    stream=True,
                    # stream=stream,
                )
                # print(response.output_text)

            case ResponseMethod.CHAT_COMPLETION:
                chat_messages = (
                    list(conversation)
                    if conversation is not None
                    else self._build_chat_messages(
                        prompt=prompt,
                        prev_conversation=prev_conversation,
                        instructions=instructions,
                        file_url=file_url,
                        b64_file=b64_file,
                        b64_file_mime_type=b64_file_mime_type,
                    )
                )
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=chat_messages,
                    stream=stream,
                )
                # print(response.choices[0].message.content)

            case _:
                raise ValueError(
                    f"Invalid response method: {response_method} provided!."
                )

        return response

    async def realtime(
        self,
        prompt: str = "",
        conversation_item: ConversationItem | ConversationItemParam | None = None,
        previous_item_id: str | None = None,
    ):
        async with self.client.realtime.connect(
            model=self.realtime_model
        ) as connection:
            await connection.session.update(
                session={"type": "realtime", "output_modalities": ["text"]}
            )

            conversation_item = conversation_item or ConversationItemParam(
                type="message",
                role="user",
                content=[{"type": "input_text", "text": prompt}],
            )

            await connection.conversation.item.create(
                item=conversation_item,
                previous_item_id=previous_item_id,
            )
            await connection.response.create()

            async for event in connection:
                if event.type == "response.output_text.delta":
                    print(event.delta, flush=True, end="")

                elif event.type == "response.output_text.done":
                    print()

                elif event.type == "response.done":
                    break

                elif event.type == "error":
                    print(
                        f"error_type: {event.error.type}: [{event.error.code}] -  {event.error.event_id} {event.error.message}"
                    )

    async def testing(self):
        pass

        # # Example code for working with paginated list data
        #
        # all_jobs = []
        # # Iterate through items across all pages, issuing requests as needed.
        # async for job in client.fine_tuning.jobs.list(
        #     limit=20,
        # ):
        #     all_jobs.append(job)
        # print(all_jobs)
        #
        # OR
        #
        # first_page = await client.fine_tuning.jobs.list(
        #     limit=20,
        # )
        # if first_page.has_next_page():
        #     print(f"will fetch next page using these details: {first_page.next_page_info()}")
        #     next_page = await first_page.get_next_page()
        #     print(f"number of items we just fetched: {len(next_page.data)}")

        # # Example code for working with uploaded files
        # client.files.create(
        #     file=Path("input.jsonl"),
        #     purpose="fine-tune",
        # )

        # # Example code for working with webhook payloads (request from FastAPI or Flask)
        # # Unwrap
        # event = client.webhooks.unwrap(request_body_text, request.headers)
        # # Verify
        # client.webhooks.verify_signature(request_body, request.headers)

    # ________________________________________________________________________________________________________________________
