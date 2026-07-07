import sys
import select
from threading import Thread
import uvicorn

from core.configs.llm import ask_luma, warmup
from core.audio.tts import LumaSpeaker
from core.audio.chunker import SpeechChunker
from core.audio.stt import LumaListener
from core.audio.normalize import normalize_command
from core.router import ask_luma_for_tool, might_be_file_action
from core.configs.personality import SPECIFIC_RESPONSES

from core import server

from tools.apps import open_app, close_app
from tools.files import delete_file_by_query, find_and_reveal_file
from tools.notis import battery_status, hardware_status, downloads_status
from tools.camera import turn_on_webcam, turn_off_webcam, enable_inspect_mode, inspect_this_area

def handle_local_command(user_input):
    command = normalize_command(user_input)

    if command.startswith("open "):
        return open_app(command[5:].strip())

    if command.startswith("close "):
        return close_app(command[6:].strip())

    if command.startswith("delete "):
        return delete_file_by_query(command[7:].strip())

    if command in {"battery", "battery status", "check battery"}:
        return battery_status()

    if command in {"hardware", "hardware status", "system status", "htop"}:
        return hardware_status()

    if command in {"downloads", "downloads status", "check downloads"}:
        return downloads_status()

    if command in {
        "turn on webcam",
        "open webcam",
        "webcam",
        "camera",
        "turn on camera",
        "start webcam",
        "start camera",
        "enable webcam",
        "enable camera",
    }:
        return turn_on_webcam()

    if command in {
        "turn off webcam",
        "close webcam",
        "stop webcam",
        "turn off camera",
        "close camera",
        "stop camera",
        "disable webcam",
        "disable camera",
    }:
        return turn_off_webcam()

    if command in {
        "inspect",
        "start inspect",
        "enable inspect",
        "inspect mode",
    }:
        return enable_inspect_mode()

    return None


def is_inspect_area_command(command: str) -> bool:
    return command in {
        "inspect this area",
        "inspect area",
        "analyze this area",
        "analyze area",
        "inspect that area",
        "look at this area",
        "what is in this area",
    }


def handle_ai_tool(user_input):
    if not might_be_file_action(user_input):
        return None

    tool_call = ask_luma_for_tool(user_input)

    if tool_call.get("tool") == "find_and_reveal_file":
        query = tool_call.get("args", {}).get("query", "").strip()

        if query:
            return find_and_reveal_file(query)

    return None

def start_api_server():
    uvicorn.run(
        server.app,
        host="127.0.0.1",
        port=8765,
        log_level="warning"
    )

def main():
    print("LUMA Lite booting...")
    warmup()

    print(r"""
                                                                                        ◇
                                                                           ◇════════════╋════════════◇
                                                                                        ◇

                                                                                    L. U. M. A.
                                                                     Language Understanding Machine Assistant
                                                                -------------------------------------------------
Push-to-talk : Cmd + F5
Type 'voices' to list voices
Type 'mute' or 'unmute' for speech
Type 'exit' to quit
""")

    speaker = LumaSpeaker(enabled=True, rate=220)
    listener = LumaListener(model_size="base.en")

    def hammerspoon_listen():
        speaker.interrupt()
        print("\n[LUMA listening...]", flush=True)

        spoken = listener.listen()

        if spoken:
            print(f"\n[Heard]: {spoken}", flush=True)
            server.pending_voice.put(spoken)
        else:
            print("LUMA: I didn't catch that, sir.", flush=True)
    
    server.listen_callback = hammerspoon_listen

    Thread(target=start_api_server, daemon=True).start()

    while True:

        print("\nYou: ", end="", flush=True)

        user_input = None

        while user_input is None:

            try:
                user_input = server.pending_voice.get_nowait()
                print(user_input)
                break

            except Exception:
                pass

            readable, _, _ = select.select([sys.stdin], [], [], 0.1)

            if readable:
                user_input = sys.stdin.readline().strip()
                break

        if not user_input:
            continue

        command = normalize_command(user_input)

        if command in {"exit", "quit"}:
            speaker.stop()
            break

        if command in {"stop", "pause", "wait", "luma stop", "stop talking"}:
            speaker.interrupt()
            print("LUMA: Stopped, sir.")
            continue

        if command == "mute":
            speaker.enabled = False
            print("LUMA voice muted.")
            continue

        if command == "unmute":
            speaker.enabled = True
            print("LUMA voice enabled.")
            continue

        if command == "voices":
            speaker.list_voices()
            continue

        if command.startswith("say "):
            message = user_input[4:].strip()

            if not message:
                print("LUMA: Say what, sir?")
                continue

            print(f"LUMA: {message}")
            speaker.say(message)
            continue

        if command in SPECIFIC_RESPONSES:
            response = SPECIFIC_RESPONSES[command]
            print(f"LUMA: {response}")
            speaker.say(response)
            continue

        local_result = handle_local_command(user_input)

        if local_result:
            print(f"LUMA: {local_result}")
            speaker.say(local_result)
            continue

        if is_inspect_area_command(command):
            print("LUMA: ", end="", flush=True)
            chunker = SpeechChunker(speaker)

            def on_chunk(token):
                chunker.feed(token)

            inspect_this_area(on_chunk=on_chunk)
            chunker.flush()
            continue

        tool_result = handle_ai_tool(user_input)

        if tool_result:
            print(f"LUMA: {tool_result}")
            speaker.say(tool_result)
            continue

        print("LUMA: ", end="", flush=True)
        chunker = SpeechChunker(speaker)

        def on_chunk(token):
            chunker.feed(token)

        ask_luma(user_input, on_chunk=on_chunk)
        chunker.flush()

if __name__ == "__main__":

    main()
