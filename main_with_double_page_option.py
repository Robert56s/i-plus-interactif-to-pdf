#!/usr/bin/env python3
"""
iPlus Interactif Image Backup Utility - Functional Edition
A functional solution for backing up books from iPlus Interactif website.

Author: DeltaGa & Robert56s
Double page mode: Kaloo234
Version: 3.0.0 (Functional)
Python: 3.7+
"""

import os
import time
import base64
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from fpdf import FPDF

from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

# Authentication
DEFAULT_EMAIL = os.getenv('EMAIL')
DEFAULT_PASSWORD = os.getenv('PASSWORD')

# Website URLs
BASE_URL = "https://www.iplusinteractif.com/"

# Selenium selectors
SELECTORS = {
    'login_email': "//*[@id='loginId']",
    'login_password': "//*[@id='password']",
    'login_button': "//*[contains(@class, 'blue button')]",
    'cookies_reject': "onetrust-reject-all-handler",
    'book_containers': "//div[contains(@class, 'accessContainer')]",
    'book_title': ".//h2[@class='access__title']",
    'popup_close': '//*[@id="commercialpopup"]/div/div/div[1]/button',
    'nav_volumes': '//*[@id="iplus-R-confBook"]/div[1]/div/ul/li',
    'volume_title': ".//h3",
    'open_book': "//a[@class='iplus-l-confBook__itemVolumeCouv coverEffect']",
    'page_input': "//input[@class='iplus-R-ReactPreviewFrame__pagination_input']",
    'main_image': '//*[@id="iplus-R-ReactPreviewFrame"]/div/div[3]/div/div/div[1]/img',
    'next_arrow': "//div[contains(@class, 'iplus-l-ReactPreviewFrame__paginationArrow__arrowRight')]",

    'main_image_double_page': "//div[contains(@class, 'iplus-R-ReactPreviewFrame__containerDoublePage')]//img",
    'view_mode_link': "//div[@class='iplus-R-ReactNavToolbar']/div[10]/div/a",
    'double_page_link': "//a[contains(@class,'iplus-R-ReactPreviewFrame__toolsPageTemplatePageDouble')]",
    'one_page_link': "//a[contains(@class,'iplus-R-ReactPreviewFrame__toolsPageTemplatePageSingle')]",
    'tool_bar': "//nav[contains(@class, 'iplus-R-ReactPreviewFrame__toolsPageItems')]"
}

# Timing configurations
TIMEOUTS = {
    'implicit_wait': 10,
    'page_load': 10,
    'navigation': 4,
    'post_click': 4
}

# File system
TEMP_DIR = "imgs"
SAVE_DIR = "save"
DEFAULT_BOOK_NAME = "book"
IMAGE_FORMAT = "png"
PDF_DIMENSIONS = (2640, 3263)


# ============================================================================
# DRIVER INITIALIZATION
# ============================================================================

def configure_chrome_options(headless=False, detach=True):
    """Configure Chrome options with defaults."""
    options = Options()
    
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    
    if detach:
        options.add_experimental_option("detach", True)
        
    # Performance and stability enhancements
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--silent")
    options.add_argument("--log-level=3")
    
    return options


def create_driver(headless=False, detach=True):
    """Create and configure the Chrome driver."""
    options = configure_chrome_options(headless, detach)
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(TIMEOUTS['implicit_wait'])
    driver.maximize_window()
    
    return driver


# ============================================================================
# AUTHENTICATION & NAVIGATION
# ============================================================================

def authenticate(driver, email=DEFAULT_EMAIL, password=DEFAULT_PASSWORD):
    """Perform user authentication."""
    try:
        print("Starting authentication...")
        driver.get(BASE_URL)
        
        wait = WebDriverWait(driver, TIMEOUTS['page_load'])
        
        # Email input
        email_element = wait.until(
            EC.element_to_be_clickable((By.XPATH, SELECTORS['login_email']))
        )
        email_element.clear()
        email_element.send_keys(email)
        
        # Password input
        password_element = driver.find_element(By.XPATH, SELECTORS['login_password'])
        password_element.clear()
        password_element.send_keys(password)
        
        # Submit login
        login_button = driver.find_element(By.XPATH, SELECTORS['login_button'])
        login_button.click()
        
        time.sleep(TIMEOUTS['post_click'])
        
        # Handle cookies popup if present
        handle_cookies_popup(driver)
        
        print("Authentication completed successfully!")
        return True
        
    except TimeoutException:
        print("Authentication timeout - UI elements not found")
        return False
    except Exception as e:
        print(f"Authentication failed: {e}")
        return False


