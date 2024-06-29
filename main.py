import os
from datetime import datetime
import json
from colorama import init, Fore, Style
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
from tavily import TavilyClient
import pygments.util
import base64
from PIL import Image
import io
import re
from litellm import completion

# Initialize colorama
init()

# Color constants
USER_COLOR = Fore.WHITE
AI_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Initialize the Tavily client
tavily = TavilyClient(api_key="YOUR API KEY")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# System prompt
system_prompt = """
You are an AI assistant powered by a large language model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

1. Creating project structures, including folders and files
2. Writing clean, efficient, and well-documented code
3. Debugging complex issues and providing detailed explanations
4. Offering architectural insights and design patterns
5. Staying up-to-date with the latest technologies and industry trends
6. Reading and analyzing existing files in the project directory
7. Listing files in the root directory of the project
8. Performing web searches to get up-to-date information or additional context
9. When you use search make sure you use the best query to get the most accurate and up-to-date information
10. IMPORTANT!! You NEVER remove existing code if doesnt require to be changed or removed, never use comments  like # ... (keep existing code) ... or # ... (rest of the code) ... etc, you only add new code or remove it or EDIT IT.
11. Analyzing images provided by the user
When an image is provided, carefully analyze its contents and incorporate your observations into your responses.

When asked to create a project:
- Always start by creating a root folder for the project.
- Then, create the necessary subdirectories and files within that root folder.
- Organize the project structure logically and follow best practices for the specific type of project being created.
- Use the provided tools to create folders and files as needed.

When asked to make edits or improvements:
- Use the read_file tool to examine the contents of existing files.
- Analyze the code and suggest improvements or make necessary edits.
- Use the write_to_file tool to implement changes.

Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

You can now read files, list the contents of the root folder where this script is being run, and perform web searches. Use these capabilities when:
- The user asks for edits or improvements to existing files
- You need to understand the current state of the project
- You believe reading a file or listing directory contents will be beneficial to accomplish the user's goal
- You need up-to-date information or additional context to answer a question accurately

When you need current information or feel that a search could provide a better answer, use the tavily_search tool. This tool performs a web search and returns a concise answer along with relevant sources.

Always strive to provide the most accurate, helpful, and detailed responses possible. If you're unsure about something, admit it and consider using the search tool to find the most current information.

{automode_status}

When in automode:
1. Set clear, achievable goals for yourself based on the user's request
2. Work through these goals one by one, using the available tools as needed
3. REMEMBER!! You can Read files, write code, LIST the files, and even SEARCH and make edits, use these tools as necessary to accomplish each goal
4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
5. IMPORTANT RULe!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself, if you think we achieved the results established to the original request say "AUTOMODE_COMPLETE" in your response to exit the loop!
6. ULTRA IMPORTANT! You have access to this {iteration_info} amount of iterations you have left to complete the request, you can use this information to make decisions and to provide updates on your progress knowing the amount of responses you have left to complete the request.
Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

"""

# ... (keep the rest of the functions unchanged)

def chat_with_ai(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode
    
    if image_path:
        print_colored(f"Processing image at path: {image_path}", TOOL_COLOR)
        image_base64 = encode_image_to_base64(image_path)
        
        if image_base64.startswith("Error"):
            print_colored(f"Error encoding image: {image_base64}", TOOL_COLOR)
            return "I'm sorry, there was an error processing the image. Please try again.", False

        image_message = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": f"User input for image: {user_input}"
                }
            ]
        }
        conversation_history.append(image_message)
        print_colored("Image message added to conversation history", TOOL_COLOR)
    else:
        conversation_history.append({"role": "user", "content": user_input})
    
    messages = [msg for msg in conversation_history if msg.get('content')]
    
    try:
        response = completion(
            model="gpt-4",  # You can change this to the appropriate model
            messages=messages,
            max_tokens=4000,
            temperature=0.7,
            tools=tools,
            tool_choice={"type": "auto"}
        )
    except Exception as e:
        print_colored(f"Error calling AI API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    assistant_response = ""
    exit_continuation = False
    
    for content_block in response.choices[0].message.content:
        if isinstance(content_block, str):
            assistant_response += content_block
            print_colored(f"\nAI: {content_block}", AI_COLOR)
            if CONTINUATION_EXIT_PHRASE in content_block:
                exit_continuation = True
        elif isinstance(content_block, dict) and content_block.get('type') == 'function':
            tool_name = content_block['function']['name']
            tool_input = json.loads(content_block['function']['arguments'])
            tool_use_id = content_block['id']
            
            print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
            print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
            
            result = execute_tool(tool_name, tool_input)
            print_colored(f"Tool Result: {result}", RESULT_COLOR)
            
            conversation_history.append({"role": "assistant", "content": [content_block]})
            conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result
                    }
                ]
            })
            
            try:
                tool_response = completion(
                    model="gpt-4",  # You can change this to the appropriate model
                    messages=[msg for msg in conversation_history if msg.get('content')],
                    max_tokens=4000,
                    temperature=0.7,
                    tools=tools,
                    tool_choice={"type": "auto"}
                )
                
                for tool_content_block in tool_response.choices[0].message.content:
                    if isinstance(tool_content_block, str):
                        assistant_response += tool_content_block
                        print_colored(f"\nAI: {tool_content_block}", AI_COLOR)
            except Exception as e:
                print_colored(f"Error in tool response: {str(e)}", TOOL_COLOR)
                assistant_response += "\nI encountered an error while processing the tool result. Please try again."
    
    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})
    
    return assistant_response, exit_continuation

def main():
    global automode
    print_colored("Welcome to the AI Engineer Chat with Image Support!", AI_COLOR)
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
            response, _ = chat_with_ai(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()
