import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

# Make sure this path is correct relative to your project structure
from crew.sudeep_crew import SudeepSearchCrew

# === SET BASE DIRECTORY ===
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# === FLASK APP SETUP (NO static_folder) ===
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, '..', 'templates')
    # No static_folder → we serve images manually
)

# === SERVE IMAGES FROM ROOT ===
@app.route('/S.png')
def serve_favicon():
    return send_from_directory(BASE_DIR, 'S.png')

@app.route('/Sudeep.png')
def serve_logo():
    return send_from_directory(BASE_DIR, 'Sudeep.png')

# Initialize your CrewAI system
sudeep_crew_system = None
try:
    sudeep_crew_system = SudeepSearchCrew()
    print("SudeepSearchCrew initialized successfully.")
except ValueError as e:
    print(f"CRITICAL ERROR: Failed to initialize SudeepSearchCrew: {e}")

@app.route('/', methods=['GET'])
def home():
    """Renders the main Sudeep search homepage."""
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    """Handles the search query, calls the CrewAI system, and displays results."""
    query = request.args.get('q', '').strip()

    if not query:
        return redirect(url_for('home'))

    results = []
    comment = ""

    if sudeep_crew_system is None:
        print("SudeepSearchCrew system is not initialized. Cannot perform search.")
        results = ["Ayyo, Sudeep's search system is down for maintenance, da! Try again later!"]
        comment = "System offline, no comments available, saar!"
    else:
        try:
            print(f"Initiating kickoff for query: '{query}'")
            crew_output = sudeep_crew_system.kickoff(query)
            
            results = crew_output.get('results', ["Ayyo, no results found, da! Must be the Bangalore traffic!"])
            comment = crew_output.get('comment', "Aiyoo, my agents forgot their lines, too much garam weather, macha!")
            
            print(f"Crew kickoff successful for '{query}'. Results count: {len(results)}")

        except Exception as e:
            print(f"CRITICAL ERROR running CrewAI kickoff for query '{query}': {e}")
            results = [f"Ayyo, Search System crashed badly for '{query}', da! Try again after a long chai break!"]
            comment = "System offline, no comments available, saar!"

    if not isinstance(results, list):
        results = [str(results)]

    return render_template('results.html', query=query, results=results, comment=comment)

# For local testing
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)