from flask import Flask, request, jsonify
from flask_cors import CORS
import requests as req
import json
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

import os
from dotenv import load_dotenv
load_dotenv()
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')


@app.route('/')
def home():
    return jsonify({'status': 'UniRide backend is running'})


@app.route('/verify-id', methods=['POST'])
def verify_id():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'No image uploaded.'}), 400

        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        file = request.files['image']
        img = Image.open(file)
        text = pytesseract.image_to_string(img)
        print("OCR text extracted:", text[:100])

        name = None
        matric_no = None
        department = None

        for line in text.split('\n'):
            line = line.strip()
            if re.search(r'[A-Z]{2,}/[A-Z]{2,}/\d{4}/\d+', line):
                matric_no = line
            if 'department' in line.lower() or 'dept' in line.lower():
                department = line
            if len(line.split()) >= 2 and line.isupper() and not any(c.isdigit() for c in line):
                name = line.title()

        return jsonify({
            'name': name,
            'matric_no': matric_no,
            'department': department,
            'raw_text': text
        }), 200

    except Exception as e:
        print("ERROR in /verify-id:", str(e))
        return jsonify({'message': str(e)}), 500


@app.route('/match-ride', methods=['POST'])
def match_ride():
    try:
        data = request.get_json()
        message = data.get('message', '')
        riders = data.get('riders', [])
        print("Match ride request:", message)

        api_response = req.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 300,
                'messages': [{
                    'role': 'user',
                    'content': f'''Extract destination, time, and budget from this ride request.
Return only JSON with keys: destination, time, budget.
If any field is not mentioned return null.
Message: "{message}"'''
                }]
            }
        )

        trip = {'destination': None, 'time': None, 'budget': None}
        try:
            raw = api_response.json()['content'][0]['text']
            raw = raw.replace('```json', '').replace('```', '').strip()
            trip = json.loads(raw)
            print("Extracted trip:", trip)
        except Exception as parse_err:
            print("Could not parse Claude response:", parse_err)

        return jsonify({'trip': trip, 'drivers': riders}), 200

    except Exception as e:
        print("ERROR in /match-ride:", str(e))
        return jsonify({'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
