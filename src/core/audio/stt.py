import queue
import tempfile
import time
import wave

import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel

class LumaListener:
    def __init__(self, model_size="base.en", device="cpu", compute_type="int8"):
        self.sample_rate = 16000
        self.block_size = 512
        self.block_ms = self.block_size / self.sample_rate * 1000
    
        self.whisper = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

        self.vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True
        )

    def _speech_prob(self, audio_block):
        tensor = torch.from_numpy(audio_block).float()
        with torch.no_grad():
            prob = self.vad_model(tensor, self.sample_rate).item()
        return prob

    def listen(
        self,
        start_threshold=0.55,
        end_threshold=0.35,
        silence_seconds=0.9,
        max_seconds=15,
        pre_roll_seconds=0.4
    ):
        print("Listening...")

        audio_q = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                pass
            audio_q.put(indata.copy().reshape(-1))

        speech_started = False
        speech_chunks = []
        pre_roll = []
        silent_for = 0.0
        total_time = 0.0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.block_size,
            callback=callback
        ):
            while total_time < max_seconds:
                try:
                    block = audio_q.get(timeout=1)
                except queue.Empty:
                    continue

                total_time += self.block_ms / 1000
                prob = self._speech_prob(block)

                if not speech_started:
                    pre_roll.append(block)

                    max_pre_blocks = int(pre_roll_seconds / (self.block_ms / 1000))
                    pre_roll = pre_roll[-max_pre_blocks:]

                    if prob >= start_threshold:
                        speech_started = True
                        speech_chunks.extend(pre_roll)
                        speech_chunks.append(block)
                        silent_for = 0.0
                        print("Speech detected.")
                else:
                    speech_chunks.append(block)

                    if prob < end_threshold:
                        silent_for += self.block_ms / 1000
                    else:
                        silent_for = 0.0

                    if silent_for >= silence_seconds:
                        break

        if not speech_chunks:
            return ""

        audio = np.concatenate(speech_chunks)

        if len(audio) < self.sample_rate * 0.25:
            return ""

        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = np.int16(audio * 32767)

        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            with wave.open(temp_file.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

            segments, _ = self.whisper.transcribe(
                temp_file.name,
                beam_size=1,
                vad_filter=True
            )

            text = " ".join(segment.text.strip() for segment in segments)

        return text.strip()
