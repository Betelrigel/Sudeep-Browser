import os
import json
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import litellm
import logging
import re # Import the regular expression module
from typing import Dict, Optional

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
        
        # Domains to filter out (Chinese and other irrelevant domains)
        self.blocked_domains = [
            'baidu.com', 'zhihu.com', 'zhidao.baidu.com', 'tardis.bd',
            'sogou.com', 'qq.com', 'weibo.com', 'douban.com',
            '163.com', 'sina.com.cn', 'sohu.com', 'tianya.cn',
            'taobao.com', 'tmall.com', 'jd.com', 'alibaba.com'
        ]
        
        # Preferred domains for better results (optional, for ranking)
        self.preferred_domains = [
            'wikipedia.org', 'reddit.com', 'stackoverflow.com', 'quora.com',
            'youtube.com', 'medium.com', 'github.com', 'stackexchange.com'
        ]

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

    def _enhance_query(self, query: str) -> str:
        """
        Enhances the search query with context to get better, more relevant results.
        Adds Bangalore context by default unless another location is explicitly specified.
        """
        query_lower = query.lower().strip()
        
        # Check for explicit location mentions (cities other than Bangalore)
        other_cities = ['mumbai', 'delhi', 'chennai', 'hyderabad', 'pune', 'kolkata', 
                       'ahmedabad', 'surat', 'jaipur', 'lucknow', 'kanpur', 'nagpur',
                       'indore', 'thane', 'bhopal', 'visakhapatnam', 'patna', 'vadodara',
                       'gurgaon', 'faridabad', 'rajkot', 'coimbatore', 'kochi', 'trivandrum',
                       'mysore', 'mangalore', 'hubli', 'gulbarga']
        
        # Check if query mentions Bangalore/Bengaluru explicitly
        bangalore_keywords = ['bangalore', 'bengaluru', 'blr']
        has_bangalore = any(kw in query_lower for kw in bangalore_keywords)
        
        # Check if query mentions other cities explicitly
        has_other_city = any(city in query_lower for city in other_cities)
        
        # Check for state/region mentions that aren't Karnataka
        other_states = ['mumbai', 'maharashtra', 'delhi', 'chennai', 'tamil nadu', 'tamilnadu',
                       'hyderabad', 'telangana', 'andhra pradesh', 'pune', 'kolkata', 'west bengal',
                       'ahmedabad', 'gujarat', 'jaipur', 'rajasthan', 'lucknow', 'uttar pradesh',
                       'kerala', 'kochi', 'trivandrum', 'coimbatore']
        has_other_state = any(state in query_lower for state in other_states)
        
        # If another city/state is explicitly mentioned, don't add Bangalore
        if has_other_city or has_other_state:
            logging.info(f"Query explicitly mentions another location, not adding Bangalore context: '{query}'")
            return query
        
        # If Bangalore is already mentioned, keep as is (but may enhance further)
        if has_bangalore:
            # Bangalore is already in query, but we can still enhance for better results
            enhanced_query = query  # Keep original, search will naturally prioritize Bangalore
            logging.info(f"Query already mentions Bangalore: '{query}'")
            return enhanced_query
        
        # Check for general location indicators that might conflict
        location_indicators = ['near me', 'nearby', 'local', 'in my area', 'around here']
        has_location_indicator = any(indicator in query_lower for indicator in location_indicators)
        
        # Food/restaurant related queries - add Bangalore context
        food_keywords = ['idli', 'dosa', 'biryani', 'restaurant', 'food', 'cafe', 
                        'hotel', 'dining', 'eat', 'cuisine', 'menu', 'best', 'top',
                        'around', 'near', 'nearby', 'place', 'places', 'where', 'recipe',
                        'south indian', 'north indian', 'chinese', 'italian', 'breakfast',
                        'lunch', 'dinner', 'snacks', 'tiffin', 'masala', 'curry']
        
        if any(keyword in query_lower for keyword in food_keywords):
            # Add Bangalore context for food queries
            enhanced_parts = [query]
            if 'around' in query_lower or 'near' in query_lower or 'nearby' in query_lower:
                enhanced_parts.append("restaurants")
            enhanced_parts.append("Bangalore")
            enhanced_query = " ".join(enhanced_parts)
            logging.info(f"Enhanced food query with Bangalore: '{query}' -> '{enhanced_query}'")
            return enhanced_query
        
        # Recipe queries - add Bangalore/India context
        recipe_keywords = ['recipe', 'how to make', 'how to cook', 'preparation', 'cooking']
        if any(keyword in query_lower for keyword in recipe_keywords):
            enhanced_query = f"{query} Bangalore India"
            logging.info(f"Enhanced recipe query with Bangalore: '{query}' -> '{enhanced_query}'")
            return enhanced_query
        
        # Service/business queries - add Bangalore context
        service_keywords = ['restaurant', 'cafe', 'hotel', 'shop', 'store', 'mall', 'market',
                          'theater', 'cinema', 'hospital', 'clinic', 'doctor', 'dentist',
                          'gym', 'fitness', 'salon', 'spa', 'school', 'college', 'university']
        if any(keyword in query_lower for keyword in service_keywords):
            enhanced_query = f"{query} Bangalore"
            logging.info(f"Enhanced service query with Bangalore: '{query}' -> '{enhanced_query}'")
            return enhanced_query
        
        # General queries - add Bangalore context for better local relevance
        # But only for queries that seem location-relevant
        if len(query.split()) <= 4:  # Short to medium queries
            # Check if it's a "what" or "how" question that might benefit from local context
            question_words = ['what', 'where', 'how', 'which', 'when', 'who']
            is_question = any(query_lower.startswith(qw) for qw in question_words)
            
            # For questions or short queries, add Bangalore for local relevance
            if is_question or len(query.split()) <= 2:
                enhanced_query = f"{query} Bangalore"
                logging.info(f"Enhanced general query with Bangalore: '{query}' -> '{enhanced_query}'")
                return enhanced_query
        
        return query
    
    def _is_blocked_domain(self, url: str) -> bool:
        """Check if URL belongs to a blocked domain."""
        if not url or url == '#':
            return False
        
        url_lower = url.lower()
        for blocked in self.blocked_domains:
            if blocked in url_lower:
                logging.info(f"Filtered out blocked domain: {url} (contains {blocked})")
                return True
        return False
    
    def _is_relevant_result(self, url: str, body: str, query: str) -> bool:
        """
        Check if a result is relevant to the query.
        Filters out results that seem unrelated (e.g., grammar discussions for food queries).
        """
        if not url or url == '#':
            return False
        
        query_lower = query.lower()
        body_lower = body.lower() if body else ""
        url_lower = url.lower()
        
        # Extract key terms from query (remove common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                     'for', 'of', 'with', 'by', 'around', 'near', 'nearby', 'best', 'top'}
        query_terms = set(query_lower.split())
        query_terms = {term for term in query_terms if term not in stop_words and len(term) > 2}
        
        # Food-related queries should not show grammar/English learning sites
        food_keywords = ['idli', 'dosa', 'biryani', 'restaurant', 'food', 'cafe', 
                        'hotel', 'dining', 'eat', 'cuisine', 'menu', 'around']
        
        is_food_query = any(keyword in query_lower for keyword in food_keywords)
        
        if is_food_query:
            # Block grammar/English learning sites for food queries
            grammar_keywords = ['grammar', 'english learning', 'sentence structure', 
                              'best wishes', 'best regards', 'phrase meaning', 'difference between',
                              'what is', 'how to use', 'meaning of']
            if any(grammar in body_lower for grammar in grammar_keywords):
                logging.info(f"Filtered out grammar result for food query: {url}")
                return False
            
            # Block stackexchange/ell (English Language & Usage) for food queries
            if 'ell.stackexchange.com' in url_lower or 'english.stackexchange.com' in url_lower:
                logging.info(f"Filtered out English learning site for food query: {url}")
                return False
            
            # For food queries, prefer results with food-related keywords
            food_result_keywords = ['restaurant', 'food', 'cafe', 'hotel', 'dining', 'cuisine',
                                  'menu', 'dish', 'recipe', 'place', 'location', 'address',
                                  'review', 'rating', 'bangalore', 'bengaluru', 'india']
            has_food_context = any(keyword in body_lower or keyword in url_lower 
                                  for keyword in food_result_keywords)
            
            # If it's a food query but result has no food context, check if it matches query terms
            if not has_food_context:
                # Allow if it has significant query term matches
                combined_text = f"{url_lower} {body_lower}"
                matching_terms = [term for term in query_terms if term in combined_text]
                if len(matching_terms) < len(query_terms) * 0.5:  # Less than 50% match
                    logging.info(f"Filtered out non-food result for food query: {url}")
                    return False
        
        # General relevance check: ensure some query terms appear in result
        combined_text = f"{url_lower} {body_lower}"
        if query_terms:
            matching_terms = [term for term in query_terms if term in combined_text]
            # For short queries (1-2 terms), require at least 1 match
            # For longer queries, require at least 40% match
            min_matches = max(1, int(len(query_terms) * 0.4))
            if len(matching_terms) < min_matches:
                logging.debug(f"Low term match for {url}: {len(matching_terms)}/{len(query_terms)} terms")
                # Don't filter out completely, just log - let domain filtering handle it
        
        return True
    
    def _extract_metadata(self, body: str, title: str = "") -> Dict[str, Optional[str]]:
        """
        Extract metadata (rating, reviews, duration) from result body and title.
        Returns a dictionary with rating, reviews, and duration if found.
        """
        metadata = {'rating': None, 'reviews': None, 'duration': None}
        combined_text = f"{title} {body}".lower()
        
        # Extract rating (look for patterns like "5.0", "4.5 stars", "rated 5", etc.)
        rating_patterns = [
            r'(\d+\.?\d*)\s*(?:star|rating|rated)',
            r'rating[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*out of',
            r'(\d+\.?\d*)\s*★',
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                try:
                    rating_val = float(match.group(1))
                    if 0 <= rating_val <= 5:  # Valid rating range
                        metadata['rating'] = f"{rating_val:.1f}"
                        break
                except (ValueError, IndexError):
                    continue
        
        # Extract reviews (look for patterns like "(2)", "2 reviews", "2 ratings")
        review_patterns = [
            r'\((\d+)\)',  # (2)
            r'(\d+)\s*review',
            r'(\d+)\s*rating',
            r'based on (\d+)',
        ]
        for pattern in review_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                try:
                    reviews_val = int(match.group(1))
                    if reviews_val > 0:
                        metadata['reviews'] = str(reviews_val)
                        break
                except (ValueError, IndexError):
                    continue
        
        # Extract duration (look for patterns like "12 hrs 10 mins", "2 hours", "30 minutes")
        duration_patterns = [
            r'(\d+\s*(?:hrs?|hours?)\s*(?:\d+\s*(?:mins?|minutes?))?)',  # "12 hrs 10 mins"
            r'(\d+\s*(?:mins?|minutes?))',  # "30 mins"
            r'(\d+\s*(?:hrs?|hours?))',  # "2 hrs"
            r'time[:\s]+(\d+[^.]*)',  # "time: 2 hours"
            r'duration[:\s]+(\d+[^.]*)',  # "duration: 30 mins"
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                duration_str = match.group(1).strip()
                # Clean up the duration string
                duration_str = re.sub(r'\s+', ' ', duration_str)
                if len(duration_str) < 30:  # Reasonable length
                    metadata['duration'] = duration_str
                    break
        
        return metadata
    
    def _clean_result_string(self, result_string: str) -> str:
        """
        Removes leading numbering (e.g., "1. ", "1. #", "2. "), markdown formatting (asterisks),
        and leading dashes from a string. Handles cases where the URL or snippet might be missing.
        """
        if not result_string:
            return ""

        # First, remove markdown formatting (asterisks for bold/italic)
        cleaned_string = re.sub(r'\*\*?', '', result_string)
        
        # Remove leading numbering, dots, spaces, hashes, and dashes
        # This regex looks for:
        # - Start of the string (^)
        # - Zero or more digits (\d*)
        # - A dot (\.?) (optional dot)
        # - Zero or more spaces, hashes, or dashes ([ #-]*)
        # - Followed by the actual content
        cleaned_string = re.sub(r'^\d*\.?[ #-]*', '', cleaned_string.strip())
        
        # Also remove any leading dash that might remain after the above
        cleaned_string = cleaned_string.lstrip('-').strip()
        
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
            
            # Try multiple search strategies to ensure we get at least 5 results
            # Prioritize India region searches first (which will favor Bangalore results)
            enhanced_query = self._enhance_query(query)
            search_strategies = [
                {'query': enhanced_query, 'region': 'in-en', 'max_results': 50, 'name': 'enhanced_india_region'},
                {'query': query, 'region': 'in-en', 'max_results': 50, 'name': 'original_india_region'},
                {'query': enhanced_query, 'region': 'wt-wt', 'max_results': 50, 'name': 'enhanced_worldwide'},
                {'query': query, 'region': None, 'max_results': 50, 'name': 'original_no_region'},
            ]
            
            all_filtered_results = []
            
            for strategy in search_strategies:
                try:
                    with DDGS() as ddgs:
                        try:
                            if strategy['region']:
                                ddgs_results_iterator = ddgs.text(
                                    strategy['query'],
                                    max_results=strategy['max_results'],
                                    region=strategy['region'],
                                    safesearch='moderate'
                                )
                            else:
                                ddgs_results_iterator = ddgs.text(
                                    strategy['query'],
                                    max_results=strategy['max_results']
                                )
                        except TypeError:
                            # Fallback if region/safesearch parameters not supported
                            ddgs_results_iterator = ddgs.text(
                                strategy['query'],
                                max_results=strategy['max_results']
                            )
                        
                        ddgs_results = list(ddgs_results_iterator) if ddgs_results_iterator else []
                        
                        if ddgs_results:
                            # Apply very lenient filtering - prioritize getting results over perfect relevance
                            parsed = []
                            for r in ddgs_results:
                                url = r.get('href', '#')
                                title = r.get('title', '')
                                body = r.get('body', 'No snippet available, da!')
                                
                                # Skip invalid URLs
                                if not url or url == '#':
                                    continue
                                
                                # Only filter blocked domains (Chinese sites) - this is the main filter
                                if self._is_blocked_domain(url):
                                    continue
                                
                                # Very minimal relevance filtering - only for extreme mismatches
                                query_lower = query.lower()
                                is_food_query = any(kw in query_lower for kw in ['idli', 'dosa', 'biryani', 'restaurant', 'food', 'cafe', 'hotel', 'dining', 'recipe'])
                                
                                if is_food_query:
                                    # Only filter if it's clearly a grammar/English learning site AND has no food context
                                    body_lower = body.lower() if body else ""
                                    title_lower = title.lower() if title else ""
                                    url_lower = url.lower()
                                    combined_text_lower = f"{title_lower} {body_lower}"
                                    
                                    # Check if it's an English learning site
                                    is_english_site = 'ell.stackexchange.com' in url_lower or 'english.stackexchange.com' in url_lower
                                    
                                    if is_english_site:
                                        # Only skip if it has no food-related content at all
                                        has_food_context = any(food_kw in combined_text_lower for food_kw in ['food', 'restaurant', 'dish', 'cuisine', 'menu', 'eat', 'dining', 'cafe', 'hotel', 'recipe', 'cook', 'ingredient'])
                                        if not has_food_context:
                                            # Double check - if the body contains grammar keywords and NO food keywords, skip it
                                            has_grammar_keywords = any(grammar_kw in combined_text_lower for grammar_kw in ['best wishes', 'best regards', 'phrase meaning', 'difference between', 'grammar'])
                                            if has_grammar_keywords:
                                                continue
                                
                                # Check for Bangalore/Bengaluru relevance (highest priority)
                                bangalore_keywords = ['bangalore', 'bengaluru', 'blr', 'karnataka']
                                has_bangalore_context = any(kw in body.lower() or kw in title.lower() or kw in url.lower() 
                                                           for kw in bangalore_keywords)
                                
                                # Check for other India locations (medium priority)
                                other_india_keywords = ['india', 'indian', 'mumbai', 'delhi', 'chennai', 
                                                       'hyderabad', 'kolkata', 'pune', 'kerala', 'tamil']
                                has_other_india_context = any(kw in body.lower() or kw in title.lower() or kw in url.lower() 
                                                             for kw in other_india_keywords) if not has_bangalore_context else False
                                
                                # Determine relevance level: 2=Bangalore, 1=Other India, 0=Other
                                relevance_level = '2' if has_bangalore_context else ('1' if has_other_india_context else '0')
                                
                                # Extract metadata (rating, reviews, duration)
                                metadata = self._extract_metadata(body, title)
                                
                                # Create structured result: title|url|body|relevance_level|rating|reviews|duration
                                # Format: "title|url|body|relevance_level|rating|reviews|duration"
                                # relevance_level: 2=Bangalore, 1=Other India, 0=Other
                                if not title:
                                    # If no title, use URL domain as title
                                    domain = url.replace('https://', '').replace('http://', '').split('/')[0]
                                    title = domain
                                
                                rating_str = metadata.get('rating', '')
                                reviews_str = metadata.get('reviews', '')
                                duration_str = metadata.get('duration', '')
                                
                                result_entry = f"{title}|{url}|{body}|{relevance_level}|{rating_str}|{reviews_str}|{duration_str}"
                                
                                # Check for duplicates using URL
                                url_part = url.lower().replace('https://', '').replace('http://', '').rstrip('/')
                                is_duplicate = any(existing.split('|')[1].lower().replace('https://', '').replace('http://', '').rstrip('/') == url_part 
                                                  for existing in all_filtered_results if '|' in existing)
                                
                                if not is_duplicate:
                                    parsed.append(result_entry)
                            
                            all_filtered_results.extend(parsed)
                            logging.info(f"Strategy '{strategy['name']}' found {len(parsed)} new results. Total so far: {len(all_filtered_results)}")
                            
                            # If we have enough results (10+), stop trying more strategies
                            if len(all_filtered_results) >= 10:
                                break
                
                except Exception as e:
                    logging.warning(f"Search strategy '{strategy['name']}' failed: {e}")
                    continue
            
            # Remove duplicates and sort by relevance (Bangalore first, then other India, then others)
            seen_urls = set()
            final_results = []
            bangalore_results = []
            other_india_results = []
            other_results = []
            
            for result in all_filtered_results:
                if '|' in result:
                    # New structured format: title|url|body|relevance_level|rating|reviews|duration
                    parts = result.split('|')
                    if len(parts) >= 3:
                        title, url, body = parts[0], parts[1], parts[2]
                        relevance_level = parts[3] if len(parts) > 3 else '0'
                        
                        # Extract metadata if present
                        rating = parts[4] if len(parts) > 4 and parts[4] else ''
                        reviews = parts[5] if len(parts) > 5 and parts[5] else ''
                        duration = parts[6] if len(parts) > 6 and parts[6] else ''
                        
                        # Normalize URL for deduplication
                        url_part_normalized = url.lower().replace('https://', '').replace('http://', '').rstrip('/')
                        
                        if url_part_normalized and url_part_normalized not in seen_urls:
                            seen_urls.add(url_part_normalized)
                            # Reconstruct result with metadata: title|url|body|rating|reviews|duration
                            result_entry = f"{title}|{url}|{body}|{rating}|{reviews}|{duration}"
                            
                            # Sort by relevance level: 2=Bangalore, 1=Other India, 0=Other
                            if relevance_level == '2':
                                bangalore_results.append(result_entry)
                            elif relevance_level == '1':
                                other_india_results.append(result_entry)
                            else:
                                other_results.append(result_entry)
                else:
                    # Legacy format: url - body (for backward compatibility)
                    url_part = result.split(' - ')[0] if ' - ' in result else result
                    url_part_normalized = url_part.lower().replace('https://', '').replace('http://', '').rstrip('/')
                    
                    if url_part_normalized and url_part_normalized not in seen_urls:
                        seen_urls.add(url_part_normalized)
                        # Check if legacy result has Bangalore context
                        result_lower = result.lower()
                        if any(kw in result_lower for kw in ['bangalore', 'bengaluru', 'blr']):
                            bangalore_results.append(result)
                        elif any(kw in result_lower for kw in ['india', 'indian', 'mumbai', 'delhi', 'chennai']):
                            other_india_results.append(result)
                        else:
                            other_results.append(result)
            
            # Sort: Bangalore results first, then other India results, then others
            final_results = bangalore_results + other_india_results + other_results
            logging.info(f"Results sorted: {len(bangalore_results)} Bangalore, {len(other_india_results)} other India, {len(other_results)} others")
            
            # Prioritize getting at least 5 results
            if len(final_results) >= 5:
                logging.info(f"DDGS search successful for '{query}'. Found {len(final_results)} results after filtering.")
                return final_results[:10]
            elif len(final_results) > 0:
                # If we have some results (even if less than 5), return them
                # This ensures we show results instead of error messages when possible
                logging.info(f"DDGS search found {len(final_results)} results for '{query}' (showing available results).")
                return final_results
            else:
                # Only show error if we truly got no results after all strategies
                logging.warning(f"DDGS returned no results for query '{query}' after trying all strategies.")
                # Check if query is extremely vague (very short, just numbers, or only symbols)
                query_stripped = query.strip()
                if len(query_stripped) < 2:
                    return [f"Ayyo, '{query}' is too vague, macha! Try searching for something more specific, da!"]
                elif query_stripped.isdigit() or not any(c.isalnum() for c in query_stripped):
                    return [f"Ayyo, '{query}' doesn't make sense, da! Try searching for actual words, yaar!"]
                else:
                    return [f"No results found for '{query}', da! Try a different search term, yaar!"]

    def translate_results(self, results: list, query: str):
        """Translates search results into Bangalore slang using LiteLLM. Preserves structured format."""
        if not self.groq_api_key:
            logging.warning("GROQ API key not available. Skipping translation.")
            return results
            
        # Check if results contain error messages - skip translation for these
        # Error messages typically start with "Ayyo", "No results", or "No specific results"
        error_indicators = ["Ayyo", "No results", "No specific results", "No valid results"]
        if not results or any(any(indicator in r for indicator in error_indicators) for r in results):
            logging.info("Skipping translation for error messages or empty results.")
            return results
        
        # Check if results are in new structured format (title|url|body)
        is_structured = any('|' in r for r in results)
        
        if not is_structured:
            # Legacy format - translate as before but return in structured format
            try:
                input_text = "\n".join(results)
                logging.info(f"Translating {len(results)} legacy format results for query '{query}'...")
                
                model_name = "groq/llama-3.1-8b-instant" 
                
                response = litellm.completion(
                    model=model_name,
                    api_key=self.groq_api_key,
                    messages=[
                        {"role": "system", "content": "You are a Bangalore techie translator. Translate these search results into Bangalore English with slang like 'da', 'macha', 'ayyo', 'garam', 'saar', 'yaar'. Keep the format as 'title|url|description' for each result. Output ONLY the translated lines, no extra text."},
                        {"role": "user", "content": f"Query: '{query}'. Results to translate:\n{input_text}"}
                    ],
                    temperature=0.9,
                    max_tokens=800,
                )
                
                translated_content = response.choices[0].message.content.strip()
                translated_lines = translated_content.split('\n')
                
                cleaned_translated_lines = []
                for line in translated_lines:
                    if line.strip() and '|' in line:
                        cleaned_line = self._clean_result_string(line)
                        if cleaned_line:
                            cleaned_translated_lines.append(cleaned_line)
                
                if cleaned_translated_lines:
                    logging.info("Translation successful for legacy format.")
                    return cleaned_translated_lines
            except Exception as e:
                logging.error(f"Translation error for legacy format: {e}")
            
            return results
        
        # New structured format - translate title and body, keep URL intact
        try:
            # Prepare results for translation
            results_to_translate = []
            for result in results:
                if '|' in result:
                    parts = result.split('|', 2)
                    if len(parts) >= 3:
                        title, url, body = parts[0], parts[1], parts[2]
                        results_to_translate.append(f"Title: {title}\nBody: {body}\nURL: {url}")
            
            if not results_to_translate:
                return results
            
            input_text = "\n\n---\n\n".join(results_to_translate)
            logging.info(f"Translating {len(results_to_translate)} structured results for query '{query}'...")
            
            model_name = "groq/llama-3.1-8b-instant" 
            
            response = litellm.completion(
                model=model_name,
                api_key=self.groq_api_key,
                messages=[
                    {"role": "system", "content": "You are a Bangalore techie translator. Translate the titles and descriptions into Bangalore English with slang like 'da', 'macha', 'ayyo', 'garam', 'saar', 'yaar'. Keep URLs unchanged. For each result, output in format: title|url|description. Output ONLY the translated results, one per line, no extra text or labels."},
                    {"role": "user", "content": f"Query: '{query}'. Results to translate:\n{input_text}"}
                ],
                temperature=0.9,
                max_tokens=1000,
            )
            
            translated_content = response.choices[0].message.content.strip()
            translated_lines = translated_content.split('\n')
            
            # Parse translated results back to structured format
            # Match translated results with original results to preserve metadata and relevance
            cleaned_translated_lines = []
            original_results_dict = {}
            for result in results:
                if '|' in result:
                    parts = result.split('|')
                    if len(parts) >= 3:
                        url = parts[1]
                        # Store all metadata from original (rating, reviews, duration)
                        # Note: relevance_level is not stored as it's determined by content, not preserved
                        original_results_dict[url] = {
                            'rating': parts[3] if len(parts) > 3 and parts[3] else '',
                            'reviews': parts[4] if len(parts) > 4 and parts[4] else '',
                            'duration': parts[5] if len(parts) > 5 and parts[5] else ''
                        }
            
            for line in translated_lines:
                if line.strip() and '|' in line:
                    cleaned_line = self._clean_result_string(line)
                    # Verify it has at least 3 parts (title|url|body)
                    parts = cleaned_line.split('|')
                    if len(parts) >= 3:
                        title, url, body = parts[0], parts[1], parts[2]
                        # Restore metadata from original result
                        metadata = original_results_dict.get(url, {})
                        rating = metadata.get('rating', '')
                        reviews = metadata.get('reviews', '')
                        duration = metadata.get('duration', '')
                        # Reconstruct with metadata (relevance will be recalculated if needed)
                        result_with_metadata = f"{title}|{url}|{body}|{rating}|{reviews}|{duration}"
                        cleaned_translated_lines.append(result_with_metadata)
            
            if cleaned_translated_lines and len(cleaned_translated_lines) >= len(results) * 0.7:
                # If we got at least 70% of results translated, use them
                logging.info(f"Translation successful: {len(cleaned_translated_lines)}/{len(results)} results translated.")
                return cleaned_translated_lines
            else:
                logging.warning("Translation returned insufficient results. Returning original results.")
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
            
            # Check if results contain error messages - skip translation for these
            # translate_results will also check, but we do it here for clarity
            error_indicators = ["Ayyo", "No results", "No specific results", "No valid results"]
            is_error = isinstance(raw_results, list) and raw_results and any(
                any(indicator in r for indicator in error_indicators) for r in raw_results
            )
            
            if is_error:
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