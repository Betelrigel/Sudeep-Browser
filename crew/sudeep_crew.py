import os
import json
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import litellm
import logging
import re # Import the regular expression module

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
os.environ['LITELLM_LOG'] = 'INFO' # LITELLM logs

class SudeepSearchCrew:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logging.error("GROQ_API_KEY not set in .env file. LLM features will not work.")
            # Removed the raise ValueError here to allow the script to run even without API key,
            # but LLM features will be disabled as intended.
            # raise ValueError("GROQ_API_KEY not set in .env file. LLM functionality requires it.")
        else:
            logging.info(f"Initialized with Groq API Key starting with: {self.groq_api_key[:4]}...")

    def _text_extract_json(self, query: str):
        """
        Fetches specific structured data (e.g., from a local JSON or API).
        Returns a dictionary with a 'results' key if successful.
        Returns None if the query is not found, data is invalid, or an error occurs.
        """
        logging.info(f"Attempting specific JSON extraction for query: '{query}'")
        try:
            # --- START: Replace this section with your actual data fetching logic ---
            # This is where you would load a JSON, call an API, etc.
            
            # For simulation purposes:
            if query.lower() == "cpu":
                logging.warning("Simulating 'subsection not found' error for 'cpu'.")
                # Raising an error here is intentional to test the fallback.
                # The caller (fetch_results) MUST catch this.
                raise ValueError("subsection not found")
            
            elif query.lower() == "food":
                logging.info("Simulating successful data fetch for 'food'.")
                return {
                    "results": [
                        {"href": "https://example.com/biryani", "body": "Best biryani in town, da!"},
                        {"href": "https://example.com/dosa", "body": "Authentic masala dosa, super macha!"}
                    ]
                }
            else:
                logging.info(f"No specific JSON data found for query: '{query}'.")
                return None # Return None if the query doesn't match any specific data

            # --- END: Replace this section ---

        except ValueError as e:
            # Catch specific ValueErrors from your logic (like 'subsection not found')
            logging.error(f"ValueError during specific data extraction for '{query}': {e}")
            return None # Crucially, return None on specific known errors
        except Exception as e:
            # Catch any other unexpected errors (e.g., network issues, JSON parsing errors)
            logging.error(f"Unexpected error during specific data extraction for '{query}': {e}")
            return None # Return None for any other unexpected errors

    def _clean_result_string(self, result_string: str) -> str:
        """
        Removes leading numbering (e.g., "1. ", "1. #", "2. ") from a string.
        Handles cases where the URL or snippet might be missing.
        """
        if not result_string:
            return ""

        # This regex looks for:
        # - Start of the string (^)
        # - Zero or more digits (\d*)
        # - A dot (\.?) (optional dot)
        # - Zero or more spaces or hashes ([ #]*)
        # - Followed by the actual content
        # It then returns the matched content after these leading characters.
        cleaned_string = re.sub(r'^\d*\.?[ #]*', '', result_string.strip())
        return cleaned_string

    def fetch_results(self, query: str):
        """
        Fetches search results. Tries specific JSON extraction first,
        then falls back to DDGS. Returns a list of formatted strings
        or an error message list. ALL results are cleaned of leading numbers.
        """
        specific_data = None  # Initialize to None
        try:
            specific_data = self._text_extract_json(query)
        except Exception as e:
            logging.error(f"Error during specific data extraction for '{query}': {e}. Falling back to DDGS.")
            specific_data = None # Ensure it's None if an error occurred

        if specific_data and isinstance(specific_data, dict) and specific_data.get('results'):
            logging.info(f"Using specific JSON results for '{query}'.")
            parsed_results = []
            for item in specific_data['results']:
                url = item.get('href', '#')
                body = item.get('body', 'No description available, da!')
                # Combine URL and body, then clean the entire resulting string
                combined_result = f"{url} - {body}"
                cleaned_result = self._clean_result_string(combined_result)
                parsed_results.append(cleaned_result)
            
            # Filter out any empty strings that might result from cleaning
            final_results = [r for r in parsed_results if r and r != '-' and r != ' - ']
            
            if final_results:
                return final_results[:10]
            else:
                return [f"No specific results found for '{query}', da! (Empty list from source after cleaning)"]
        else:
            # Fallback to DDGS if specific extraction failed (returned None) or returned no valid results
            logging.info(f"Specific data not found or invalid for '{query}'. Falling back to DDGS.")
            try:
                with DDGS() as ddgs:
                    ddgs_results_iterator = ddgs.text(query, max_results=10)
                    ddgs_results = list(ddgs_results_iterator) if ddgs_results_iterator else []
                
                if ddgs_results:
                    parsed = []
                    for r in ddgs_results:
                        url = r.get('href', '#')
                        body = r.get('body', 'No snippet available, da!')
                        # Combine URL and body, then clean the entire resulting string
                        combined_result = f"{url} - {body}"
                        cleaned_result = self._clean_result_string(combined_result)
                        parsed.append(cleaned_result)
                        
                    # Filter out any empty strings that might result from cleaning
                    final_results = [r for r in parsed if r and r != '-' and r != ' - ']
                    
                    if final_results:
                        logging.info(f"DDGS search successful for '{query}'. Found {len(final_results)} results after cleaning.")
                        return final_results[:10]
                    else:
                        logging.warning(f"DDGS returned results for '{query}', but all were empty after cleaning.")
                        return [f"No valid results found from DDGS for '{query}', da! (All results were empty after cleaning)"]
                else:
                    logging.warning(f"DDGS returned no results for query '{query}'.")
                    return [f"No results found from DDGS for '{query}', da!"]
            except Exception as e:
                logging.error(f"DDGS fetch error for query '{query}': {e}")
                return [f"Ayyo, DDGS search failed for '{query}', da! The search engine is taking a chai break, macha!"]

    def translate_results(self, results: list, query: str):
        """Translates search results into Bangalore slang using LiteLLM."""
        if not self.groq_api_key:
            logging.warning("GROQ API key not available. Skipping translation.")
            return results
            
        # Check if the first result looks like a generic error message (starts with "Ayyo")
        # This ensures we don't try to translate error messages returned by fetch_results
        if not results or any(r.startswith("Ayyo") for r in results):
            logging.info("Skipping translation for error messages or empty results.")
            return results
            
        try:
            input_text = "\n".join(results)
            logging.info(f"Translating {len(results)} results for query '{query}'...")
            
            model_name = "groq/llama-3.1-8b-instant" 
            
            response = litellm.completion(
                model=model_name,
                api_key=self.groq_api_key,
                messages=[
                    {"role": "system", "content": "You are a Bangalore techie translator. Turn these full search result lines (URL - snippet) into super strong Bangalore English with heavy slang like 'da', 'macha', 'ayyo', 'garam', 'saar', 'yaar'. Make both the title-like part (before '-') and description (after '-') sound like a witty, sarcastic Bangalore techie chatting with a friend. Output ONLY the translated lines, each as 'URL - translated title/description', no extra text or labels. If a URL is not provided or invalid, use '#' for the URL. If the snippet is missing, use a placeholder. Ensure each line is properly formatted."},
                    {"role": "user", "content": f"Query: '{query}'. Results to translate:\n{input_text}"}
                ],
                temperature=0.9,
                max_tokens=500,
            )
            
            translated_content = response.choices[0].message.content.strip()
            translated_lines = translated_content.split('\n')
            
            # Clean the translated lines to ensure no numbering persists from LLM output
            cleaned_translated_lines = []
            for line in translated_lines:
                if line.strip():
                    # Use the same cleaning logic as in fetch_results
                    cleaned_line = self._clean_result_string(line)
                    cleaned_translated_lines.append(cleaned_line)
            
            # Filter out any empty strings that might result from cleaning
            final_translated_lines = [r for r in cleaned_translated_lines if r and r != '-' and r != ' - ']

            if final_translated_lines:
                logging.info("Translation successful and cleaned.")
                return final_translated_lines
            else:
                logging.warning("Translation returned empty or only whitespace lines after cleaning. Returning original results.")
                return results

        except Exception as e:
            logging.error(f"Translation error for query '{query}': {e}")
            return results

    def generate_comment(self, query: str):
        """Generates a sarcastic Bangalore techie comment using LiteLLM."""
        if not self.groq_api_key:
            logging.warning("GROQ API key not available. Returning default comment.")
            return "Ayyo, comment generation failed, macha! Need that API key!"
            
        try:
            logging.info(f"Generating comment for query: '{query}'")
            model_name = "groq/llama-3.1-8b-instant"
            
            response = litellm.completion(
                model=model_name,
                api_key=self.groq_api_key,
                messages=[
                    {"role": "system", "content": "You are Sudeep, a sarcastic Bangalore techie. Generate one single, funny, sarcastic comment roasting the person searching, in strong Bangalore English with heavy slang like 'da', 'macha', 'ayyo', 'garam', 'saar', 'yaar'. Theme it around high temperature and techie life, keep it short, witty, and roast the searcher directly, no numbers or lists. If the search query is technical, roast them for searching something obvious or basic. If it's about food, roast them for being hungry or ordering."},
                    {"role": "user", "content": f"Query: '{query}'"}
                ],
                temperature=0.9,
                max_tokens=100,
            )
            comment = response.choices[0].message.content.strip()
            if comment:
                logging.info(f"Generated comment: {comment}")
            else:
                logging.warning("LLM returned an empty comment.")
                comment = "Ayyo, my comment generator took a nap in this garam weather!" # Fallback comment
            return comment
        except Exception as e:
            logging.error(f"Comment generation failed for query '{query}': {e}")
            return "Ayyo, comment generation failed in this garam heat, da!"

    def kickoff(self, query: str):
        """
        Main function to orchestrate the search process.
        Generates a comment, fetches results (handling specific extraction vs. DDGS fallback),
        translates results if possible, and returns a structured response.
        Ensures a dictionary with 'results' and 'comment' is always returned.
        """
        logging.info(f"--- Starting search kickoff for query: '{query}' ---")
        
        comment = ""
        try:
            comment = self.generate_comment(query)
        except Exception as e:
            logging.error(f"Error generating comment during kickoff: {e}")
            comment = "Ayyo, couldn't even generate a comment, da! System totally garam!"
            
        results = []
        try:
            # fetch_results now handles cleaning of numbering
            raw_results = self.fetch_results(query) 
            
            # Check if the first result looks like a generic error message (starts with "Ayyo")
            # If it is an error, we don't attempt translation.
            if isinstance(raw_results, list) and raw_results and raw_results[0].startswith("Ayyo"):
                logging.info("Skipping translation for error results.")
                results = raw_results
            else:
                # translate_results also cleans its output as a safeguard
                translated_results = self.translate_results(raw_results, query) 
                results = translated_results

        except Exception as e:
            # This catches unexpected errors *after* fetch_results returns (e.g., during translate)
            logging.error(f"Unexpected error during fetch/translate for '{query}': {e}")
            results = [f"Ayyo, something went wrong fetching/translating results for '{query}', da! Server's confused!"]

        response = {
            "results": results if isinstance(results, list) else [str(results)],
            "comment": comment
        }
        
        logging.info(f"--- Kickoff finished for '{query}'. Returning response with {len(response.get('results', []))} translated/fallback results. ---")
        
        return response

