# 🎤 Presentify Air – Voice-Controlled Presentation Assistant

A real-time voice transcription and presentation control system built for live lectures, demos, and hackathons.

This app listens to speech, converts it into text using OpenAI Whisper, and executes commands like:
- 👉 Next slide  
- 👈 Previous slide  
- 💾 Save board  
- 🎯 Focus mode  

---

## 🚀 Features

- 🎙️ Real-time speech-to-text transcription (Whisper API)
- ⚡ Low-latency chunk-based audio processing
- 🧠 Command detection from natural speech
- 🎮 Automatic slide control via keyboard simulation
- 📊 Detailed transcript logging (timestamps, pauses, speech ratio)
- 🌐 Simple frontend interface
- 🧪 Built for live demos and hackathons

---

## 🧱 Project Structure

```
voice/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── transcripts.txt
│   ├── transcripts_detailed.jsonl
│   ├── commands.txt
│   └── sessions/
│
├── frontend/
│   └── index.html
│
└── run_instructions.txt
```

---

## ⚙️ Requirements

Install dependencies:

```
pip install -r requirements.txt
```

---

## 🔑 Environment Setup

### Windows
```
set OPENAI_API_KEY=your_api_key
```

### Linux / WSL / Mac
```
export OPENAI_API_KEY=your_api_key
```

---

## ▶️ How to Run

### 1. Start backend
```
uvicorn app:app --reload
```

### 2. Start frontend
```
python -m http.server 5500
```

Open:
```
http://127.0.0.1:5500
```

---

## 🎤 How It Works

1. Audio is recorded in chunks  
2. Sent to backend (`/transcribe-chunk`)  
3. Whisper converts speech → text  
4. Commands are detected  
5. Actions are executed (keyboard control)  

---

## ⚠️ Known Issues

- Audio must be in supported formats (webm, wav, mp3)
- PyAutoGUI may not work on some systems
- Command detection is currently exact-match

---

## 🧠 Future Improvements

- Smarter NLP command detection
- Live transcript UI
- Auto summaries
- Multi-user sessions

---

## 🏆 Hackathon Use

Great for:
- Live presentations
- Teaching assistants
- Demo automation

---

## 💡 Notes

- Logs and generated files are ignored in `.gitignore`
- Designed for real-time use
