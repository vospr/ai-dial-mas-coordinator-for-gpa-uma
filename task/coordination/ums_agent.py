import json
from typing import Optional

import httpx
from aidial_sdk.chat_completion import Role, Request, Message, Stage, Choice
from pydantic import StrictStr


_UMS_CONVERSATION_ID = "ums_conversation_id"


class UMSAgentGateway:

    def __init__(self, ums_agent_endpoint: str):
        self.ums_agent_endpoint = ums_agent_endpoint

    async def response(
            self,
            choice: Choice,
            stage: Stage,
            request: Request,
            additional_instructions: Optional[str]
    ) -> Message:
        # 1. Get UMS conversation id
        ums_conversation_id = self.__get_ums_conversation_id(request)

        # 2. If no conversation id found, create new conversation
        if not ums_conversation_id:
            ums_conversation_id = await self.__create_ums_conversation()
            stage.append_content(f"_Created new UMS conversation: {ums_conversation_id}_\n\n")

        # 3. Get last message and make augmentation with additional instructions
        user_message = request.messages[-1].content
        if additional_instructions:
            user_message = f"{user_message}\n\n{additional_instructions}"

        # 4. Call UMS Agent
        content = await self.__call_ums_agent(
            conversation_id=ums_conversation_id,
            user_message=user_message,
            stage=stage
        )

        # Set conversation ID to state for next requests
        choice.set_state({_UMS_CONVERSATION_ID: ums_conversation_id})

        # 5. Return assistant message
        return Message(
            role=Role.ASSISTANT,
            content=StrictStr(content),
        )


    def __get_ums_conversation_id(self, request: Request) -> Optional[str]:
        """Extract UMS conversation ID from previous messages if it exists"""
        # Iterate through message history
        for msg in request.messages:
            if msg.custom_content and msg.custom_content.state:
                ums_conversation_id = msg.custom_content.state.get(_UMS_CONVERSATION_ID)
                if ums_conversation_id:
                    return ums_conversation_id
        return None

    async def __create_ums_conversation(self) -> str:
        """Create a new conversation on UMS agent side"""
        # 1. Create async context manager
        async with httpx.AsyncClient() as client:
            # 2. Make POST request to create conversation
            response = await client.post(
                f"{self.ums_agent_endpoint}/conversations",
                json={"title": "UMS Agent Conversation"},
                timeout=30.0
            )
            response.raise_for_status()
            
            # 3. Get response json and return id
            conversation_data = response.json()
            return conversation_data['id']

    async def __call_ums_agent(
            self,
            conversation_id: str,
            user_message: str,
            stage: Stage
    ) -> str:
        """Call UMS agent and stream the response"""
        # 1. Create async context manager
        async with httpx.AsyncClient() as client:
            # 2. Make POST request to chat with streaming enabled
            response = await client.post(
                f"{self.ums_agent_endpoint}/conversations/{conversation_id}/chat",
                json={
                    "message": {
                        "role": "user",
                        "content": user_message
                    },
                    "stream": True
                },
                timeout=60.0
            )
            response.raise_for_status()

            # 3. Parse streaming response
            content = ''
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data_str = line[6:]  # Cut the 'data: ' prefix

                    # Check for end of stream
                    if data_str == '[DONE]':
                        break

                    try:
                        data = json.loads(data_str)

                        # Skip conversation_id message
                        if 'conversation_id' in data:
                            continue

                        # Extract content from choices
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if delta_content := delta.get('content'):
                                # Append chunks to stage and accumulate
                                stage.append_content(delta_content)
                                content += delta_content
                    except json.JSONDecodeError:
                        continue

            return content
