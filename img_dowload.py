import pandas as pd
import requests
import os
import re

# Define the path to the Excel file and the output directory
excel_file_path = r'E:\project\2023\scraping-gramedia-book\source\image_urls.xlsx'
output_directory = r'E:\project\2023\scraping-gramedia-book\source\img\result'
output_excel_path = r'E:\project\2023\scraping-gramedia-book\source\image_urls_with_filenames.xlsx'

# Create the output directory if it does not exist
os.makedirs(output_directory, exist_ok=True)

# Function to create a safe filename from the title
def create_safe_filename(title):
    # Ensure the title is a string
    title = str(title)
    # Replace non-alphanumeric characters with hyphens
    safe_filename = re.sub(r'[^\w\s]', '', title)
    safe_filename = re.sub(r'\s+', '-', safe_filename)
    return safe_filename.lower() + '.jpg'

# Load the Excel file
df = pd.read_excel(excel_file_path)

# Download images
results = []
for index, row in df.iterrows():
    title = row['title']
    image_url = row['image_url']
    safe_filename = create_safe_filename(title)
    output_path = os.path.join(output_directory, safe_filename)
    
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(output_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f'Successfully downloaded {safe_filename}')
            results.append([title, image_url, safe_filename])  # Collect results
        else:
            print(f'Failed to download {image_url}: HTTP {response.status_code}')
    except Exception as e:
        print(f'Error downloading {image_url}: {e}')

# Create a DataFrame with results
result_df = pd.DataFrame(results, columns=['title', 'image_url', 'filename_img'])

# Save the DataFrame to a new Excel file
result_df.to_excel(output_excel_path, index=False)

print(f'Download completed. Results saved to {output_excel_path}')
