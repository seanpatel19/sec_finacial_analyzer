SEC Filing Summarizer with Local LLM
A simple yet powerful tool to download, parse, and summarize SEC filings using the EDGAR API and a locally running Large Language Model (LLM).

Table of Contents
Features
How It Works
Prerequisites
Installation
Usage
Configuration
To-Do / Future Enhancements
License
Features
Direct SEC EDGAR Integration: Downloads public filings directly from the official SEC EDGAR API.
On-Demand Analysis: Specify a company's stock ticker and the desired filing type (e.g., 10-K, 10-Q) for targeted analysis.
Local Processing: All data parsing and summarization is handled by a locally running LLM, ensuring privacy and control over your data.
Simplified Insights: Transforms lengthy, complex legal and financial documents into concise, easy-to-understand summaries.
How It Works
The project follows a simple, automated workflow:

User Input: The user provides a stock ticker (e.g., AAPL for Apple Inc.) and a filing type (e.g., 10-K).
API Request: The script constructs a request to the SEC EDGAR API to locate and download the most recent specified filing for that company.
Parsing: The downloaded filing (often in a complex HTML or XBRL format) is parsed to extract the relevant textual content.
LLM Interaction: The cleaned text is sent as a prompt to your locally running LLM via an API call.
Summarization: The LLM processes the text and generates a summary.
Output: The final summary is displayed to the user.
Prerequisites
Before you begin, ensure you have the following installed and running:

Python 3.8+: Check your version with python3 --version.
A Locally Running LLM: This tool does not include the LLM itself. You must have an LLM running locally with an accessible API endpoint. Popular options include:
Ollama (Recommended for ease of use)
LM Studio
A custom API server using llama.cpp
SEC EDGAR User-Agent: The SEC requires a custom User-Agent for all API requests. You can format it as YourName YourEmail@example.com. This is crucial to avoid being blocked.
Installation
Clone the repository:

bash
git clone https://github.com/YourUsername/your-repository-name.git
cd your-repository-name
Create and activate a virtual environment (recommended):

bash
python3 -m venv venv
source venv/bin/activate
# On Windows, use: venv\Scripts\activate
Install the required Python packages:
(First, make sure you have your dependencies listed in a requirements.txt file.)

bash
pip install -r requirements.txt
Note: If you don't have a requirements.txt file yet, you can create one with pip freeze > requirements.txt after installing necessary libraries like requests.

Set up your configuration:
Create a file named .env in the root directory of the project by copying the example file:

bash
cp .env.example .env
Now, edit the .env file with your specific settings.

Usage
Once installed and configured, you can run the main script from your terminal.

(This is an example. Adjust the command based on your script's name and arguments.)

bash
python main.py --ticker MSFT --filing "10-K"
The script will then print the summary to the console.

text
Fetching latest 10-K for MSFT...
Downloading filing...
Parsing document...
Sending to local LLM for summarization...

--- Summary ---
Microsoft's latest 10-K filing indicates strong growth in its cloud computing segment, particularly Azure...
[...rest of the summary...]
Configuration
All configuration is handled in the .env file.

.env.example

ini
# .env.example - Copy this to .env and fill in your values

# -- SEC EDGAR API Configuration --
# Required by the SEC. Format: "Sample Company Name Your.Email@example.com"
SEC_USER_AGENT="Your Name your.email@example.com"

# -- Local LLM API Configuration --
# The full URL of your local LLM's API endpoint for completions
LLM_API_ENDPOINT="http://localhost:11434/api/generate"

# The name of the model you are using with your local LLM (e.g., for Ollama)
LLM_MODEL_NAME="llama3"
SEC_USER_AGENT: Required. Your identifier for the SEC's systems.
LLM_API_ENDPOINT: The URL where your local LLM is listening for requests. The example http://localhost:11434/api/generate is the default for Ollama.
LLM_MODEL_NAME: The specific model you want to use for the summarization task (e.g., llama3, mistral, phi3).
To-Do / Future Enhancements
 Create a simple web interface (using Flask or Streamlit) for easier user input.
 Add support for batch processing multiple tickers or filings at once.
 Improve parsing to handle different sections of the filings (e.g., "Risk Factors," "MD&A").
 Allow users to choose different summary lengths or styles.
 Cache downloaded filings to avoid redundant API calls.
License
This project is licensed under the MIT License. See the LICENSE file for details.

How to Use This Template:

Save: Create a file named README.md and paste this text into it.
Customize: Go through and replace placeholders like YourUsername, your-repository-name, and your.email@example.com.
Adjust: Modify the Usage section to match how your script actually runs.
requirements.txt: Make sure you have a requirements.txt file that lists the libraries your project needs (e.g., requests, python-dotenv, beautifulsoup4).
Commit and Push: Add the README.md to git, commit, and push it to your GitHub repository.
bash
git add README.md
git commit -m "docs: Create initial README file"
git push
