from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

# Configure Selenium options for window size and zoom
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--start-maximized")  # Open browser in full screen
chrome_options.add_argument("--force-device-scale-factor=0.75")  # Set zoom to 75%

# Set up the Selenium WebDriver with configured options
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL of the website you want to scrape
base_url = "https://www.gramedia.com/search?based_on=best-seller&category=buku&page={}"

# List to store all products
all_products = []

# Function to scroll down slowly to the middle of the page
def scroll_down_slow(driver):
    # Get current page height
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # Scroll down in increments
    for i in range(10):  # Adjust the number of increments as needed
        # Scroll down by a small increment
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
        time.sleep(2)  # Adjust sleep time if necessary

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Function to scrape details from a detail link
def scrape_detail_page(detail_link):
    driver.get(detail_link)

    try:
        # Wait until the detail-section is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'detail-section'))
        )
        
        # Find and extract details
        detail_section = driver.find_element(By.CLASS_NAME, 'detail-section')
        detail_items = detail_section.find_elements(By.TAG_NAME, 'li')

        details = {}
        for item in detail_items:
            label = item.find_element(By.TAG_NAME, 'span').text.split("\n")[0].strip()
            value = item.find_element(By.TAG_NAME, 'p').text.strip()
            details[label] = value

        # Extract title, author, and price
        title = driver.find_element(By.CLASS_NAME, 'book-title').text.strip()
        author = driver.find_element(By.CLASS_NAME, 'title-author').text.strip()
        price = driver.find_element(By.CLASS_NAME, 'price-from').text.strip()

        # Add extracted fields to details
        details['Title'] = title
        details['Author'] = author
        details['Price'] = price

        # Add detail_link to details
        details['detail_link'] = detail_link

        # Create a dictionary with the required format
        formatted_details = {
            'Title': details.pop('Title', 'No title available'),
            'detail_link': detail_link,
            'Author': details.pop('Author', 'No author available'),
            'Price': details.pop('Price', 'No price available'),
            **details
        }

        return formatted_details

    except Exception as e:
        print(f"Error scraping detail page: {str(e)}")
        return None

# Iterate over pages until no more results are found
page = 1
while True:
    url = base_url.format(page)
    print(f"Scraping page: {page}, URL: {url}")
    
    # Navigate to the URL
    driver.get(url)
    
    try:
        # Wait until the products are loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'card-list'))
        )
    except:
        print(f"No products found or page did not load on page {page}")
        break
    
    # Scroll down slowly to load more content
    scroll_down_slow(driver)
    
    # Get the updated page source after scrolling
    html_content = driver.page_source
    
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check for "no results" message
    no_results = soup.find('div', class_='no-result')
    if no_results and "Maaf, kami tidak menemukan apa yang anda cari" in no_results.text:
        print("No more results found.")
        break
    
    # Find all product containers with the class 'card-list'
    products = soup.find_all('gm-product-list', class_='card-list')
    
    # Check if products are found
    if not products:
        print(f"No products found on page {page}")
        break
    
    # Iterate through the products and extract data
    for product in products:
        # Extract detail link if available
        detail_link_tag = product.find('a', attrs={'_ngcontent-web-gramedia-c26': '', 'href': True})
    
        # Check if detail_link_tag exists and extract the href attribute
        if detail_link_tag:
            href_attr = detail_link_tag.get('href')
            full_detail_link = f"https://www.gramedia.com{href_attr}" if href_attr else 'No detail link available'
            
            # Scrape detail data from the detail link
            detail_data = scrape_detail_page(full_detail_link)
            
            if detail_data:
                print(f"Detail Data for {full_detail_link}:")
                print(detail_data)
                print("---")
                all_products.append(detail_data)
            else:
                print(f"Failed to scrape detail data for {full_detail_link}")
    
    # Move to the next page
    page += 1
    
# Close the WebDriver
driver.quit()

# Convert the list of dictionaries to JSON format
json_data = json.dumps(all_products, indent=2)

# Save the JSON data to a file (optional)
with open('gramedia_best_sellers_with_details.json', 'w') as f:
    f.write(json_data)

# Print or save the JSON data
print(json_data)

# Debug message to indicate the script has finished running
print("Script execution completed")
