# Parellel Paths

An interactive game companion powered by Azure AI services that demonstrates generative AI capabilities in gaming.

<img width="591" alt="Screenshot 2025-04-11 at 9 03 52 AM" src="https://github.com/user-attachments/assets/ec0740da-a489-4bd0-949d-8b3c47877c07" />


## Features
- Dynamic NPC conversations using Azure OpenAI
- Voice command recognition with Azure Speech Services
- Procedural game content generation
- Interactive pygame-based interface

## Setup Requirements
- Python 3.8+
- Azure OpenAI Service access
- Azure Speech Services subscription

## Installation
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt` / pip install pygame openai azure-cognitiveservices-speech python-dotenv
3. Configure environment variables (see below)
4. Run the application: `python src/game_companion.py`

## Environment Variables
Set the following environment variables with your Azure credentials:
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_KEY
- AZURE_SPEECH_KEY
- AZURE_SPEECH_REGION

## Demo Instructions
- Type text and press Enter to interact with the NPC
- Press 'V' to use voice commands
- Press 'E', 'I', or 'L' to generate game elements
