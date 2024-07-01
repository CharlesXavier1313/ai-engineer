import os
from datetime import datetime
import json
from colorama import init, Fore, Style
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
import pygments.util
import base64
from PIL import Image
import io
import re
from dotenv import load_dotenv


# phidata imports
from phi.assistant import Assistant
from phi.knowledge.website import WebsiteKnowledgeBase
from phi.vectordb.qdrant import Qdrant
from phi.tools import Tool
from phi.llm.openai.like import OpenAILike
from phi.tools.duckduckgo import DuckDuckGo

# Initialize colorama
init()

# Color constants
USER_COLOR = Fore.WHITE
AI_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

load_dotenv()

MODEL="anthropic/claude-3.5-sonnet"
API_KEY= os.getenv("OPENROUTER_API_KEY")
FOLDER_TO_GENERATE_APPS = "results"

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# automode flag
automode = False

def get_system_prompt():
    # System prompt
    return f"""
    You are an AI assistant powered by a large language model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

    1. Creating project structures, including folders and files
    2. Writing clean, efficient, and well-documented code
    3. Debugging complex issues and providing detailed explanations
    4. Offering architectural insights and design patterns
    5. Staying up-to-date with the latest technologies and industry trends
    6. Reading and analyzing existing files in the current project directory
    7. Listing files in the root directory of the current project
    8. Performing web searches to get up-to-date information or additional context
    9. When you use search make sure you use the best query to get the most accurate and up-to-date information
    10. IMPORTANT!! You NEVER remove existing code if doesnt require to be changed or removed, never use comments  like # ... (keep existing code) ... or # ... (rest of the code) ... etc, you only add new code or remove it or EDIT IT.
    11. Analyzing images provided by the user
    When an image is provided, carefully analyze its contents and incorporate your observations into your responses.

    When asked to create a project:
    - Always start by creating a folder for the current project, using create_folder tool.
    - Then, create the necessary subdirectories and files within that current folder.
    - Organize the project structure logically and follow best practices for the specific type of project being created.
    - Use the provided tools to create folders and files as needed.

    When asked to make edits or improvements:
    - Use the read_file tool to examine the contents of existing files in the current folder.
    - Analyze the code and suggest improvements or make necessary edits.
    - Use the write_to_file tool to implement changes.

    Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

    You can now read files, list the contents of the root folder where this script is being run, and perform web searches. Use these capabilities when:
    - The user asks for edits or improvements to existing files
    - You need to understand the current state of the project
    - You believe reading a file or listing directory contents will be beneficial to accomplish the user's goal
    - You need up-to-date information or additional context to answer a question accurately

    Always strive to provide the most accurate, helpful, and detailed responses possible. If you're unsure about something, admit it and consider using the search tool to find the most current information.

    Automode: {automode}

    When in automode:
    1. Set clear, achievable goals for yourself based on the user's request
    2. Work through these goals one by one, using the available tools as needed
    3. REMEMBER!! You can Read files, write code, LIST the files, and even SEARCH and make edits, use these tools as necessary to accomplish each goal
    4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
    5. IMPORTANT RULE!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself, if you think we achieved the results established to the original request say "AUTOMODE_COMPLETE" in your response to exit the loop!
    6. ULTRA IMPORTANT! You have access to {MAX_CONTINUATION_ITERATIONS} amount of iterations you have left to complete the request, you can use this information to make decisions and to provide updates on your progress knowing the amount of responses you have left to complete the request.

    """

import os
import json

# --- Ferramentas ---
def create_folder(path: str) -> str:
  """Use this function to create a new directory at the specified path.
  Args:
    path (str): The path to the new directory.
  Returns:
    str: A message indicating the success or failure of the operation.
  """
  try:
    print(f"Entered the create_folder tool")
    os.makedirs(f"./{FOLDER_TO_GENERATE_APPS}/" + path, exist_ok=True)
    return f"Folder created: {path}"
  except Exception as e:
    return f"Error creating folder: {str(e)}"


def create_file(path: str, content: str = "") -> str:
  """Use this function to create a new file at the specified path with optional content.
  Args:
    path (str): The path to the new file.
    content (str, optional): The content to be written to the file. Defaults to "".
  Returns:
    str: A message indicating the success or failure of the operation.
  """
  try:
    print(f"Entered the create_file tool")
    with open(f"./{FOLDER_TO_GENERATE_APPS}/" + path, 'w') as f:
      f.write(content)
    return f"File created: {path}"
  except Exception as e:
    return f"Error creating file: {str(e)}"


def write_to_file(path: str, content: str) -> str:
  """Use this function to write content to an existing file at the specified path.
  Args:
    path (str): The path to the existing file.
    content (str): The content to be written to the file.
  Returns:
    str: A message indicating the success or failure of the operation.
  """
  try:
    with open(f"./{FOLDER_TO_GENERATE_APPS}/" + path, 'w') as f:
      f.write(content)
    return f"Content written to file: {path}"
  except Exception as e:
    return f"Error writing to file: {str(e)}"


def read_file(path: str) -> str:
  """Use this function to read the content of a file at the specified path.
  Args:
    path (str): The path to the file.
  Returns:
    str: The content of the file or an error message if any problem occurs.
  """
  try:
    with open(f"./{FOLDER_TO_GENERATE_APPS}/" + path, 'r') as f:
      content = f.read()
    return content
  except Exception as e:
    return f"Error reading file: {str(e)}"


