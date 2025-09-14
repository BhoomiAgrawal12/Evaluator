from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return send_from_directory('.', 'upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and (file.filename.lower().endswith('.ppt') or file.filename.lower().endswith('.pptx')):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        # Send file to LlamaParse API with error handling
        api_url = 'https://api.llamaparse.com/v1/parse'
        api_key = 'llx-V1ZqMmwUaUYMXE1spAwkhybu1PA3VnMzR4Sq18ikRqiH4dbj'
        
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (file.filename, f, 'application/vnd.ms-powerpoint')}
                headers = {'Authorization': f'Bearer {api_key}'}
                
                response = requests.post(api_url, files=files, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    try:
                        parsed = response.json()
                        return jsonify({
                            'message': 'File uploaded and parsed successfully', 
                            'parsed': parsed
                        }), 200
                    except Exception as json_error:
                        return jsonify({
                            'error': 'Failed to parse response as JSON', 
                            'raw': response.text[:500]
                        }), 500
                else:
                    return jsonify({
                        'error': 'LlamaParse API error', 
                        'status_code': response.status_code, 
                        'response': response.text[:500]
                    }), 500
                    
        except ConnectionError as e:
            if "getaddrinfo failed" in str(e):
                return jsonify({
                    'error': 'DNS resolution failed. Cannot reach LlamaParse API.',
                    'suggestions': [
                        'Check your internet connection',
                        'Try changing DNS to 8.8.8.8 or 1.1.1.1',
                        'Flush DNS cache: ipconfig /flushdns',
                        'Check firewall settings'
                    ]
                }), 503
            else:
                return jsonify({
                    'error': 'Connection error to LlamaParse API',
                    'details': str(e)
                }), 503
                
        except Timeout:
            return jsonify({
                'error': 'Request timed out',
                'suggestion': 'Please try again'
            }), 503
            
        except Exception as e:
            return jsonify({
                'error': 'An unexpected error occurred',
                'details': str(e)
            }), 500
    else:
        return jsonify({'error': 'Invalid file type. Only PPT/PPTX files are allowed.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)