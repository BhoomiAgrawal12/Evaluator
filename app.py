from flask import Flask, request, jsonify, send_from_directory
import os
import traceback
from llama_cloud_services import LlamaParse
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return '''
    <h1>Upload a PPT or PPTX file</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".ppt,.pptx,.pdf,.png,.jpg,.jpeg" required>
        <button type="submit">Upload</button>
    </form>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if file part is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    file = request.files['file']
    # Check if filename is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected for upload.'}), 400
    # Check file extension
    allowed_ext = ('.ppt', '.pptx', '.pdf', '.png', '.jpg', '.jpeg')
    if not (file and file.filename.lower().endswith(allowed_ext)):
        return jsonify({'error': 'Invalid file type. Only PPT, PPTX, PDF, PNG, JPG, or JPEG allowed.'}), 400
    # Check file size (limit to 20MB for example)
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    max_size = 20 * 1024 * 1024  # 20MB
    if file_length > max_size:
        return jsonify({'error': 'File too large. Max size is 20MB.'}), 400
    # Save file safely
    try:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
    except Exception as e:
        return jsonify({'error': 'Failed to save file.', 'details': str(e)}), 500
    # Parse with LlamaParse
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        return jsonify({'error': 'LlamaParse API key not set in environment.'}), 500
    parser = LlamaParse(
        api_key=api_key,
        num_workers=4,
        verbose=True,
        language="en",
    )
    try:
        result = parser.parse(filepath)
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg']:
            # Get image documents and descriptions
            image_documents = result.get_image_documents(
                include_screenshot_images=True,
                include_object_images=False,
                image_download_dir="./images",
            )
            # Prepare image info (base64 and description)
            images_info = []
            for img_doc in image_documents:
                # img_doc.image_bytes is the image in bytes
                import base64
                img_b64 = base64.b64encode(img_doc.image_bytes).decode('utf-8')
                images_info.append({
                    'image_base64': img_b64,
                    'description': getattr(img_doc, 'description', ''),
                })
            # Also include page-level info if available
            pages = []
            for page in result.pages:
                pages.append({
                    'text': getattr(page, 'text', ''),
                    'md': getattr(page, 'md', ''),
                    'images': getattr(page, 'images', []),
                    'layout': getattr(page, 'layout', {}),
                    'structuredData': getattr(page, 'structuredData', {}),
                })
            return jsonify({'message': 'Image uploaded and parsed successfully', 'images': images_info, 'pages': pages}), 200
        else:
            markdown_documents = result.get_markdown_documents(split_by_page=True)
            # Convert Document objects to plain markdown strings
            markdown_strings = [doc.markdown if hasattr(doc, 'markdown') else str(doc) for doc in markdown_documents]
            return jsonify({'message': 'File uploaded and parsed successfully', 'markdown_documents': markdown_strings}), 200
    except Exception as e:
        err_msg = str(e)
        tb = traceback.format_exc()
        print("--- Exception Traceback ---")
        print(tb)
        # Custom error messages for common issues
        if 'DNS resolution failed' in err_msg or 'Name or service not known' in err_msg:
            return jsonify({
                'error': 'DNS resolution failed. Cannot reach LlamaParse API.',
                'suggestions': [
                    'Check your internet connection',
                    'Try changing DNS to 8.8.8.8 or 1.1.1.1',
                    'Flush DNS cache: ipconfig /flushdns',
                    'Check firewall settings'
                ],
                'traceback': tb
            }), 500
        if '401' in err_msg or 'Unauthorized' in err_msg or 'Invalid token format' in err_msg:
            return jsonify({
                'error': 'LlamaParse API key is invalid or expired.',
                'suggestions': [
                    'Check your API key',
                    'Generate a new API key from LlamaIndex Cloud',
                    'Set the correct key in your code or environment variable'
                ],
                'traceback': tb
            }), 401
        return jsonify({'error': 'LlamaParse Python client failed', 'py_error': err_msg, 'traceback': tb}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)