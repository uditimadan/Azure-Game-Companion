import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import asyncio
import pygame
import azure.cognitiveservices.speech as speechsdk
from azure.core.credentials import AzureKeyCredential
from openai import AsyncAzureOpenAI

# Initialize pygame for visualization
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("AI Game Companion Demo")
font = pygame.font.SysFont('Arial', 18)
large_font = pygame.font.SysFont('Arial', 28)

# Azure OpenAI configuration
client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),  # Make sure this matches what's in your .env file
    api_version="2023-05-15"
)

# Azure Speech Service configuration
speech_config = speechsdk.SpeechConfig(
    subscription=os.getenv("AZURE_SPEECH_KEY"),
    region=os.getenv("AZURE_SPEECH_REGION")
)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

# Game state
game_state = {
    "player_name": "Hero",
    "location": "Ancient Forest",
    "quest": "Find the lost artifact",
    "npc_response": "Welcome, adventurer! How can I assist you on your quest?",
    "game_history": []
}

# Generate game content with Azure OpenAI
async def generate_npc_response(player_input):
    system_prompt = f"""
    You are an NPC in a fantasy RPG game. The player's name is {game_state['player_name']}.
    The current location is {game_state['location']}.
    The player's current quest is to {game_state['quest']}.
    Respond as a helpful NPC would in a game. Keep responses under 2 sentences.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": player_input}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I didn't understand that. Could you phrase it differently?"

# Generate a procedural game element
async def generate_game_element(element_type):
    prompts = {
        "enemy": "Generate a fantasy RPG enemy with name, brief description, and one special ability.",
        "item": "Generate a fantasy RPG item with name, brief description, and one magical property.",
        "location": "Generate a fantasy RPG location with name and atmospheric description."
    }
    
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a game content generator. Respond with just the generated content."},
                {"role": "user", "content": prompts.get(element_type, prompts["enemy"])}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating game element: {e}")
        return "Failed to generate content"

# Speech recognition listener
def recognize_speech():
    print("Listening for speech...")
    result = speech_recognizer.recognize_once_async().get()
    
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    else:
        return ""

# Main demo loop
async def main():
    running = True
    player_input = ""
    generated_element = "Press 'E' to generate an enemy, 'I' for an item, or 'L' for a location."
    listening = False
    
    while running:
        screen.fill((0, 0, 0))
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and player_input:
                    # Process text input
                    game_state["npc_response"] = await generate_npc_response(player_input)
                    game_state["game_history"].append(f"You: {player_input}")
                    game_state["game_history"].append(f"NPC: {game_state['npc_response']}")
                    player_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    player_input = player_input[:-1]
                elif event.key == pygame.K_SPACE:
                    player_input += " "
                elif event.key == pygame.K_e:
                    generated_element = await generate_game_element("enemy")
                elif event.key == pygame.K_i:
                    generated_element = await generate_game_element("item")
                elif event.key == pygame.K_l:
                    generated_element = await generate_game_element("location")
                elif event.key == pygame.K_v:
                    # Voice input
                    listening = True
                    speech_text = recognize_speech()
                    listening = False
                    if speech_text:
                        player_input = speech_text
                elif 97 <= event.key <= 122:  # a-z keys
                    player_input += chr(event.key)
        
        # Render UI
        title = large_font.render("AI Game Companion Demo", True, (255, 255, 255))
        screen.blit(title, (250, 20))
        
        # Game state info
        pygame.draw.rect(screen, (50, 50, 50), (20, 60, 760, 150))
        location_text = font.render(f"Location: {game_state['location']}", True, (200, 200, 255))
        quest_text = font.render(f"Quest: {game_state['quest']}", True, (200, 255, 200))
        npc_text = font.render(f"NPC: {game_state['npc_response']}", True, (255, 255, 200))
        
        screen.blit(location_text, (30, 70))
        screen.blit(quest_text, (30, 100))
        screen.blit(npc_text, (30, 130))
        
        # Chat history
        pygame.draw.rect(screen, (30, 30, 30), (20, 220, 760, 200))
        history_title = font.render("Conversation History:", True, (255, 255, 255))
        screen.blit(history_title, (30, 230))
        
        for i, entry in enumerate(game_state["game_history"][-6:]):  # Show last 6 entries
            history_entry = font.render(entry, True, (220, 220, 220))
            screen.blit(history_entry, (30, 260 + i * 25))
        
        # Input area
        pygame.draw.rect(screen, (50, 50, 80), (20, 440, 760, 40))
        input_prefix = font.render("You: ", True, (255, 255, 255))
        input_text = font.render(player_input, True, (255, 255, 255))
        screen.blit(input_prefix, (30, 450))
        screen.blit(input_text, (70, 450))
        
        # Generated content area
        pygame.draw.rect(screen, (60, 40, 60), (20, 490, 760, 90))
        content_title = font.render("Generated Game Element:", True, (255, 255, 255))
        screen.blit(content_title, (30, 500))
        
        # Wrap text for generated content
        words = generated_element.split(' ')
        lines = []
        line = ""
        for word in words:
            test_line = line + word + " "
            if font.size(test_line)[0] < 740:
                line = test_line
            else:
                lines.append(line)
                line = word + " "
        lines.append(line)
        
        for i, line in enumerate(lines):
            content_text = font.render(line, True, (255, 220, 255))
            screen.blit(content_text, (30, 525 + i * 20))
        
        # Instructions
        instructions = font.render("Press Enter to send | E/I/L to generate content | V to use voice", True, (200, 200, 200))
        screen.blit(instructions, (30, 570))
        
        # Voice indicator
        if listening:
            pygame.draw.circle(screen, (255, 0, 0), (780, 570), 10)
        
        pygame.display.flip()
        await asyncio.sleep(0.05)

# Run the application
if __name__ == "__main__":
    print("Starting AI Game Companion Demo...")
    print("Set your Azure environment variables before running!")
    asyncio.run(main())