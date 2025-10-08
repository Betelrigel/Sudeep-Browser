import os
from flask import Flask, render_template, request, redirect, url_for
# Make sure this path is correct relative to your project structure
from crew.sudeep_crew import SudeepSearchCrew

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Initialize your CrewAI system
# Moved initialization to within a try-except to handle potential config errors
sudeep_crew_system = None
try:
    sudeep_crew_system = SudeepSearchCrew()
    print("SudeepSearchCrew initialized successfully.")
except ValueError as e:
    print(f"CRITICAL ERROR: Failed to initialize SudeepSearchCrew: {e}")
    # You might want to set a flag or have a way to disable search functionality
    # For now, we'll let it proceed, but searches will fail gracefully.

@app.route('/', methods=['GET'])
def home():
    """Renders the main Sudeep search homepage."""
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    """Handles the search query, calls the CrewAI system, and displays results."""
    query = request.args.get('q', '').strip()

    if not query:
        return redirect(url_for('home')) # Redirect to home if query is empty

    results = []
    comment = ""

    if sudeep_crew_system is None:
        # Handle case where CrewAI system failed to initialize
        print("SudeepSearchCrew system is not initialized. Cannot perform search.")
        results = ["Ayyo, Sudeep's search system is down for maintenance, da! Try again later!"]
        comment = "System offline, no comments available, saar!"
    else:
        try:
            print(f"Initiating kickoff for query: '{query}'")
            crew_output = sudeep_crew_system.kickoff(query)
            
            # The kickoff function is designed to always return a dict with 'results' and 'comment'
            results = crew_output.get('results', ["Ayyo, no results found, da! Must be the Bangalore traffic!"])
            comment = crew_output.get('comment', "Aiyoo, my agents forgot their lines, too much garam weather, macha!")
            
            print(f"Crew kickoff successful for '{query}'. Results count: {len(results)}")

        except Exception as e:
            # This catches errors if kickoff itself fails unexpectedly (e.g., if crew_output is not a dict)
            print(f"CRITICAL ERROR running CrewAI kickoff for query '{query}': {e}")
            # Provide a very basic, direct error message that won't be translated
            results = [f"Ayyo, Search System crashed badly for '{query}', da! Try again after a long chai break!"]
            comment = "System offline, no comments available, saar!"

    # Ensure results is always a list, even if empty or a single item
    if not isinstance(results, list):
        results = [str(results)] # Convert to list if it's not already

    return render_template('results.html', query=query, results=results, comment=comment)

# For local testing convenience during development
if __name__ == '__main__':
    print("Starting Flask server...")
    # Use debug=False for production, True for development
    # Bind to 0.0.0.0 to make it accessible on your network, not just localhost
    app.run(debug=True, host='0.0.0.0', port=5000)