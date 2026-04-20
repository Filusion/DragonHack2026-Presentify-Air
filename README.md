# Presentify-Air

**Presentify-Air** is a real-time lecture control assistant that enables presenters to control slides and capture notes using **hand gestures and voice**, eliminating the need for physical interaction.

## 🚀 Overview

Presentify-Air allows seamless, touch-free presentations. Using computer vision and speech recognition, presenters can navigate slides, interact with a virtual whiteboard, and automatically generate transcriptions — all in real time.

## ✨ Features

- 🖐️ **Gesture-Based Slide Control**  
  Navigate slides by swiping your hand with an open palm.

- 🧑‍🏫 **Virtual Whiteboard**  
  - Open and close a whiteboard using gestures  
  - Draw in the air naturally

- 🎯 **Smooth Drawing**  
  Hand movements are stabilized using a Kalman filter for precise and fluid drawing.

- 🎤 **Real-Time Transcription**  
  Automatically records and transcribes speech during the presentation.

## 🧠 Technologies Used

- **MediaPipe** – Hand tracking and gesture recognition  
- **Kalman Filter** – Motion smoothing for drawing  
- **OpenAI Whisper** – Speech-to-text transcription  
- **OpenCV** – Video capture and processing  

## ⚙️ How It Works

1. The camera captures live video input  
2. Hand gestures are detected using MediaPipe  
3. Gestures are interpreted as commands (e.g., slide navigation, drawing)  
4. Drawing input is smoothed using a Kalman filter  
5. Audio is recorded and transcribed using Whisper  

## 📌 Use Cases

- Lectures and teaching  
- Business presentations  
- Workshops and demos  
- Remote presentations  

## 🔮 Future Improvements

- Custom gesture configuration  
- Multi-language transcription
- Transcription summaries
- Slide content summarization  
- Integration with PowerPoint / Google Slides  
