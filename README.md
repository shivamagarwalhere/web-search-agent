# React Research Agent

An intelligent research agent that leverages Google Gemini API and DuckDuckGo search to automatically generate comprehensive research reports on any given topic.

## Features

- **Automated Question Generation**: Generates relevant research questions based on a given topic
- **Web Search Integration**: Uses DuckDuckGo to search for answers to generated questions
- **AI-Powered Analysis**: Leverages Google Gemini API to analyze and synthesize search results
- **Report Generation**: Creates well-structured markdown reports with findings
- **Source Tracking**: Maintains a list of all sources consulted during research
- **Execution Tracing**: Logs all steps taken during the research process

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/shivamagarwalhere/web-search-agent.git
cd react_research_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

Run the main script with a predefined topic:

```bash
python main.py
```

By default, it researches "Impact of Generative AI on MLOps" and generates 5 questions with 3 search results per question.

### Customization

Edit the configuration in `main.py`:

```python
TOPIC = "Your Research Topic"
NUM_QUESTIONS = 5  # Number of questions to generate
RESULTS_PER_QUESTION = 3  # Search results per question
OUTPUT_DIR = "reports"  # Output directory for reports
VERBOSE = True  # Enable verbose logging
```

### Output

The agent generates the following files in the output directory:

- **report.md** - Formatted markdown research report
- **sources.json** - List of all sources consulted
- **trace.json** - Execution trace of all steps taken

## Project Structure

```
react_research_agent/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create manually)
└── src/
    ├── __init__.py         # Package initialization
    ├── agent.py            # ResearchAgent class
    ├── llm.py              # Google Gemini LLM client
    └── search.py           # DuckDuckGo search tool
```

## Dependencies

- `requests` (2.32.3) - HTTP library for API calls
- `beautifulsoup4` (4.12.3) - HTML parsing
- `python-dotenv` (1.0.1) - Environment variable management
- `lxml` (5.3.0) - XML/HTML parsing

## How It Works

1. **Initialization**: Loads the Gemini API key and initializes the LLM and search clients
2. **Question Generation**: Uses Gemini to generate relevant research questions about the topic
3. **Search**: Performs web searches for each question using DuckDuckGo
4. **Analysis**: Uses Gemini to analyze and synthesize search results
5. **Report Generation**: Creates a comprehensive markdown report with findings
6. **Output**: Saves the report, sources, and execution trace to files

## Configuration

### Environment Variables

- `GEMINI_API_KEY` (required) - Your Google Gemini API key for LLM functionality

## Requirements

See `requirements.txt` for the complete list of dependencies and versions.

## Notes

- Ensure you have a valid Gemini API key from Google AI Studio
- The agent requires internet access to perform web searches
- Generated reports are saved to the `reports/` directory by default

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues for bugs and feature requests.

## Author

Created as an intelligent research automation tool using state-of-the-art LLM and web search technologies.
