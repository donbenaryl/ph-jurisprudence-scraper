from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import mysql.connector
import os
from dotenv import load_dotenv
import time
import logging
from datetime import datetime
from urllib.parse import urljoin
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class JurisprudenceScraper:
    def __init__(self):
        self.base_url = "https://lawphil.net/judjuris/judjuris.html"
        self.setup_database()
        self.setup_driver()

    def setup_driver(self):
        logging.info("Initializing WebDriver")
        
        """Initialize the Chrome WebDriver"""
        
        try:
            self.driver = webdriver.Chrome()
            self.wait = WebDriverWait(self.driver, 10)
            logging.info("WebDriver initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {e}")
            raise

    def setup_database(self):
        """Setup MySQL database connection"""
        try:
            self.db = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', 'password'),
                database=os.getenv('DB_NAME', 'case_comparison'),
                port=os.getenv('DB_PORT', '3306')
            )
            self.cursor = self.db.cursor()
            self.create_tables()
        except mysql.connector.Error as err:
            logging.error(f"Database connection failed: {err}")
            raise

    def create_tables(self):
        """Create necessary database tables if they don't exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(500),
                case_date DATE,
                content TEXT,
                year INT,
                month VARCHAR(20),
                url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.db.commit()

    def closeCookiePopup(self):
        """Close the cookie popup"""
        try:
            close_button = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cookie_box_close")))
            close_button.click()
            self.wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "cookie_box_close")))
            
        except Exception as e:
            logging.error(f"Failed to find or click the cookie popup close button: {e}")

    def scrape(self):
        """Main scraping method"""
        try:
            self.driver.get(self.base_url)
            logging.info("Started scraping process")

            # Close cookie popup
            self.closeCookiePopup()

            current_year = datetime.now().year
            year_links = [link.text for link in self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[href*='juri']:not(b.progressive)")))]
            year_links = [year for year in year_links if year.isdigit() and int(year) <= current_year]


            for year_link in year_links:
                logging.info(f"Processing year {year_link}")

                year_element = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//a[descendant-or-self::text()[contains(., '{year_link}')]]")))

                logging.info("Processing year next year")
                year = year_element.text.strip()

                logging.info(f"Checking if year is digit: {year}")
                if not year.isdigit():
                    continue

                logging.info(f"Processing year: {year}")
                year_element.click()

                # Get all month links
                month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

                month_ctr = 0
                for month_name in month_names:
                    logging.info(f"Loading month: {month_name}")
                    month_link = self.wait.until(EC.presence_of_element_located(
                        (By.XPATH, f"//a[text()='{month_name}' and not(contains(@class, 'nya'))]")))

                    # Proceed to next loop on disabled month
                    if "progressive" in month_link.get_attribute("class"):
                        logging.info(f"Skipping month: {month_name} as it contains class 'progressive'")
                        continue

                    month_link.click()

                    # Wait for the next page to load
                    logging.info(f"Loading cases")
                    # Get all case links
                    case_links = self.wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(text(), 'G.R.') and not(contains(@class, 'nya'))]")))

                    # ctr = 0
                    for case_link in case_links:
                        self.process_case(case_link, year, month_name)

                    logging.info("Going back to month list")
                    self.driver.back()
                
                logging.info("Going back to year list")
                self.driver.back()

        except Exception as e:
            logging.error(f"Error during scraping: {e}")
        finally:
            self.cleanup()

    def process_case(self, case_link, year, month):
        """Process individual case"""
        try:
            all_titles = case_link.text.strip().split("/")
            title = all_titles[0]
            path = case_link.get_attribute('href')

            # Extract date from the case link structure
            parent_element = case_link.find_element(By.XPATH, "..")
            date_text = parent_element.text.split("\n")[1]

            logging.info(f"Processing case: {title} - {date_text}")
            case_link.click()

            # Extract the numbers from the title
            title_numbers = title.split(".")[-1].strip()
            logging.info(f"Extracted title numbers: {title_numbers}")



            logging.info(f"Loading case {title} content")
            content_element = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//*[contains(text(), '{title_numbers}')]/ancestor::blockquote[1]")))
            content = content_element.get_attribute('innerText').replace('\n', '\n\n')
            if "Footnotes" in content:
                content = content.split("Footnotes")[0].strip()
                

            # Convert date string to Date object
            logging.info(f"Converting date {date_text} to Date object")
            case_date = datetime.strptime(date_text, "%B %d, %Y").date()

            # Save to database
            for title in all_titles:
                case = self.load_case_by_title(title)
                if case == None:
                    logging.info(f"Saving case {title} to database")
                    self.save_case({
                        'case_date': case_date,
                        'title': title,
                        'year': year,
                        'month': month,
                        'content': content,
                        'url': path
                    })

            logging.info("Going back to case lists")
            self.driver.back()

        except Exception as e:
            logging.error(f"Error processing case: {e}. Loading next case")
            self.driver.back()
        
    def exit_if_error(self, error_message):
        """Log the error and exit the program"""
        logging.error(error_message)
        self.cleanup()
        exit(1)

    def save_case(self, case_data):
        """Save case data to database"""
        try:
            query = '''
                INSERT INTO cases (case_date, title, year, month, content, url)
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
            values = (
                case_data['case_date'],
                case_data['title'],
                case_data['year'],
                case_data['month'],
                case_data['content'],
                case_data['url']
            )
            self.cursor.execute(query, values)
            self.db.commit()
            logging.info(f"Saved case: {case_data['title']}")
        except mysql.connector.Error as err:
            logging.error(f"Error saving case to database: {err}")
    
    def load_case_by_title(self, title):
        """Load case data from database based on title"""
        try:
            query = '''
                SELECT case_date, title, year, month, content, url
                FROM cases
                WHERE title = %s
            '''
            self.cursor.execute(query, (title,))
            case_data = self.cursor.fetchone()
            if case_data:
                logging.info(f"Loaded case: {title}")
                return {
                    'case_date': case_data[0],
                    'title': case_data[1],
                    'year': case_data[2],
                    'month': case_data[3],
                    'content': case_data[4],
                    'url': case_data[5]
                }
            else:
                logging.warning(f"No case found with title: {title}")
                return None
        except mysql.connector.Error as err:
            logging.error(f"Error loading case from database: {err}")
            return None

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'driver'):
            self.driver.quit()
        if hasattr(self, 'db'):
            self.db.close()

if __name__ == "__main__":
    scraper = JurisprudenceScraper()
    scraper.scrape() 