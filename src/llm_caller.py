"""
A simple, standalone script to make a single call to the Ollama LLM.
This script is designed to be called as a subprocess to ensure complete
memory cleanup after each call.
"""

import sys
import ollama

def main():
    """
    Takes a model name and a prompt from command-line arguments,
    calls the LLM, and prints the response to standard output.
    """
    if len(sys.argv) != 3:
        print("Usage: python llm_caller.py <model_name> \"<prompt_string>\"", file=sys.stderr)
        sys.exit(1)

    model_name = sys.argv[1]
    prompt = sys.argv[2]

    try:
        # Use the most direct API call possible
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.2}
        )
        
        # Print the successful result to stdout
        print(response['message']['content'])
        sys.exit(0)

    except Exception as e:
        # Print any errors to stderr so the parent process can see them
        print(f"LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()