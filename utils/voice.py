# speech_utils.py

import pyttsx3
import speech_recognition as sr

def text_to_speech(text):
    """
    Convert text to speech and play it.
    """
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def speech_to_text():
    """
    Convert speech to text.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand that.")
            return None
        except sr.RequestError:
            print("Sorry, there was an error with the speech recognition service.")
            return None

# Test the functions
if __name__ == "__main__":
    text_to_speech("Welcome to the Banking Assistant. How can I help you today?")
    user_input = speech_to_text()
    if user_input:
        text_to_speech(f"You said: {user_input}")