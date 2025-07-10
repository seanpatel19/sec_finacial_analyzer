"""
Local LLM interface for text generation
Handles communication with local language models via Ollama
"""

import logging
import time
from typing import Optional, Dict, Any

try:
    import ollama
except ImportError:
    raise ImportError("ollama package is required. Install with: pip install ollama")

logger = logging.getLogger(__name__)

class LLMInterface:
    """Interface for local LLM communication via Ollama"""
    
    def __init__(self, model_name: str = "llama2:13b"):
        """
        Initialize LLM interface
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        
        try:
            self.client = ollama.Client()
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise RuntimeError(f"Could not connect to Ollama service. Make sure Ollama is running. Error: {e}")
        
        logger.info(f"Initializing LLM interface with model: {model_name}")
        self._ensure_model_available()
        logger.info("LLM interface initialized successfully")
    
    def _ensure_model_available(self):
        """Check if model is available, download if not"""
        try:
            models_response = self.client.list()
            
            # Debug: Print the actual response structure
            logger.debug(f"Models response structure: {models_response}")
            
            # Handle different possible response structures
            if isinstance(models_response, dict) and 'models' in models_response:
                models_list = models_response['models']
            elif isinstance(models_response, list):
                models_list = models_response
            else:
                logger.error(f"Unexpected models response format: {type(models_response)}")
                raise ValueError(f"Invalid response format from Ollama: {models_response}")
            
            # Extract model names with better error handling
            model_names = []
            for model in models_list:
                if isinstance(model, dict):
                    # Handle dictionary format (older ollama library)
                    name = model.get('name') or model.get('model') or model.get('id')
                    if name:
                        model_names.append(name)
                    else:
                        logger.warning(f"Model object missing name field: {model}")
                elif hasattr(model, 'model'):
                    # Handle Model objects (newer ollama library)
                    model_names.append(model.model)
                elif hasattr(model, 'name'):
                    # Handle Model objects with 'name' attribute
                    model_names.append(model.name)
                else:
                    # Try to convert to string and extract model name
                    model_str = str(model)
                    logger.warning(f"Unexpected model format, trying to parse: {model_str}")
                    # Try to extract model name from string representation
                    import re
                    match = re.search(r"model='([^']+)'", model_str)
                    if match:
                        model_names.append(match.group(1))
                    else:
                        logger.warning(f"Could not extract model name from: {model}")
            
            logger.debug(f"Available models: {model_names}")
            
            if self.model_name not in model_names:
                logger.info(f"Model {self.model_name} not found. Downloading...")
                try:
                    self.client.pull(self.model_name)
                    logger.info(f"Model {self.model_name} downloaded successfully!")
                except Exception as pull_error:
                    logger.error(f"Failed to download model {self.model_name}: {pull_error}")
                    raise RuntimeError(f"Could not download model {self.model_name}: {pull_error}")
            else:
                logger.info(f"Model {self.model_name} is available")
                
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            # Try to continue without model validation as fallback
            logger.warning("Continuing without model validation - model may not be available")
            
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1000, 
                 stop_sequences: Optional[list] = None) -> str:
        """
        Generate text using the local LLM
        
        Args:
            prompt: Input prompt for generation
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum number of tokens to generate
            stop_sequences: List of stop sequences (optional)
            
        Returns:
            str: Generated text response
        """
        logger.debug(f"Generating text with temperature={temperature}, max_tokens={max_tokens}")
        
        # Set default stop sequences if none provided
        if stop_sequences is None:
            stop_sequences = ['Human:', 'User:']
        
        try:
            start_time = time.time()
            
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    'stop': stop_sequences
                }
            )
            
            # Validate response structure
            if not response or 'response' not in response:
                raise ValueError("Invalid response from model - missing 'response' key")
            
            generation_time = time.time() - start_time
            generated_text = response['response']
            
            logger.debug(f"Generated {len(generated_text)} characters in {generation_time:.2f} seconds")
            return generated_text
            
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return f"Error generating text: {str(e)}"
    
    def generate_with_context(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate text with system and user context
        
        Args:
            system_prompt: System context/instructions
            user_prompt: User input/question
            **kwargs: Additional generation parameters
            
        Returns:
            str: Generated response
        """
        logger.debug("Generating with system and user context")
        
        # Combine system and user prompts
        full_prompt = f"""System: {system_prompt}

User: {user_prompt}"""
        
        return self.generate(full_prompt, **kwargs)