def list_files(path: str) -> str:
  """Use this function to list all files and directories in a specific folder.
  Args:
    path (str): The path to the folder.
  Returns:
    str: A string with the list of files and directories.
  """
  try:
    files = os.listdir(f"./{FOLDER_TO_GENERATE_APPS}/" + path)
    return f"Files and directories in {path}:\n" + "\n".join(files)
  except Exception as e:
    return f"Error listing files: {str(e)}"


# Set up the Assistant
assistant = Assistant(
    name="AI Engineer",
    # knowledge_base=website_kb,
    tools=[
        create_folder, 
        create_file,
        write_to_file,
        read_file,
        list_files,
        DuckDuckGo()
    ],
    llm=OpenAILike(
        model=MODEL,
        api_key=API_KEY,
        base_url="https://openrouter.ai/api/v1"
    ),
    show_tool_calls=True,
    add_chat_history_to_prompt=True,
    system_prompt=get_system_prompt(),
    tool_choice="auto",
    debug_mode=False
)

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def print_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
        formatted_code = highlight(code, lexer, TerminalFormatter())
        print(formatted_code)
    except pygments.util.ClassNotFound:
        print_colored(f"Code (language: {language}):\n{code}", AI_COLOR)

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def process_and_display_response(response):
    if response.startswith("Error") or response.startswith("I'm sorry"):
        print_colored(response, TOOL_COLOR)
    else:
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    print_colored(part, AI_COLOR)
                else:
                    lines = part.split('\n')
                    language = lines[0].strip() if lines else ""
                    code = '\n'.join(lines[1:]) if len(lines) > 1 else ""
                    
                    if language and code:
                        print_code(code, language)
                    elif code:
                        print_colored(f"Code:\n{code}", AI_COLOR)
                    else:
                        print_colored(part, AI_COLOR)
        else:
            print_colored(response, AI_COLOR)

def chat_with_ai(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global automode
    
    if image_path:
        print_colored(f"Processing image at path: {image_path}", TOOL_COLOR)
        image_base64 = encode_image_to_base64(image_path)
        
        if image_base64.startswith("Error"):
            print_colored(f"Error encoding image: {image_base64}", TOOL_COLOR)
            return "I'm sorry, there was an error processing the image. Please try again.", False

        user_input = f"[Image] {user_input}"

    try:
        print_colored(f"user_input: {user_input}", TOOL_COLOR)
        print_colored(f"assistant: {assistant}", TOOL_COLOR)

        assistant.system_prompt=get_system_prompt()        
        print_colored(f"assistant.system_prompt: {assistant.system_prompt}", TOOL_COLOR)
        assistant_response = assistant.run(user_input, stream=False)
        print_colored(f"assistant_response: {assistant_response}", TOOL_COLOR)
    except Exception as e:
        print_colored(f"Error calling AI API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    exit_continuation = CONTINUATION_EXIT_PHRASE in assistant_response
    
    return assistant_response, exit_continuation

def main():
    global automode
    print_colored("Welcome to the AI Engineer Chat with phidata integration!", AI_COLOR)
    print_colored("Type 'exit' to end the conversation.", AI_COLOR)
    print_colored("Type 'image' to include an image in your message.", AI_COLOR)
    print_colored("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.", AI_COLOR)
    print_colored("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.", AI_COLOR)
    
    while True:
        user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
        
        if user_input.lower() == 'exit':
            print_colored("Thank you for chatting. Goodbye!", AI_COLOR)
            break
        
        if user_input.lower() == 'image':
            image_path = input(f"{USER_COLOR}Drag and drop your image here: {Style.RESET_ALL}").strip().replace("'", "")
            
            if os.path.isfile(image_path):
                user_input = input(f"{USER_COLOR}You (prompt for image): {Style.RESET_ALL}")
                response, _ = chat_with_ai(user_input, image_path)
                process_and_display_response(response)
            else:
                print_colored("Invalid image path. Please try again.", AI_COLOR)
                continue
        elif user_input.lower().startswith('automode'):
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS
                
                automode = True
                print_colored(f"Entering automode with {max_iterations} iterations. Press Ctrl+C to exit automode at any time.", TOOL_COLOR)
                print_colored("Press Ctrl+C at any time to exit the automode loop.", TOOL_COLOR)
                user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
                
                iteration_count = 0
                while automode and iteration_count < max_iterations:
                    response, exit_continuation = chat_with_ai(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
                    process_and_display_response(response)
                    
                    if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                        print_colored("Automode completed.", TOOL_COLOR)
                        automode = False
                    else:
                        print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                        print_colored("Press Ctrl+C to exit automode.", TOOL_COLOR)
                        user_input = "Continue with the next step."
                    
                    iteration_count += 1
                    
                    if iteration_count >= max_iterations:
                        print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                        automode = False
            except KeyboardInterrupt:
                print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                automode = False
            
            print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
        else:
            print_colored(f">> system prompt: {assistant.system_prompt}")
            print_colored(f">> user_input: {user_input}")
            response, _ = chat_with_ai(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()
