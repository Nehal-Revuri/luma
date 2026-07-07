import queue
import threading
import time
from AppKit import NSSpeechSynthesizer

class LumaSpeaker:
    def __init__(self, enabled=True, rate=230, voice=None):
        self.enabled = enabled
        self.q = queue.Queue()
        self.voice = voice
        self.rate = rate

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        self.synth = NSSpeechSynthesizer.alloc().init()

        if self.voice:
            self.synth.setVoice_(self.voice)

        self.synth.setRate_(self.rate)

        while True:
            text = self.q.get()

            if text is None:
                self.q.task_done()
                break

            if self.enabled and text.strip():
                self.synth.startSpeakingString_(text)

                while self.synth.isSpeaking():
                    time.sleep(0.05)

            self.q.task_done()

    def say(self, text):
        if text and text.strip():
            self.q.put(text.strip())

    def list_voices(self):
        voices = NSSpeechSynthesizer.availableVoices()
        for i, voice in enumerate(voices):
            print(f"{i}: {voice}")

    def stop(self):
        self.q.put(None)

    def interrupt(self):
        while not self.q.empty():
            try:
                self.q.get_nowait()
                self.q.task_done()
            except queue.Empty:
                break

        if hasattr(self, "synth"):
            self.synth.stopSpeaking()

