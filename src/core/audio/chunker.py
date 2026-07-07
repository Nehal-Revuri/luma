class SpeechChunker:
    def __init__(self, speaker, min_words=14):
        self.speaker = speaker   
        self.buffer = ""
        self.min_words = min_words
    
    def feed(self, token):
        if not token:
            return

        self.buffer += token
        text = self.buffer.strip()

        if not text:
            return
            
        words = text.split()
                
        if text.endswith((".", "!", "?")) or len(words) >= self.min_words:
            self.speaker.say(text)
            self.buffer = ""
        
    def flush(self):
        if self.buffer.strip():
            self.speaker.say(self.buffer.strip())
            self.buffer = ""
        

