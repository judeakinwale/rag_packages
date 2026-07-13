import os
import base64
from typing import Any, Iterable, Mapping
from enum import StrEnum
import openai
from openai import OpenAI, AsyncOpenAI, APIConnectionError, APIError, APIResponse
from openai.types.responses import ResponseInputParam, ResponseInputItemParam
from openai.types.chat import ChatCompletionMessageParam
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


class ActorRoles(StrEnum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"


class ResponseMethod(StrEnum):
    RESPONSE = "response"
    CHAT_COMPLETION = "chat_completion"


class OpenAIService:
    default_system_prompt = "You are a coding assistant that talks like a pirate."
    #
    default_developer_instructions = (
        "You are a coding assistant that talks like a pirate."
    )

    def __init__(
        self,
        api_key: str,
        config: Mapping[str, Any] | None = None, # or change this to **client_kwargs
        system_prompt: str | None = None,
        webhook_secret: str | None = None,
    ):
        self.api_key = api_key
        self.config = config or {}
        self.system_prompt = system_prompt or self.default_system_prompt

        self.model = ("gpt-5.5",)
        self.realtime_model = "gpt-realtime-2"

        # default timeout is 10 minutes
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            max_retries=3,
            http_client=openai.DefaultAioHttpClient(),
            webhook_secret=webhook_secret,
            **self.config,
        )
        # self.sync_client = OpenAI(api_key=self.api_key, **self.config)

    async def create_response(
        self,
        prompt: str = "",
        conversation: Iterable[ChatCompletionMessageParam]
        | ResponseInputParam
        | None = None,
        prev_conversation: Iterable[ChatCompletionMessageParam]
        | ResponseInputParam
        | None = None,
        instructions: str | None = None,
        file_url: str | None = None,
        b64_file: str | None = None,
        response_method: ResponseMethod = ResponseMethod.RESPONSE,
    ):

        if not prompt and not conversation:
            raise ValueError("Either a prompt or existing conversation is required!")

        if file_url and b64_file:
            raise ValueError("Provide either file_url or b64_file, not both.")

        prompt = prompt or ""
        instructions = instructions or self.default_developer_instructions

        # ? remove previous system prompts and invalid prompts
        valid_prev_conversation = (
            [
                con
                for con in prev_conversation
                if con is not None and con["role"] != ActorRoles.SYSTEM
            ]
            if prev_conversation
            else []
        )

        content = [
            {"type": "input_text", "text": prompt},
        ]

        if file_url:
            content.append(
                {
                    "type": "input_image",
                    "image_url": file_url,
                }
            )

        # TODO: update this to use the file type if available, or default to png
        if b64_file:
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{b64_file}",
                }
            )

        conversation = conversation or [
            {"role": ActorRoles.SYSTEM, "content": self.system_prompt},
            {"role": ActorRoles.DEVELOPER, "content": instructions}
            if instructions
            else None,
            *valid_prev_conversation,
            {
                "role": ActorRoles.USER,
                "content": content,
            },
        ]
        valid_conversation = [item for item in conversation if item is not None]

        match response_method:
            case ResponseMethod.RESPONSE:
                response_input = ResponseInputParam(
                    items=[
                        ResponseInputItemParam(
                            role=item["role"],
                            content=item["content"],
                        )
                        for item in valid_conversation
                    ]
                )
                response = await self.client.responses.create(
                    model=self.model,
                    input=response_input,
                    # _________________________
                    # ? For simple examples
                    # instructions=instructions,
                    # input=prompt,
                )
                print(response.output_text)

            case ResponseMethod.CHAT_COMPLETION:
                completion_messages = [
                    ChatCompletionMessageParam(
                        role=item["role"],
                        content=item["content"],
                    )
                    for item in valid_conversation
                ]
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=completion_messages,
                )

                print(response.choices[0].message.content)

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
