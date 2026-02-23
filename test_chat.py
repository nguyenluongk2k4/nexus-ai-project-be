import asyncio
from uuid import UUID
from modules.chat.tasks import _process_chat_intent_async

async def main():
    print("Testing chat processor async directly...")
    try:
        session_id = "feef4cc3-beb8-488d-a2bb-7ca096f37b16"
        user_id = "4fbee216-cff7-4b39-a362-0fb20a3b2cea"
        res = await _process_chat_intent_async(
            session_id=session_id,
            user_message="tôi muốn học backend test 2",
            request_id="test-req-123",
            user_id=user_id,
            attachments=[],
            user_msg_id=str(UUID("e4d164bd-7c74-45e7-98b3-2eaf5237a253"))
        )
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
