from flask import Flask, render_template, request, send_from_directory, redirect, url_for
from io import BytesIO
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import os
from scripts.utils import load_image_into_array
from scripts.pca_compression import PCACompressor
from scripts.utils import load_array_into_image
from scripts.utils import resize_image
import tempfile

app = Flask(__name__)

# Define A4 dimensions (Width x Height in millimeters)
A4 = (210, 297)

def generate_pdf(image_buffer, pdf_filename):
    # Save the BytesIO object as a temporary image file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
        tmp_file.write(image_buffer.getvalue())

    try:
        # Create a PDF with the image
        with open(pdf_filename, 'wb') as pdf_file:
            pdf = canvas.Canvas(pdf_file, pagesize=A4)
            pdf.drawImage(tmp_file.name, 0, 0, width=A4[0], height=A4[1])
            pdf.showPage()
            pdf.save()
    finally:
        # Clean up the temporary image file
        os.unlink(tmp_file.name)

# Utility function to get original_info from the compressed image
def get_original_info_from_compressed_image(compressed_image_filename):
    # Implement this function based on your actual logic
    # For example, retrieve metadata from the original image
    # and store it in the compressed image during compression
    # Here, I'm assuming you have a function named 'get_original_info'
    # that retrieves information from the original image file
    original_image_filename = compressed_image_filename.replace("_pca_compressed_adjusted.jpg", "")
    return get_original_info(original_image_filename)

# Route for the index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling image compression
@app.route('/compress', methods=['POST'])
def compress():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file"
    
    quality = request.form.get('quality', default=85, type=int)
    number_of_components = request.form.get('number_of_components', default=5000, type=int)

    # Calculate file sizes
    original_size_bytes = len(file.read())
    original_size_kb = original_size_bytes / 1024  # Convert to KB

    # Reset the file pointer before reading again
    file.seek(0)

    image_array = load_image_into_array(file)
    if image_array is None:
        return "Invalid image file. Please try again."

    compressor = PCACompressor(image_array)
    compressed_array = compressor.compress(number_of_components)
    compressed_image = load_array_into_image(compressed_array)

    # Save the compressed image to the server with the original image's dimensions
    compressed_image_filename = f"{file.filename}_pca_compressed.jpg"
    compressed_image.save(compressed_image_filename, format="JPEG", quality=quality)

    # Save the compressed image to the buffer for PDF generation
    buffer_for_pdf = BytesIO()
    compressed_image.save(buffer_for_pdf, format="JPEG", quality=quality)

    # Generate PDF with the compressed image
    pdf_filename = f"{file.filename}_pca_compressed.pdf"
    generate_pdf(buffer_for_pdf, pdf_filename)

    # Example of how to pass original_info to the result route
    original_info = compressor.get_original_info()

    # Calculate compressed image size in KB
    compressed_size_kb = len(buffer_for_pdf.getvalue()) / 1024  # Convert to KB

    return render_template(
        'result.html',
        uploaded_image=file,
        original_info=original_info,
        compressed_info=compressor.get_compressed_info(),
        original_size_kb=original_size_kb,
        compressed_size_kb=compressed_size_kb,
        compressed_image_filename=compressed_image_filename,
        compressed_pdf_filename=pdf_filename
    )

# Route for converting adjusted image to PDF
@app.route('/convert_to_pdf', methods=['POST'])
def convert_to_pdf():
    adjusted_image_filename = request.form.get('adjusted_image_filename')

    if not adjusted_image_filename:
        return "Error: No filename provided."

    if not os.path.exists(adjusted_image_filename):
        return f"Error: File not found at {adjusted_image_filename}"

    try:
        # Read the adjusted image content
        adjusted_image = Image.open(adjusted_image_filename)

        # Generate the PDF filename
        pdf_filename = adjusted_image_filename.replace(".jpg", ".pdf")

        # Create a PDF with the adjusted image
        with open(pdf_filename, 'wb') as pdf_file:
            c = canvas.Canvas(pdf_file, pagesize=A4)
            c.drawImage(adjusted_image_filename, 0, 0, width=A4[0], height=A4[1])
            c.showPage()
            c.save()

        # Provide a link to download the generated PDF
        return redirect(url_for('download', filename=pdf_filename))
    except Exception as e:
        return f"Error creating PDF: {str(e)}"

# Route for downloading files
@app.route('/download/<path:filename>')
def download(filename):
    directory = os.path.dirname(filename)
    return send_from_directory(directory, os.path.basename(filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
