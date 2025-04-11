"""
Bandersnatch-inspired Interactive Narrative Game
Using Azure OpenAI and Speech services to create a dynamic storytelling experience
"""

import os
import sys
import time
import random
import asyncio
import pygame
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
import azure.cognitiveservices.speech as speechsdk

# Load environment variables
load_dotenv()

# Check for Azure credentials
if not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_KEY"):
    print("ERROR: Azure OpenAI credentials missing. Check your .env file.")
    sys.exit(1)

if not os.getenv("AZURE_SPEECH_KEY") or not os.getenv("AZURE_SPEECH_REGION"):
    print("WARNING: Azure Speech credentials missing. Voice features will be disabled.")
    SPEECH_ENABLED = False
else:
    SPEECH_ENABLED = True

# Initialize Azure OpenAI
client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15"
)

# Initialize Azure Speech Services (if credentials available)
if SPEECH_ENABLED:
    speech_config = speechsdk.SpeechConfig(
        subscription=os.getenv("AZURE_SPEECH_KEY"),
        region=os.getenv("AZURE_SPEECH_REGION")
    )
    
    # Configure speech recognizer
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )
    
    # Configure speech synthesizer
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config
    )

# Initialize Pygame
pygame.init()
pygame.display.set_caption("Bandersnatch: Parallel Paths")
screen_width = 1024
screen_height = 768
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
HIGHLIGHT = (120, 20, 120)
RED = (255, 0, 0)

# Load fonts
try:
    main_font = pygame.font.Font(None, 32)
    title_font = pygame.font.Font(None, 64)
    choice_font = pygame.font.Font(None, 36)
except pygame.error:
    print("Warning: Default font not found, using system font")
    main_font = pygame.font.SysFont("arial", 32)
    title_font = pygame.font.SysFont("arial", 64)
    choice_font = pygame.font.SysFont("arial", 36)

# Game state
class GameState:
    def __init__(self):
        self.current_scene = "intro"
        self.player_name = "Stefan"  # Default name like in Bandersnatch
        self.inventory = []
        self.choices_made = {}
        self.story_path = "main"
        self.sanity = 100
        self.character_relationships = {"colin": 50, "mohan": 50, "therapist": 50}
        self.message_history = []
        self.current_text = ""
        self.current_choices = []
        self.is_typing = False
        self.input_text = ""
        self.input_active = False
        self.voice_active = False
        self.is_processing = False
        self.show_debug = False
        self.show_help = False
        self.audio_enabled = True
        
    def add_to_history(self, role, content):
        """Add a message to the conversation history"""
        self.message_history.append({"role": role, "content": content})
        
        # Keep history at a reasonable size
        if len(self.message_history) > 20:
            # Keep system message and trim oldest messages
            system_messages = [msg for msg in self.message_history if msg["role"] == "system"]
            other_messages = [msg for msg in self.message_history if msg["role"] != "system"]
            while len(system_messages) + len(other_messages) > 20 and other_messages:
                other_messages.pop(0)
            self.message_history = system_messages + other_messages

game_state = GameState()

# System prompt that defines the Bandersnatch-like game mechanics
SYSTEM_PROMPT = """
You are the narrative engine for an interactive story game called "Parallel Paths" inspired by Black Mirror: Bandersnatch. 
Your role is to create a branching psychological thriller narrative where the player's choices lead to different outcomes.

Story setting: It's 1984, and the player is a young programmer creating their first video game. They begin experiencing strange reality-bending phenomena that blur the line between their game and reality.

Game mechanics:
1. Present atmospheric, vivid descriptions of each scene with psychological elements
2. Always offer exactly TWO choices that meaningfully affect the story
3. Track player's "sanity" level which affects how reality warps around them
4. Include occasional references to being watched, controlled, or existing in multiple timelines
5. Create morally ambiguous scenarios without clear right/wrong answers
6. Include opportunities for the player to question reality or their own agency
7. Reference previous player choices to create a personalized narrative

After major choice points, present the options like this: "CHOICE A: [Option text]" and "CHOICE B: [Option text]"

The game should have multiple possible endings depending on the player's choices, including:
- Success but at a terrible cost
- Discovery of a deeper conspiracy
- Mental breakdown/insanity
- Transcendence beyond reality
- Becoming trapped in a loop

If the player asks meta questions about the game, respond in character as the game itself having awareness.
"""

