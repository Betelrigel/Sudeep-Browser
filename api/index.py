import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

# === PROJECT ROOT (Go up from api/ to Sudeep/) ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# === FLASK APP ===
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates')
    # No static_folder → we serve images manually
)

# === SERVE IMAGES FROM ROOT ===
@app.route('/S.png')
def serve_favicon():
    return send_from_directory(BASE_DIR, 'S.png', mimetype='image/png')

@app.route('/Sudeep.png')
def serve_logo():
    return send_from_directory(BASE_DIR, 'Sudeep.png', mimetype='image/png')

# === IMPORT CREW (Safe) ===
sudeep_crew_system = None
try:
    from crew.sudeep_crew import SudeepSearchCrew
    sudeep_crew_system = SudeepSearchCrew()
    print("SudeepSearchCrew initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize SudeepSearchCrew: {e}")

# === HOME PAGE ===
@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

# === SEARCH PAGE ===
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('home'))

    results = []
    comment = ""

    if sudeep_crew_system is None:
        results = ["Ayyo, Sudeep's search system is down for maintenance, da! Try again later!"]
        comment = "System offline, no comments available, saar!"
    else:
        try:
            print(f"Searching for: '{query}'")
            crew_output = sudeep_crew_system.kickoff(query)
            results = crew_output.get('results', ["Ayyo, no results found, da! Must be the Bangalore traffic!"])
            comment = crew_output.get('comment', "Aiyoo, my agents forgot their lines, too much garam weather, macha!")
            print(f"Results: {len(results)}")
        except Exception as e:
            print68(f"Search error: {e}")
            results = [f"Ayyo, Search System crashed for '{query}', da!"]
            comment = "System error!"

    if not isinstance(results, list):
        results = [str(results)]

    return render_template('results.html', query=query, results=results, comment=comment)

# === RUN LOCALLY ===
if __name__ == '__main__':
    print("Starting Sudeep Search on http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)