from flask import Flask, request, jsonify
from flask_cors import CORS
import requests as req
import json
import re
import os
import base64
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')


@app.route('/')
def home():
    return jsonify({'status': 'UniRide backend is running'})


@app.route('/verify-id', methods=['POST'])
def verify_id():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'No image uploaded.'}), 400

        file = request.files['image']
        image_data = file.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        media_type = file.content_type or 'image/jpeg'

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
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': media_type,
                                'data': image_b64
                            }
                        },
                        {
                            'type': 'text',
                            'text': 'This is a student ID card. Extract the full name, matric number, and department. Return only JSON with keys: name, matric_no, department. If you cannot find a field return null.'
                        }
                    ]
                }]
            }
        )

        result = {'name': None, 'matric_no': None, 'department': None}
        try:
            raw = api_response.json()['content'][0]['text']
            raw = raw.replace('```json', '').replace('```', '').strip()
            result = json.loads(raw)
            print("ID scan result:", result)
        except Exception as parse_err:
            print("Could not parse ID response:", parse_err)

        return jsonify(result), 200

    except Exception as e:
        print("ERROR in /verify-id:", str(e))
        return jsonify({'message': str(e)}), 500


@app.route('/verify-id/confirm', methods=['POST'])
def confirm_verification():
    return jsonify({'message': 'Verified successfully.'}), 200


@app.route('/match-ride', methods=['POST'])
def match_ride():
    try:
        data = request.get_json()
        message = data.get('message', '')
        riders = data.get('riders', [])
        print("Match ride request:", message)
        print("Online riders received:", len(riders))

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
                    'content': 'Extract destination, time, and budget from this ride request. Return only JSON with keys: destination, time, budget. If any field is not mentioned return null. Message: "' + message + '"'
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
    app.run(host='0.0.0.0', port=10000, debug=False)