def handle_cookies_popup(driver):
    """Handle cookies popup with graceful fallback."""
    try:
        cookies_button = driver.find_element(By.ID, SELECTORS['cookies_reject'])
        if cookies_button.is_displayed():
            cookies_button.click()
            print("Cookies popup handled")
    except NoSuchElementException:
        pass  # No cookies popup


def discover_books(driver):
    """Discover and catalog available books."""
    time.sleep(TIMEOUTS['navigation'])  # Allow page to stabilize
    
    try:
        book_elements = driver.find_elements(By.XPATH, SELECTORS['book_containers'])
        books = []
        
        for index, element in enumerate(book_elements):
            try:
                title_element = element.find_element(By.XPATH, SELECTORS['book_title'])
                title = title_element.text.strip()
                
                books.append({
                    'index': index,
                    'title': title,
                    'element': element
                })
                
            except NoSuchElementException:
                print(f"Could not extract title for book at index {index}")
                continue
        
        print(f"Discovered {len(books)} books")
        return books
        
    except Exception as e:
        print(f"Book discovery failed: {e}")
        return []


def handle_commercial_popup(driver):
    """Handle commercial popup with graceful fallback."""
    try:
        close_popup = driver.find_element(By.XPATH, SELECTORS['popup_close'])
        close_popup.click()
        print("Commercial popup closed")
    except NoSuchElementException:
        pass  # No commercial popup


def handle_volume_selection(driver):
    """Handle volume selection for multi-volume books."""
    try:
        nav_volumes = driver.find_elements(By.XPATH, SELECTORS['nav_volumes'])
        
        if not nav_volumes:
            return "None"  # Single volume book
            
        print(f"\nMultiple volumes detected. Please select:")
        
        for volume in nav_volumes:
            try:
                vol_title = volume.find_element(By.XPATH, SELECTORS['volume_title']).text
                choice = input(f"Save volume '{vol_title}'? (yes/no): ").lower().strip()
                
                if choice == 'yes':
                    volume.click()
                    print(f"Selected volume: {vol_title}")
                    return vol_title
                elif choice == 'no':
                    print("Volume skipped.")
                    continue
                    
            except Exception as e:
                print(f"Error processing volume: {e}")
                continue
        
        print("No volumes selected.")
        return False  # Signal user cancellation
        
    except Exception as e:
        print(f"Volume selection failed: {e}")
        return None


def select_book_and_volume(driver, book):
    """Select a book and handle volume selection if necessary."""
    try:
        book['element'].click()
        time.sleep(TIMEOUTS['navigation'])
        
        # Switch to new window
        driver.switch_to.window(driver.window_handles[1])
        
        # Handle commercial popup
        handle_commercial_popup(driver)
        
        # Check for multiple volumes
        selected_volume = handle_volume_selection(driver)
        if selected_volume is False:  # User cancelled volume selection
            return None
            
        return selected_volume
        
    except Exception as e:
        print(f"Book selection failed: {e}")
        return None


def open_book_viewer(driver):
    """Open the book viewer and navigate to first page."""
    try:
        time.sleep(TIMEOUTS['post_click'])
        
        wait = WebDriverWait(driver, TIMEOUTS['page_load'])
        
        open_book_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, SELECTORS['open_book']))
        )
        open_book_button.click()
        
        time.sleep(TIMEOUTS['navigation'])
        
        # Navigate to cover page (C1)
        page_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, SELECTORS['page_input']))
        )
        page_input.clear()
        page_input.send_keys('C1')
        page_input.send_keys(u'\ue007')  # Enter key
        
        time.sleep(TIMEOUTS['navigation'])
        
        print("Book viewer opened successfully")
        return True
        
    except Exception as e:
        print(f"Failed to open book viewer: {e}")
        return False
    

