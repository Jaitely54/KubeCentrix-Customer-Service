
from googletrans import Translator

def translate_text(text, target_language='en'):
    translator = Translator()
    translation = translator.translate(text, dest=target_language)
    return translation.text

def detect_language(text):
    translator = Translator()
    detection = translator.detect(text)
    return detection.lang
