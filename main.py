import os
from dotenv import load_dotenv

from src.llm import GeminiClient
from src.search import DuckDuckGoSearchTool
from src.agent import ResearchAgent

# Configuration
TOPIC = "Impact of Generative AI on MLOps"
NUM_QUESTIONS = 5
RESULTS_PER_QUESTION = 3
OUTPUT_DIR = "reports"
VERBOSE = True

def main():
    load_dotenv()
    
    if not os.getenv("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found. Please set it in the .env file.")
        return

    print("Initializing agents and clients...")
    llm = GeminiClient()
    search_tool = DuckDuckGoSearchTool()
    agent = ResearchAgent(llm=llm, search_tool=search_tool, verbose=VERBOSE)

    print(f"\nStarting research on: '{TOPIC}'\n" + "-"*40)
    result = agent.run(
        TOPIC,
        num_questions=NUM_QUESTIONS,
        results_per_question=RESULTS_PER_QUESTION,
    )

    saved_files = agent.save_outputs(result, output_dir=OUTPUT_DIR)

    print("\n" + "="*40)
    print("Done. Files created:")
    for name, path in saved_files.items():
        print(f"- {name.capitalize()}: {path}")

if __name__ == "__main__":
    main()
