from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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

# List of category URLs
category_urls = [
    "https://www.gramedia.com/categories/buku/buku-masakan?page={}"
]

# List to store all products
all_products = []

# Function to scrape details from a detail link
def scrape_detail_page(detail_link, category):
    start_time = time.time()
    try:
        # Set a shorter timeout initially
        driver.set_page_load_timeout(10)
        driver.get(detail_link)

        # Check if the product is out of stock
        try:
            stock_section = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'stock-section'))
            )
            stock_message = stock_section.find_element(By.CLASS_NAME, 'stock-label').text.strip()
            if "Maaf, stok barang sedang kosong" in stock_message:
                print(f"Product out of stock: {detail_link}")
                return None
        except TimeoutException:
            pass
        except NoSuchElementException:
            pass

        # Proceed with the usual detail extraction process
        driver.set_page_load_timeout(30)

        # Wait until the detail-section is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'detail-section'))
        )

        # Check if the detail section exists
        try:
            detail_section = driver.find_element(By.CLASS_NAME, 'detail-section')
        except NoSuchElementException:
            print(f"No detail section found for {detail_link}. Skipping.")
            return None

        # Find and extract details
        detail_items = detail_section.find_elements(By.TAG_NAME, 'li')

        details = {}
        for item in detail_items:
            try:
                label = item.find_element(By.TAG_NAME, 'span').text.split("\n")[0].strip()
                value = item.find_element(By.TAG_NAME, 'p').text.strip()
                details[label] = value
            except NoSuchElementException:
                continue

        # Extract title, author, and price
        title = driver.find_element(By.CLASS_NAME, 'book-title').text.strip()
        author = driver.find_element(By.CLASS_NAME, 'title-author').text.strip()
        price = driver.find_element(By.CLASS_NAME, 'price-from').text.strip()

        # Extract image URL
        try:
            image_url = driver.find_element(By.CSS_SELECTOR, '.box-image .image img').get_attribute('src')
        except NoSuchElementException:
            image_url = 'No image available'

        # Add extracted fields to details
        details['Title'] = title
        details['Author'] = author
        details['Price'] = price
        details['image_url'] = image_url
        details['category'] = category

        # Add detail_link to details
        details['detail_link'] = detail_link

        # Create a dictionary with the required format
        formatted_details = {
            'Title': details.pop('Title', 'No title available'),
            'detail_link': detail_link,
            'image_url': details.pop('image_url', 'No image available'),
            'category': details.pop('category', 'No category available'),
            'Author': details.pop('Author', 'No author available'),
            'Price': details.pop('Price', 'No price available'),
            **details
        }

        return formatted_details

    except TimeoutException:
        print(f"Timeout while loading page: {detail_link}. Skipping.")
        return None
    except Exception as e:
        print(f"Error scraping detail page: {str(e)}")
        return None
    finally:
        end_time = time.time()
        time_taken = end_time - start_time
        print(f"Time taken for {detail_link}: {time_taken:.2f} seconds")

# Function to save the current state of all_products to a JSON file
def save_to_file():
    with open('gramedia_best_sellers_with_details.json', 'w') as f:
        json.dump(all_products, f, indent=2)

# Iterate over each category URL
for category_url in category_urls:
    # Extract category from the URL and remove '?page={}' part
    category = category_url.split('categories/')[1].split('/')[1].split('?')[0]
    
    # Iterate over pages until no more results are found
    page = 1
    while True:
        url = category_url.format(page)
        print(f"Scraping category: {category}, page: {page}, URL: {url}")
        
        # Navigate to the URL
        try:
            driver.get(url)
            
            # Wait until the products are loaded
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'card-list'))
            )
        except TimeoutException:
            print(f"Timeout occurred on page {page} in category {category}. Saving progress and stopping.")
            save_to_file()
            break
        except Exception as e:
            print(f"Error occurred: {str(e)}. Saving progress and stopping.")
            save_to_file()
            break
        
        # Get the updated page source after loading
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
            print(f"No products found on page {page} in category {category}")
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
                detail_data = scrape_detail_page(full_detail_link, category)
                
                if detail_data:
                    print(f"Detail Data for {full_detail_link}:")
                    print(detail_data)
                    print("---")
                    all_products.append(detail_data)
                else:
                    print(f"Failed to scrape detail data for {full_detail_link}")
        
        # Save progress after each page
        save_to_file()
        
        # Move to the next page
        page += 1

# Close the WebDriver
driver.quit()

# Final save to ensure all data is stored
save_to_file()

# Print or save the JSON data
print(json.dumps(all_products, indent=2))

# Debug message to indicate the script has finished running
print("Script execution completed")
