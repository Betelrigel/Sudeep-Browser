import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

# === PROJECT ROOT ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# === FLASK APP ===
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

# === SERVE IMAGES ===
@app.route('/S.png')
def serve_favicon():
    return send_from_directory(BASE_DIR, 'S.png', mimetype='image/png')

@app.route('/Sudeep.png')
def serve_logo():
    return send_from_directory(BASE_DIR, 'Sudeep.png', mimetype='image/png')

# === IMPORT CREW ===
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
    city = request.args.get('city', 'Bangalore').strip()  # GET CITY FROM URL
    lucky = request.args.get('lucky') == '1'

    if not query:
        return redirect(url_for('home'))

    results = []
    comment = ""
    final_city = "Bangalore"

    if sudeep_crew_system is None:
        results = ["Ayyo, Sudeep's search system is down for maintenance, da!"]
        comment = "System offline, no comments available, saar!"
    else:
        try:
            print(f"Searching: '{query}' | City: {city}")
            crew_output = sudeep_crew_system.kickoff(query, city=city)  # PASS CITY!
            results = crew_output.get('results', [])
            comment = crew_output.get('comment', "Ayyo, no comment da!")
            final_city = crew_output.get('city', city)
            print(f"Results: {len(results)} | Final City: {final_city}")
        except Exception as e:
            print(f"Search error: {e}")
            results = [f"Ayyo, search crashed for '{query}', da!"]
            comment = "System error, macha!"

    if not isinstance(results, list):
        results = [str(results)]

    return render_template(
        'results.html',
        query=query,
        results=results,
        comment=comment,
        city=final_city,   # PASS CITY
        lucky=lucky        # For Lucky redirect
    )

# === RUN ===
if __name__ == '__main__':
    print("Sudeep Search → http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)