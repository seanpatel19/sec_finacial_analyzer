# SEC Filing Summarizer with Local LLM

A simple yet powerful tool to download, parse, and summarize SEC filings using the EDGAR API and a locally running Large Language Model (LLM).

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [To-Do / Future Enhancements](#to-do--future-enhancements)
- [License](#license)

## Features

-   **Direct SEC EDGAR Integration:** Downloads public filings directly from the official SEC EDGAR API.
-   **On-Demand Analysis:** Specify a company's stock ticker and the desired filing type (e.g., 10-K, 10-Q) for targeted analysis.
-   **Local Processing:** All data parsing and summarization is handled by a locally running LLM, ensuring privacy and control over your data.
-   **Simplified Insights:** Transforms lengthy, complex legal and financial documents into concise, easy-to-understand summaries.

## How It Works

The project follows a simple, automated workflow:

1.  **User Input:** The user provides a stock ticker (e.g., `AAPL` for Apple Inc.) and a filing type (e.g., `10-K`).
2.  **API Request:** The script constructs a request to the SEC EDGAR API to locate and download the most recent specified filing for that company.
3.  **Parsing:** The downloaded filing (often in a complex HTML or XBRL format) is parsed to extract the relevant textual content.
4.  **LLM Interaction:** The cleaned text is sent as a prompt to your locally running LLM via an API call.
5.  **Summarization:** The LLM processes the text and generates a summary.
6.  **Output:** The final summary is displayed to the user.

## Prerequisites

Before you begin, ensure you have the following installed and running:

1.  **Python 3.9+**: Check your version with `python3 --version`.
2.  **A Locally Running LLM**: This tool does **not** include the LLM itself. You must have an LLM running locally with an accessible API endpoint. Popular options include:
    -   [Ollama](https://ollama.com/) (Recommended for ease of use)
    -   [LM Studio](https://lmstudio.ai/)
    -   A custom API server using [llama.cpp](https://github.com/ggerganov/llama.cpp)
3.  **SEC EDGAR User-Agent**: The SEC requires a custom User-Agent for all API requests. You can format it as `YourName YourEmail@example.com`. This is crucial to avoid being blocked.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YourUsername/your-repository-name.git
    cd your-repository-name
    ```

2.  **Example Environment provided in .env.example:**
  

3.  **Install the required Python packages:**
    (First, make sure you have your dependencies listed in a `requirements.txt` file.)
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you don't have a `requirements.txt` file yet, you can create one with `pip freeze > requirements.txt` after installing necessary libraries like `requests`.*

4.  **Set up your configuration:**
    Create a file named `.env` in the root directory of the project by copying the example file:
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file with your specific settings.

## Usage

Once installed and configured, you can run the main script from your terminal.

*(This is an example. Adjust the command based on your script's name and arguments.)*

```bash
python main.py MSFT --form 10-K
