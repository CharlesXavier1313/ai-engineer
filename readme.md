# 🤖 AI Engineer (forked from Doriandarko/claude-engineer)

AI Engineer is an interactive command-line interface (CLI) that leverages the power of large language models through LiteLLM to assist with software development tasks. This tool combines the capabilities of advanced language models with practical file system operations and web search functionality.

## ✨ Features

- 💬 Interactive chat interface with support for various language models via phidata and openrouter
- 📁 File system operations (create folders, files, read/write files)
- 🔍 Web search capabilities using DuckDuckGo Tool from phidata
  - You can use these tools through phidata: Arxiv, Apify, CSV, DuckDb, DuckDuckGo, Email, Exa, File, Newspaper4k, OpenBBTools, Pubmed, Resend, Serpapi, Shell, SQL, Tavily, Wikipedia, Website, YFinance, Youtube, Zendesk.
- 🌈 Syntax highlighting for code snippets
- 🏗️ Project structure creation and management
- 🧐 Code analysis and improvement suggestions
- 🖼️ Vision capabilities support via drag and drop of images in the terminal
- 🚀 Automode for autonomous task completion
- 🔄 Iteration tracking in automode

## 🛠️ Installation

1. Clone this repository
   ```
   git clone https://github.com/renatocaliari/ai-engineer.git
   cd ai-engineer
   ```
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your API keys:

   - Add your OpenRouter API key in a .env file

     ```env
     OPENROUTER_API_KEY=your_openrouter_api_key
     ```

## 🚀 Usage

Run the main script to start the AI Engineer interface:

```
python main.py
```

Once started, you can interact with AI Engineer by typing your queries or commands. Some example interactions:

- "Create a new Python project structure for a web application"
- "Explain the code in file.py and suggest improvements"
- "Search for the latest best practices in React development"
- "Help me debug this error: [paste your error message]"

Special commands:

- Type 'exit' to end the conversation and close the application.
- Type 'image' to include an image in your message.
- Type 'automode' plus the max amount of iterations to enter Autonomous mode.
- Press Ctrl+C at any time to exit the automode to return to regular chat.

### 🤖 Automode

Automode allows AI Engineer to work autonomously on complex tasks. When in automode:

1. LLM sets clear, achievable goals based on your request.
2. It works through these goals one by one, using available tools as needed.
3. LLM provides regular updates on its progress.
4. Automode continues until goals are completed or the maximum number of iterations is reached.

To use automode:

1. Type 'automode' when prompted for input.
2. Provide your request when prompted.
3. LLM will work autonomously, providing updates after each iteration.
4. Automode exits when the task is completed or after reaching the maximum number of iterations.

Note: AI Engineer will only have access to the files in the root folders of the script or any folder path you provide it.

## 🥳 Credits

forked from Doriandarko/claude-engineer

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
