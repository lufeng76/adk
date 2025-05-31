"""
Example of using types.Part.from_function_call in google.genai to read a web URI 
and generate a PDF as part of a multimodal prompt.
"""

import os
import requests
import tempfile
from google.genai import Client, types
import pdfkit  # You may need to install this: pip install pdfkit
# Note: pdfkit requires wkhtmltopdf to be installed on your system
# For macOS: brew install wkhtmltopdf
# For Ubuntu: apt-get install wkhtmltopdf
# For Windows: Download from https://wkhtmltopdf.org/downloads.html

# Initialize the Google Generative AI client
# Replace with your project ID and location
client = Client(
    vertexai=True,  # Required for Google Cloud API
    project="lufeng-demo",  # Replace with your project ID
    location="us-central1",  # Replace with your location
)

def fetch_web_content(url):
    """
    Fetch content from a web URL.
    
    Args:
        url (str): The URL to fetch content from
        
    Returns:
        str: The HTML content of the webpage
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except Exception as e:
        print(f"Error fetching content from {url}: {e}")
        return None

def convert_html_to_pdf(html_content, output_path=None):
    """
    Convert HTML content to a PDF file.
    
    Args:
        html_content (str): The HTML content to convert
        output_path (str, optional): Path to save the PDF. If None, a temporary file is created.
        
    Returns:
        str: Path to the generated PDF file
    """
    if output_path is None:
        # Create a temporary file with .pdf extension
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        output_path = temp_file.name
        temp_file.close()
    
    try:
        # Convert HTML to PDF
        pdfkit.from_string(html_content, output_path)
        return output_path
    except Exception as e:
        print(f"Error converting HTML to PDF: {e}")
        return None

def web_to_pdf(url):
    """
    Function to be used with types.Part.from_function_call.
    Fetches content from a URL and converts it to PDF.
    
    Args:
        url (str): The URL to fetch and convert to PDF
        
    Returns:
        dict: A dictionary with the path to the generated PDF
    """
    # Fetch content from the URL
    html_content = fetch_web_content(url)
    
    if html_content:
        # Convert HTML to PDF
        pdf_path = convert_html_to_pdf(html_content)
        
        if pdf_path:
            return {"pdf_path": pdf_path}
    
    return {"error": f"Failed to process URL: {url}"}

def main():
    # URL to fetch and convert to PDF
    url = "https://cloud.google.com/billing/docs/how-to/export-data-bigquery-tables"
    
    # Create a multimodal prompt with text and the result of the function call
    content_parts = [
        # Add text prompt
        types.Part.from_text(text="Analyze the following html page about Google Cloud Billing exports and summarize the key points:"),
        
        # Add PDF generated from web content using function call
        types.Part.from_text(text=fetch_web_content(url)),
        # types.Part.from_function_call(
        #     name="fetch_web_content",
        #     args={"url": url}
        # )
    ]
    
    # Generate content using the multimodal prompt
    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro",  # Use an appropriate model that supports multimodal input
            contents=content_parts,
            config=types.GenerateContentConfig(
                 temperature=0.3,
            ),
        )
        
        # Print the response
        print("Summary of the PDF content:")
        print(response.text)
        
    except Exception as e:
        print(f"Error generating content: {e}")
    
    # Clean up temporary files if needed
    # If you're using temporary files, you might want to delete them after use

if __name__ == "__main__":
    main()
