"""
Use this script to generate the alarm file to be spoken when the door is opened.
The default is to say the nasal spray usage instruction.
After generation, rename the generated mp3 file as "default.mp3",
and move it to main/res/.
"""

from gtts import gTTS


if __name__ == "__main__":
    tts = gTTS("If you suspect an opioid overdose, follow these steps: Shake the naloxone nasal spray. Remove the red safety cap. Insert the nozzle into a nostril. Press firmly to release the dose. Administer half the dose in each nostril. Place the person in the recovery position if possible. Call nine one one for immediate assistance. Remember, naloxone is for emergency use only and does not replace professional medical help. Refer to the provided instructions for more details.")
    tts.save("default.mp3")