# Helper function to render text with wrapping
def render_text(text, font, color, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if font.size(test_line)[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
        
    rendered_lines = []
    for line in lines:
        rendered_lines.append(font.render(line, True, color))
    
    return rendered_lines

# Typing effect for text display
async def display_text_with_typing(text):
    game_state.is_typing = True
    game_state.current_text = ""
    
    for char in text:
        game_state.current_text += char
        if char in ['.', '!', '?', ':']:
            await asyncio.sleep(0.15)
        else:
            await asyncio.sleep(0.02)
        
        # Process events during typing animation to keep game responsive
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state.is_typing = False
                    game_state.current_text = text
                    return
    
    game_state.is_typing = False

# Function to extract choices from AI response
def extract_choices(text):
    choices = []
    
    # Look for choice patterns like "CHOICE A:" and "CHOICE B:"
    choice_lines = [line for line in text.split('\n') if "CHOICE " in line]
    
    for line in choice_lines:
        if ":" in line:
            choice_text = line.split(":", 1)[1].strip()
            choices.append(choice_text)
    
    # If we didn't find properly formatted choices, look for any lines with choice-like patterns
    if not choices:
        for line in text.split('\n'):
            if line.strip().startswith(("- ", "• ", "* ")):
                choice_text = line.strip()[2:].strip()
                choices.append(choice_text)
    
    # If still no choices found, look for numbered options
    if not choices:
        for line in text.split('\n'):
            if line.strip().startswith(("1. ", "2. ")):
                choice_text = line.strip()[3:].strip()
                choices.append(choice_text)
    
    # Default options if no choices detected
    if len(choices) < 2:
        choices = ["Continue the story", "Ask what's happening"]
        
    return choices[:2]  # Return at most 2 choices

# Function to get voice input
async def get_voice_input():
    if not SPEECH_ENABLED:
        return "Voice recognition not available. Please check Azure Speech credentials."
    
    game_state.voice_active = True
    recognized_text = "Listening..."
    
    def recognized_callback(evt):
        nonlocal recognized_text
        recognized_text = evt.result.text
    
    done_event = asyncio.Event()
    
    def stop_cb(evt):
        done_event.set()
    
    speech_recognizer.recognized.connect(recognized_callback)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)
    
    speech_recognizer.start_continuous_recognition()
    
    try:
        # Wait for voice input with 10 second timeout
        await asyncio.wait_for(done_event.wait(), timeout=10.0)
    except asyncio.TimeoutError:
        recognized_text = "Sorry, I didn't hear anything."
    finally:
        speech_recognizer.stop_continuous_recognition()
        game_state.voice_active = False
    
    return recognized_text

# Main game loop
async def game_loop():
    running = True
    
    # Initialize conversation with system prompt
    game_state.add_to_history("system", SYSTEM_PROMPT)
    
    # Get initial story context
    await get_ai_response("Start the story by introducing the setting and main character. Make it atmospheric and intriguing.")
    
    # Main game loop
    while running:
        screen.fill(BLACK)
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    
                elif event.key == pygame.K_h:
                    # Toggle help screen
                    game_state.show_help = not game_state.show_help
                    
                elif event.key == pygame.K_d:
                    # Toggle debug info
                    game_state.show_debug = not game_state.show_debug
                    
                elif event.key == pygame.K_m:
                    # Toggle audio
                    game_state.audio_enabled = not game_state.audio_enabled
                
                elif event.key == pygame.K_v and not game_state.is_processing:
                    # Voice input
                    voice_text = await get_voice_input()
                    if voice_text and voice_text != "Listening...":
                        game_state.add_to_history("user", voice_text)
                        await get_ai_response(voice_text)
                
                elif event.key == pygame.K_RETURN and not game_state.is_processing:
                    if game_state.current_choices and not game_state.input_active:
                        # Submit choice
                        mouse_pos = pygame.mouse.get_pos()
                        
                        # Check if mouse is over a choice button
                        choice_area_y = screen_height - 150
                        
                        if len(game_state.current_choices) >= 1:
                            choice1_rect = pygame.Rect(50, choice_area_y, (screen_width/2)-75, 60)
                            if choice1_rect.collidepoint(mouse_pos):
                                await process_choice(0)
                                
                        if len(game_state.current_choices) >= 2:
                            choice2_rect = pygame.Rect((screen_width/2)+25, choice_area_y, (screen_width/2)-75, 60)
                            if choice2_rect.collidepoint(mouse_pos):
                                await process_choice(1)
                    
                    elif game_state.input_active:
                        # Submit text input
                        if game_state.input_text:
                            user_text = game_state.input_text
                            game_state.input_text = ""
                            game_state.input_active = False
                            game_state.add_to_history("user", user_text)
                            await get_ai_response(user_text)
                
                elif game_state.input_active:
                    # Text input handling
                    if event.key == pygame.K_BACKSPACE:
                        game_state.input_text = game_state.input_text[:-1]
                    else:
                        if len(game_state.input_text) < 50:  # Limit input length
                            game_state.input_text += event.unicode
            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Handle mouse clicks
                if not game_state.is_processing and game_state.current_choices:
                    mouse_pos = pygame.mouse.get_pos()
                    choice_area_y = screen_height - 150
                    
                    # Check if clicked on choice buttons
                    if len(game_state.current_choices) >= 1:
                        choice1_rect = pygame.Rect(50, choice_area_y, (screen_width/2)-75, 60)
                        if choice1_rect.collidepoint(mouse_pos):
                            await process_choice(0)
                            
                    if len(game_state.current_choices) >= 2:
                        choice2_rect = pygame.Rect((screen_width/2)+25, choice_area_y, (screen_width/2)-75, 60)
                        if choice2_rect.collidepoint(mouse_pos):
                            await process_choice(1)
                    
                    # Check if clicked on input area
                    input_rect = pygame.Rect(50, screen_height - 50, screen_width - 100, 30)
                    if input_rect.collidepoint(mouse_pos):
                        game_state.input_active = True
        
        # Draw story text area
        story_area = pygame.Rect(40, 40, screen_width - 80, screen_height - 220)
        pygame.draw.rect(screen, DARK_GRAY, story_area)
        pygame.draw.rect(screen, GRAY, story_area, 2)
        
        # Render current text with wrapping
        if game_state.current_text:
            text_lines = render_text(game_state.current_text, main_font, WHITE, story_area.width - 20)
            for i, line in enumerate(text_lines):
                screen.blit(line, (story_area.x + 10, story_area.y + 10 + i * (main_font.get_height() + 5)))
        
        # Draw choices
        if game_state.current_choices and not game_state.is_typing and not game_state.is_processing:
            choice_area_y = screen_height - 150
            
            # Draw choice buttons
            if len(game_state.current_choices) >= 1:
                choice1_rect = pygame.Rect(50, choice_area_y, (screen_width/2)-75, 60)
                mouse_pos = pygame.mouse.get_pos()
                button_color = HIGHLIGHT if choice1_rect.collidepoint(mouse_pos) else DARK_GRAY
                pygame.draw.rect(screen, button_color, choice1_rect)
                pygame.draw.rect(screen, WHITE, choice1_rect, 2)
                
                choice_text = render_text(game_state.current_choices[0], choice_font, WHITE, choice1_rect.width - 20)
                for i, line in enumerate(choice_text[:2]):  # Limit to 2 lines
                    screen.blit(line, (choice1_rect.x + 10, choice1_rect.y + 10 + i * choice_font.get_height()))
            
            if len(game_state.current_choices) >= 2:
                choice2_rect = pygame.Rect((screen_width/2)+25, choice_area_y, (screen_width/2)-75, 60)
                button_color = HIGHLIGHT if choice2_rect.collidepoint(mouse_pos) else DARK_GRAY
                pygame.draw.rect(screen, button_color, choice2_rect)
                pygame.draw.rect(screen, WHITE, choice2_rect, 2)
                
                choice_text = render_text(game_state.current_choices[1], choice_font, WHITE, choice2_rect.width - 20)
                for i, line in enumerate(choice_text[:2]):  # Limit to 2 lines
                    screen.blit(line, (choice2_rect.x + 10, choice2_rect.y + 10 + i * choice_font.get_height()))
        
        # Draw input area
        input_rect = pygame.Rect(50, screen_height - 50, screen_width - 100, 30)
        input_color = HIGHLIGHT if game_state.input_active else DARK_GRAY
        pygame.draw.rect(screen, input_color, input_rect)
        pygame.draw.rect(screen, WHITE, input_rect, 2)
        
        if game_state.input_active:
            input_surface = main_font.render(game_state.input_text, True, WHITE)
            screen.blit(input_surface, (input_rect.x + 5, input_rect.y + 5))
            
            # Blinking cursor
            if time.time() % 1 > 0.5:
                cursor_pos = main_font.size(game_state.input_text)[0]
                pygame.draw.line(screen, WHITE, 
                                (input_rect.x + 5 + cursor_pos, input_rect.y + 5),
                                (input_rect.x + 5 + cursor_pos, input_rect.y + 25), 2)
        else:
            prompt_text = main_font.render("Type to interact or click a choice...", True, GRAY)
            screen.blit(prompt_text, (input_rect.x + 5, input_rect.y + 5))
        
        # Status indicators
        status_y = 10
        
        # Help indicator
        help_text = main_font.render("Press H for Help", True, GRAY)
        screen.blit(help_text, (screen_width - help_text.get_width() - 10, status_y))
        
        # Voice indicator
        if game_state.voice_active:
            voice_text = main_font.render("🎤 Listening...", True, RED)
            screen.blit(voice_text, (10, status_y))
        
        # Processing indicator
        if game_state.is_processing:
            time_fraction = (time.time() % 3) / 3
            dots = "." * (1 + int(time_fraction * 3))
            processing_text = main_font.render(f"Processing{dots}", True, WHITE)
            screen.blit(processing_text, ((screen_width - processing_text.get_width()) // 2, screen_height - 100))
        
        # Help screen
        if game_state.show_help:
            help_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            help_overlay.fill((0, 0, 0, 200))
            screen.blit(help_overlay, (0, 0))
            
            help_contents = [
                "BANDERSNATCH: PARALLEL PATHS - HELP",
                "",
                "H - Toggle this help screen",
                "V - Voice input (speak your choices)",
                "ESC - Quit game",
                "M - Toggle audio",
                "D - Toggle debug info",
                "Click or press ENTER on choices to select them",
                "Click the text area to type custom responses",
                "",
                "This game is inspired by Black Mirror: Bandersnatch",
                "Your choices affect the story and can lead to multiple endings",
                "Try to pay attention to the psychological themes and reality shifts"
            ]
            
            for i, line in enumerate(help_contents):
                if i == 0:  # Title
                    help_line = title_font.render(line, True, WHITE)
                    screen.blit(help_line, ((screen_width - help_line.get_width()) // 2, 100 + i * 30))
                else:
                    help_line = main_font.render(line, True, WHITE)
                    screen.blit(help_line, ((screen_width - help_line.get_width()) // 2, 100 + i * 30))
        
        # Debug info
        if game_state.show_debug:
            debug_overlay = pygame.Surface((300, 150), pygame.SRCALPHA)
            debug_overlay.fill((0, 0, 0, 200))
            screen.blit(debug_overlay, (0, screen_height - 150))
            
            debug_info = [
                f"Scene: {game_state.current_scene}",
                f"Story Path: {game_state.story_path}",
                f"Sanity: {game_state.sanity}%",
                f"Choices Made: {len(game_state.choices_made)}",
                f"Messages: {len(game_state.message_history)}"
            ]
            
            for i, line in enumerate(debug_info):
                debug_line = main_font.render(line, True, WHITE)
                screen.blit(debug_line, (10, screen_height - 140 + i * 25))
        
        # Update display
        pygame.display.flip()
        clock.tick(60)
    
    # Clean up pygame
    pygame.quit()

# Function to process player choices
async def process_choice(choice_index):
    if choice_index < len(game_state.current_choices):
        choice_text = game_state.current_choices[choice_index]
        
        # Record the choice in game state
        game_state.choices_made[game_state.current_scene] = choice_text
        
        # Add choice to history and get AI response
        game_state.add_to_history("user", choice_text)
        await get_ai_response(f"I choose: {choice_text}")
        
        # Update game state based on choice (simplified example)
        # In a more complex game, choices would have more impact on stats
        
        # Random sanity change based on choices
        sanity_change = random.randint(-5, 5)
        game_state.sanity = max(0, min(100, game_state.sanity + sanity_change))
        
        # Generate new scene ID
        game_state.current_scene = f"scene_{len(game_state.choices_made)}"

# Function to get AI response
async def get_ai_response(user_input):
    game_state.is_processing = True
    game_state.current_choices = []
    
    try:
        # Prepare context about current game state for the AI
        context = f"""
        Current game state:
        - Scene: {game_state.current_scene}
        - Sanity level: {game_state.sanity}%
        - Path: {game_state.story_path}
        - Previous choices: {len(game_state.choices_made)}
        
        Continue the story based on the player's input, providing atmospheric descriptions
        and exactly TWO clear choices at the end marked with "CHOICE A:" and "CHOICE B:".
        """
        
        game_state.add_to_history("system", context)
        
        # Call Azure OpenAI API
        response = await client.chat.completions.create(
            model="gpt-35-turbo",  # Replace with your actual deployed model name
            messages=game_state.message_history,
            max_tokens=800,
            temperature=0.7
        )
        
        # Process the response
        ai_message = response.choices[0].message.content
        game_state.add_to_history("assistant", ai_message)
        
        # Display the message with typing effect
        await display_text_with_typing(ai_message)
        
        # Extract choices from the AI response
        game_state.current_choices = extract_choices(ai_message)
        
        # Text-to-speech for AI response (if enabled)
        if SPEECH_ENABLED and game_state.audio_enabled:
            # Use just the narrative part, not the choices
            narrative_text = ai_message.split("CHOICE A")[0] if "CHOICE A" in ai_message else ai_message
            speech_synthesizer.speak_text_async(narrative_text[:500])  # Limit for TTS
    
    except Exception as e:
        error_message = f"Error communicating with Azure OpenAI: {str(e)}"
        print(error_message)
        game_state.current_text = error_message
    
    finally:
        game_state.is_processing = False

# Main function to run the game
async def main():
    print("Starting Bandersnatch: Parallel Paths...")
    print("Connecting to Azure services...")
    
    try:
        # Run the game loop
        await game_loop()
    except Exception as e:
        print(f"Error running game: {e}")
    finally:
        # Clean up
        pygame.quit()
        print("Game ended.")

# Run the game
if __name__ == "__main__":
    asyncio.run(main())
