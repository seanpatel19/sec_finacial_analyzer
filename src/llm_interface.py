"""
Local LLM interface for text generation.
Handles all communication with a local language model server via the Ollama library,
using the modern 'chat' completion endpoint for better instruction following.
"""

import logging
import time
from typing import Optional

try:
    import ollama
except ImportError:
    raise ImportError("The 'ollama' package is required. Please install it with: pip install ollama")

logger = logging.getLogger(__name__)

class LLMInterface:
    """A streamlined interface for local LLM communication via Ollama."""
    
    def __init__(self, model_name: str = "llama3"):
        """
        Initializes the LLM interface and ensures the specified model is available.

        Args:
            model_name: The name of the Ollama model to use (e.g., 'llama3', 'mistral').
        """
        self.model_name = model_name
        
        try:
            self.client = ollama.Client()
            self._ensure_model_available()
        except Exception as e:
            logger.error(f"Failed to initialize or connect to Ollama client: {e}", exc_info=True)
            raise RuntimeError(
                "Could not connect to the Ollama service. "
                "Please ensure the Ollama application is running on your machine."
            )
        
        logger.info(f"LLMInterface initialized successfully with model: {self.model_name}")
    
    def _ensure_model_available(self):
        """
        Checks if the specified model is available locally. If not, it attempts to download it.
        This version safely handles different response formats from the ollama library.
        """
        logger.info(f"Checking for availability of model: '{self.model_name}'...")
        try:
            response = self.client.list()
            
            # --- FIX: Use a safe method to extract model names ---
            # The .get() method avoids a KeyError if the key doesn't exist.
            # This handles variations in the ollama library's response format.
            installed_models = set()
            for model_data in response.get('models', []):
                # Safely get the name, checking for 'name' first, then 'model' as a fallback.
                name = model_data.get('name') or model_data.get('model')
                if name:
                    installed_models.add(name)
                else:
                    logger.warning(f"Could not determine name from model data: {model_data}")

            if self.model_name not in installed_models:
                logger.warning(f"Model '{self.model_name}' not found locally. Attempting to download...")
                
                pull_response = self.client.pull(self.model_name, stream=True)
                for progress in pull_response:
                    if 'status' in progress:
                        print(f"\rDownloading model... Status: {progress['status']}", end="")
                print("\nModel download complete.")
                
                logger.info(f"Model '{self.model_name}' downloaded successfully.")
            else:
                logger.info(f"Model '{self.model_name}' is available locally.")

        except Exception as e:
            logger.error(f"An error occurred while checking for or pulling the model: {e}")
            raise ConnectionError(f"Failed to verify model '{self.model_name}' with the Ollama service.")
            
    def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        """
        Generates text using the model's chat endpoint for better instruction following.
        """
        logger.debug(f"Generating text for a prompt of length {len(prompt)} chars...")
        
        try:
            start_time = time.time()
            
            response = self.client.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': temperature, 'num_predict': max_tokens}
            )
            
            if not response or 'message' not in response or 'content' not in response['message']:
                raise ValueError("Invalid response structure from Ollama chat endpoint.")
            
            generation_time = time.time() - start_time
            generated_text = response['message']['content']
            
            logger.debug(f"Generated {len(generated_text)} characters in {generation_time:.2f} seconds.")
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"An error occurred during LLM text generation: {e}", exc_info=True)
            return f"Error: LLM generation failed. Details: {str(e)}"