if __name__ == "__main__":
    print("\n--- Testing SudeepSearchCrew directly ---")
    
    print("\n--- Testing with 'food' ---")
    try:
        crew_food = SudeepSearchCrew()
        output_food = crew_food.kickoff("food")
        print(f"Output for 'food': {json.dumps(output_food, indent=2)}")
    except ValueError as e: # This catch is now less critical as init doesn't raise
        print(f"Could not initialize crew for 'food' test: {e}")

    print("\n--- Testing with 'cpu' ---")
    try:
        crew_cpu = SudeepSearchCrew()
        output_cpu = crew_cpu.kickoff("cpu")
        print(f"Output for 'cpu': {json.dumps(output_cpu, indent=2)}")
    except ValueError as e:
        print(f"Could not initialize crew for 'cpu' test: {e}")

    print("\n--- Testing with 'garam masala' ---")
    try:
        crew_masala = SudeepSearchCrew()
        output_masala = crew_masala.kickoff("garam masala")
        print(f"Output for 'garam masala': {json.dumps(output_masala, indent=2)}")
    except ValueError as e:
        print(f"Could not initialize crew for 'garam masala' test: {e}")

    print("\n--- Testing with 'nonexistentquery12345' ---")
    try:
        crew_nonexistent = SudeepSearchCrew()
        output_nonexistent = crew_nonexistent.kickoff("nonexistentquery12345")
        print(f"Output for 'nonexistentquery12345': {json.dumps(output_nonexistent, indent=2)}")
    except ValueError as e:
        print(f"Could not initialize crew for 'nonexistentquery12345' test: {e}")