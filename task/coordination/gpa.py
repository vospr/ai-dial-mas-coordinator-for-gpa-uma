from copy import deepcopy
from typing import Optional, Any

from aidial_client import AsyncDial
from aidial_sdk.chat_completion import Role, Choice, Request, Message, CustomContent, Stage, Attachment
from pydantic import StrictStr

from task.stage_util import StageProcessor

_IS_GPA = "is_gpa"
_GPA_MESSAGES = "gpa_messages"


class GPAGateway:

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    async def response(
            self,
            choice: Choice,
            stage: Stage,
            request: Request,
            additional_instructions: Optional[str]
    ) -> Message:
        # 1. Create AsyncDial client
        api_key = request.api_key
        client: AsyncDial = AsyncDial(
            base_url=self.endpoint,
            api_key=api_key,
            api_version='2025-01-01-preview'
        )

        # 2. Make call with streaming
        chunks = await client.chat.completions.create(
            stream=True,
            messages=self.__prepare_gpa_messages(request, additional_instructions),
            deployment_name="general-purpose-agent",
            extra_headers={
                'x-conversation-id': request.headers.get('x-conversation-id'),
            }
        )

        # 3. Create variables for collecting response data
        content = ''
        result_custom_content: CustomContent = CustomContent(attachments=[])
        stages_map: dict[int, Stage] = {}
        
        # 4. Process streaming chunks
        async for chunk in chunks:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                
                # Print delta for debugging
                if delta:
                    print(delta)
                
                # Append content to stage
                if delta and delta.content:
                    stage.append_content(delta.content)
                    content += delta.content
                
                # Handle custom_content (attachments, state, stages)
                if cc := delta.custom_content:
                    # Handle attachments
                    if cc.attachments:
                        result_custom_content.attachments.extend(cc.attachments)

                    # Handle state
                    if cc.state:
                        result_custom_content.state = cc.state

                    # Propagate stages from GPA
                    cc_dict = cc.dict(exclude_none=True)
                    if stages := cc_dict.get("stages"):
                        for stg in stages:
                            idx = stg["index"]
                            
                            # If stage already exists, update it
                            if opened_stg := stages_map.get(idx):
                                if stg_content := stg.get("content"):
                                    opened_stg.append_content(stg_content)
                                elif stg_attachments := stg.get("attachments"):
                                    for stg_attachment in stg_attachments:
                                        opened_stg.add_attachment(Attachment(**stg_attachment))
                                elif stg.get("status") and stg.get("status") == 'completed':
                                    StageProcessor.close_stage_safely(stages_map[idx])
                            else:
                                # Open new stage and add to map
                                stages_map[idx] = StageProcessor.open_stage(choice, stg.get("name"))

        # Close any remaining open stages
        for stg in stages_map.values():
            StageProcessor.close_stage_safely(stg)

        # 5. Propagate result_custom_content to choice
        for attachment in result_custom_content.attachments:
            choice.add_attachment(
                Attachment(**attachment.dict(exclude_none=True))
            )

        # 6. Save GPA conversation info to state
        choice.set_state(
            {
                _IS_GPA: True,
                _GPA_MESSAGES: result_custom_content.state,
            }
        )

        # 7. Return assistant message
        return Message(
            role=Role.ASSISTANT,
            content=StrictStr(content),
        )

    def __prepare_gpa_messages(self, request: Request, additional_instructions: Optional[str]) -> list[dict[str, Any]]:
        # 1. Create empty array for GPA-related messages
        res_messages = []

        # 2. Iterate through request messages
        for idx in range(len(request.messages)):
            msg = request.messages[idx]
            if msg.role == Role.ASSISTANT:
                # Check if it's a GPA message
                if msg.custom_content and msg.custom_content.state:
                    msg_state = msg.custom_content.state
                    if msg_state.get(_IS_GPA):
                        # Add user request (always before assistant message)
                        res_messages.append(request.messages[idx-1].dict(exclude_none=True))
                        
                        # Copy assistant message and restore GPA format
                        copied_msg = deepcopy(msg)
                        copied_msg.custom_content.state = msg_state.get(_GPA_MESSAGES)
                        res_messages.append(copied_msg.dict(exclude_none=True))

        # 3. Add last message from request
        last_user_msg = request.messages[-1]
        custom_content = last_user_msg.custom_content
        
        # 4. If additional_instructions present, augment the message
        if additional_instructions:
            res_messages.append(
                {
                    "role": Role.USER,
                    "content": f"{last_user_msg.content}\n\n{additional_instructions}",
                    "custom_content": custom_content.dict(exclude_none=True) if custom_content else None,
                }
            )
        else:
            res_messages.append(last_user_msg.dict(exclude_none=True))

        # 5. Return prepared messages
        return res_messages