def set_view_mode(driver, is_double_page):
    try:
        wait = WebDriverWait(driver, TIMEOUTS['page_load'])

        tool_bar_element= driver.find_element(By.XPATH, SELECTORS['tool_bar'])

        lst = tool_bar_element.get_attribute('class').split(" ")

        if is_double_page:
            if 'currentDoublePage\n' in lst:
                return True
            
            view_mode_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS['view_mode_link']))
            )
            view_mode_element.click()
            time.sleep(2)
            double_page_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS['double_page_link']))
            )
            driver.execute_script("arguments[0].click();", double_page_element)
        else:
            if 'currentOnePage\n' in lst:
                return True
            
            view_mode_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS['view_mode_link']))
            )
            view_mode_element.click()
            time.sleep(2)
            double_page_element = wait.until(
                EC.element_to_be_clickable((By.XPATH, SELECTORS['one_page_link']))
            )
            driver.execute_script("arguments[0].click();", double_page_element)

        time.sleep(TIMEOUTS['navigation'])
        return True
    except Exception as e:
        print(e)
        return False


# ============================================================================
# IMAGE PROCESSING
# ============================================================================

def ensure_output_directory():
    """Ensure output directory exists."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        print(f"Created output directory: {TEMP_DIR}")


def extract_image_as_base64(driver):
    """Extract image as base64 using canvas technique."""
    js_script = """
    try {
        var imgElement = document.querySelector('img');
        if (!imgElement) return null;
        
        var canvas = document.createElement('canvas');
        canvas.width = imgElement.naturalWidth || imgElement.width;
        canvas.height = imgElement.naturalHeight || imgElement.height;
        
        var ctx = canvas.getContext('2d');
        ctx.drawImage(imgElement, 0, 0, canvas.width, canvas.height);
        
        return canvas.toDataURL('image/png');
    } catch(e) {
        return null;
    }
    """
    
    try:
        base64_img = driver.execute_script(js_script)
        return base64_img.split(',')[1] if base64_img else None
    except Exception as e:
        print(f"JavaScript extraction failed: {e}")
        return None


def save_base64_image(base64_data, page_number):
    """Save base64 image data to file."""
    try:
        image_data = base64.b64decode(base64_data)
        file_path = os.path.join(TEMP_DIR, f"{page_number}.{IMAGE_FORMAT}")
        
        with open(file_path, 'wb') as f:
            f.write(image_data)
            
    except Exception as e:
        print(f"Failed to save image {page_number}: {e}")
        raise


def process_current_page(driver, page_number):
    """Process the current page image."""
    try:
        # Locate main image
        image_element = driver.find_element(By.XPATH, SELECTORS['main_image'])
        img_src = image_element.get_attribute("src")
        
        if not img_src:
            print("No image source found")
            return False
        
        # Open image in new tab
        driver.execute_script(f'window.open("{img_src}","_blank");')
        driver.switch_to.window(driver.window_handles[2])
        
        time.sleep(TIMEOUTS['post_click'])
        
        # Click to ensure image is loaded
        page_image = driver.find_element(By.XPATH, "//img")
        page_image.click()
        time.sleep(0.3)
        
        # Extract image using JavaScript canvas technique
        base64_data = extract_image_as_base64(driver)
        if not base64_data:
            return False
        
        # Save image
        save_base64_image(base64_data, page_number)
        
        # Cleanup - close current tab and return to book viewer
        driver.close()
        driver.switch_to.window(driver.window_handles[1])
        
        print(f'Page #{page_number} saved successfully')
        return True
        
    except Exception as e:
        print(f"Error processing page {page_number}: {e}")
        return False
    

def process_left_page(driver, page_number):
    """Process the current left page image."""
    try:
        # Locate main image
        image_element = driver.find_elements(By.XPATH, SELECTORS['main_image_double_page'])[0]
        img_src = image_element.get_attribute("src")
        img_width = image_element.get_dom_attribute("width")

        if not img_src:
            print("No image source found")
            return False
        
        if int(img_width) < 10:
            print("No left page")
            return False
        
        # Open image in new tab
        driver.execute_script(f'window.open("{img_src}","_blank");')
        driver.switch_to.window(driver.window_handles[2])
        
        time.sleep(TIMEOUTS['post_click'])
        
        # Click to ensure image is loaded
        page_image = driver.find_element(By.XPATH, "//img")
        page_image.click()
        time.sleep(0.3)
        
        # Extract image using JavaScript canvas technique
        base64_data = extract_image_as_base64(driver)
        if not base64_data:
            return False
        
        # Save image
        save_base64_image(base64_data, page_number)
        
        # Cleanup - close current tab and return to book viewer
        driver.close()
        driver.switch_to.window(driver.window_handles[1])
        
        print(f'Page #{page_number} saved successfully')
        return True
        
    except Exception as e:
        print(f"Error processing page {page_number}: {e}")
        return False
    

def process_right_page(driver, page_number):
    """Process the current right page image."""
    try:
        # Locate main image
        image_element = driver.find_elements(By.XPATH, SELECTORS['main_image_double_page'])[1]
        img_src = image_element.get_attribute("src")
        img_width = image_element.get_dom_attribute("width")

        if not img_src:
            print("No image source found")
            return False
        
        if int(img_width) < 10:
            print("No right page")
            return False
        
        # Open image in new tab
        driver.execute_script(f'window.open("{img_src}","_blank");')
        driver.switch_to.window(driver.window_handles[2])
        
        time.sleep(TIMEOUTS['post_click'])
        
        # Click to ensure image is loaded
        page_image = driver.find_element(By.XPATH, "//img")
        page_image.click()
        time.sleep(0.3)
        
        # Extract image using JavaScript canvas technique
        base64_data = extract_image_as_base64(driver)
        if not base64_data:
            return False
        
        # Save image
        save_base64_image(base64_data, page_number)
        
        # Cleanup - close current tab and return to book viewer
        driver.close()
        driver.switch_to.window(driver.window_handles[1])
        
        print(f'Page #{page_number} saved successfully')
        return True
        
    except Exception as e:
        print(f"Error processing page {page_number}: {e}")
        return False


def navigate_to_next_page(driver):
    """Navigate to the next page if available."""
    try:
        next_element = driver.find_element(By.XPATH, SELECTORS['next_arrow'])
        
        # Check if the arrow is clickable (not disabled/hidden)
        # Get the element's classes to check for disabled state
        classes = next_element.get_attribute('class')
        
        # If arrow has disabled, inactive, or hidden class, we're on last page
        if classes and any(x in classes.lower() for x in ['disabled', 'inactive', 'hidden', 'nodisplay']):
            print("Next arrow is disabled - reached last page")
            return False
        
        # Check if element is actually visible and clickable
        if not next_element.is_displayed() or not next_element.is_enabled():
            print("Next arrow not visible/enabled - reached last page")
            return False
        
        # Try to click
        driver.execute_script("arguments[0].click();", next_element)
        time.sleep(0.5)  # Small delay to let page change register
        
        # Verify page actually changed by checking if we can still find the arrow
        # If we can't, something went wrong
        try:
            driver.find_element(By.XPATH, SELECTORS['next_arrow'])
        except NoSuchElementException:
            print("Page changed but navigation lost - stopping")
            return False
            
        return True
        
    except NoSuchElementException:
        print("Next arrow not found - reached last page")
        return False  # No more pages
    except Exception as e:
        print(f"Navigation error: {e}")
        return False


def process_book_pages(driver, double_page_mode):
    """Process all pages in the current book."""
    ensure_output_directory()
    
    pages_processed = 0
    errors_encountered = 0
    start_time = time.time()
    
    try:
        while True:
            # Process current page
            if not double_page_mode:
                success = process_current_page(driver, pages_processed)
                
                if success:
                    pages_processed += 1
                else:
                    errors_encountered += 1
            else:
                success = process_left_page(driver, pages_processed)

                if success:
                    pages_processed += 1
                else:
                    errors_encountered += 1

                success = process_right_page(driver, pages_processed)

                if success:
                    pages_processed += 1
                else:
                    errors_encountered += 1
            
            # Try to navigate to next page
            time.sleep(TIMEOUTS['post_click'])
            
            if not navigate_to_next_page(driver):
                print("Reached end of book")
                break
        
    except Exception as e:
        print(f"Page processing error: {e}")
        errors_encountered += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nProcessing complete: {pages_processed} pages processed in {duration:.2f} seconds")
    
    return pages_processed, errors_encountered


# ============================================================================
# OUTPUT PROCESSING
# ============================================================================

def collect_image_files():
    """Collect and sort image files numerically."""
    try:
        image_files = []
        
        for filename in os.listdir(TEMP_DIR):
            if filename.endswith(f".{IMAGE_FORMAT}") and filename[:-4].isdigit():
                image_files.append(os.path.join(TEMP_DIR, filename))
        
        # Sort numerically by filename
        image_files.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
        
        return image_files
        
    except Exception as e:
        print(f"Failed to collect image files: {e}")
        return []


def sanitize_filename(filename):
    """Sanitize filename for filesystem compatibility."""
    if not filename:
        return ""
        
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
        
    # Limit length and strip whitespace
    return filename.strip()[:200]


def create_pdf(book_name):
    """Create PDF from processed images."""
    try:
        print("Generating PDF... This may take a while.")
        
        # Collect and sort image files
        image_files = collect_image_files()
        if not image_files:
            print("No image files found for PDF creation")
            return False
        
        # Create backup BEFORE generating PDF (in case PDF generation fails)
        create_backup(book_name)
        
        # Create PDF
        pdf = FPDF(format=PDF_DIMENSIONS)
        
        for image_path in image_files:
            try:
                pdf.add_page("P")
                pdf.image(image_path, 0, 0, *PDF_DIMENSIONS)
            except Exception as e:
                print(f"Failed to add image {image_path} to PDF: {e}")
                continue
        
        # Save PDF
        pdf_filename = f"{book_name}.pdf"
        pdf.output(pdf_filename)
        
        cleanup_temp_files()
        
        print(f"PDF '{pdf_filename}' created successfully!")
        return True
        
    except Exception as e:
        print(f"PDF creation failed: {e}")
        return False


def preserve_as_images(book_name, page_count):
    """Preserve images as directory."""
    try:
        # Create backup BEFORE renaming (in case rename fails)
        create_backup(book_name)
        
        target_dir = sanitize_filename(book_name) or DEFAULT_BOOK_NAME
        
        if os.path.exists(target_dir):
            target_dir = f"{target_dir}_backup"
            
        os.rename(TEMP_DIR, target_dir)
        
        print(f"Images preserved in '{target_dir}/' directory ({page_count} pages)")
        return True
        
    except Exception as e:
        print(f"Failed to preserve images: {e}")
        # Fallback to generic name
        try:
            os.rename(TEMP_DIR, DEFAULT_BOOK_NAME)
            print(f"Images preserved in '{DEFAULT_BOOK_NAME}/' directory")
            return True
        except Exception as fallback_error:
            print(f"Fallback preservation failed: {fallback_error}")
            return False


def create_backup(book_name):
    """Create backup of processed images."""
    try:
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        
        if os.path.exists(TEMP_DIR):
            backup_name = sanitize_filename(book_name) or f"backup_{int(time.time())}"
            backup_path = os.path.join(SAVE_DIR, backup_name)
            
            # Handle existing backup
            counter = 1
            original_backup_path = backup_path
            while os.path.exists(backup_path):
                backup_path = f"{original_backup_path}_{counter}"
                counter += 1
            
            shutil.copytree(TEMP_DIR, backup_path)
            print(f"Backup created: {backup_path}")
            
    except Exception as e:
        print(f"Backup creation failed: {e}")


def cleanup_temp_files():
    """Clean up temporary files."""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            print("Temporary files cleaned up")
    except Exception as e:
        print(f"Cleanup warning: {e}")


def process_output(book_name, page_count):
    """Process output based on user preference."""
    print("\nOutput Options:")
    print("1. Generate PDF from pages")
    print("2. Keep as image directory")
    print("3. Save backup and quit")
    
    choice = input("\nSelect option (1, 2, or 3): ").strip()
    
    if choice == "1":
        return create_pdf(book_name)
    elif choice == "2":
        return preserve_as_images(book_name, page_count)
    elif choice == "3":
        create_backup(book_name)
        print("Session completed successfully!")
        return True
    else:
        print("Invalid option. Please choose 1, 2, or 3.")
        return process_output(book_name, page_count)  # Recursive retry


# ============================================================================
# USER INTERACTION
# ============================================================================

def display_and_select_books(books):
    """Display available books and handle user selection."""
    print("\n📚 Available Books:")
    print("-" * 30)
    
    for book in books:
        print(f"({book['index']}) → {book['title']}")
    
    try:
        selection = input("\nWhich book would you like to backup? (Enter number): ").strip()
        book_index = int(selection)
        
        if 0 <= book_index < len(books):
            return books[book_index]
        else:
            print("❌ Invalid selection. Please choose a valid book number.")
            return None
            
    except ValueError:
        print("❌ Please enter a valid number.")
        return None
    except KeyboardInterrupt:
        return None


def confirm_book_selection(book):
    """Confirm book selection with user."""
    confirmation = input(f"\n📖 Backup '{book['title']}'? (yes/no): ").lower().strip()
    return confirmation in ('yes', 'y')

def double_page_mode_selection():
    anwser = input("\nUse double page mode? (yes/no): ").lower().strip()
    return anwser in ('yes', 'y')


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Main application workflow."""
    print("🎨 iPlus Interactif Backup Utility (Functional Edition)")
    print("=" * 50)
    
    driver = None
    
    try:
        # Step 1: Initialize driver
        driver = create_driver()
        
        # Step 2: Authentication
        if not authenticate(driver):
            print("❌ Authentication failed. Please check credentials.")
            return False
        
        # Step 3: Book Discovery and Selection
        books = discover_books(driver)
        if not books:
            print("❌ No books found. Please check website availability.")
            return False
        
        selected_book = display_and_select_books(books)
        if not selected_book:
            print("👋 No book selected. Goodbye!")
            return True
        
        # Step 4: User Confirmation
        if not confirm_book_selection(selected_book):
            print("👋 Operation cancelled. Goodbye!")
            return True
        
        # Step 5: Book and Volume Selection
        volume_name = select_book_and_volume(driver, selected_book)
        if volume_name is None:
            print("❌ Book selection failed or cancelled.")
            return False
        elif volume_name == "None":
            volume_name = None  # Single volume book
        
        # Step 5b: Page Disposition Selection
        double_page_mode = double_page_mode_selection()

        # Update book name with volume if applicable
        final_book_name = volume_name or selected_book['title']
        
        # Step 6: Open Book Viewer
        if not open_book_viewer(driver):
            print("❌ Failed to open book viewer.")
            return False
        
        # Step 6b: Set view mode
        if not set_view_mode(driver, double_page_mode):
            print("❌ Failed to set page view.")
            return False
        
        # Step 7: Process Images
        pages_processed, errors_encountered = process_book_pages(driver, double_page_mode)
        
        if pages_processed == 0:
            print("❌ No pages were processed successfully.")
            return False
        
        print(f"\n✅ Successfully processed {pages_processed} pages")
        
        if errors_encountered > 0:
            print(f"⚠️  Warnings: {errors_encountered} pages had issues")
        
        # Step 8: Output Processing
        process_output(final_book_name, pages_processed)
        
        print("\n🎉 Backup operation completed successfully!")
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user.")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
                print("Browser closed.")
            except Exception:
                pass


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        exit(0)
