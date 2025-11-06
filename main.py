#!/usr/bin/env python3
"""
iPlus Interactif Image Backup Utility - Professional Edition
A modular, maintainable solution for backing up books from iPlus Interactif website.

Author: Dave Erickson & Robert56s
Version: 2.0.0
Python: 3.7+
"""

import os
import time
import base64
import shutil
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager
import logging

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
# CONFIGURATION & CONSTANTS (Atomic Global Variables)
# ============================================================================

class Config:
    """Centralized configuration management for easy UI adaptation."""
    
    # Authentication
    DEFAULT_EMAIL = os.getenv('EMAIL')
    DEFAULT_PASSWORD = os.getenv('PASSWORD')
    
    # Website URLs and structure
    BASE_URL = "https://www.iplusinteractif.com/"
    
    # Selenium selectors (centralized for easy UI change adaptation)
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
        'next_arrow': '//*[@id="iplus-R-ReactPreviewFrame"]/div/div[2]/div[2]'
    }
    
    # Timing configurations
    TIMEOUTS = {
        'implicit_wait': 10,
        'page_load': 30,
        'image_processing': 5,
        'navigation': 3,
        'post_click': 1
    }
    
    # File system
    TEMP_DIR = "imgs"
    SAVE_DIR = "save"
    DEFAULT_BOOK_NAME = "book"
    IMAGE_FORMAT = "png"
    PDF_DIMENSIONS = (2640, 3263)  # Custom format for books


class OutputFormat(Enum):
    """Output format options for processed books."""
    PDF = "1"
    IMAGES = "2"
    QUIT = "3"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BookInfo:
    """Encapsulates book metadata and selection state."""
    index: int
    title: str
    element: Any
    selected_volume: Optional[str] = None


@dataclass
class ProcessingStats:
    """Tracks processing statistics for reporting."""
    pages_processed: int = 0
    errors_encountered: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0.0


# ============================================================================
# CORE AUTOMATION ENGINE
# ============================================================================

class SeleniumDriverManager:
    """Professional Selenium driver lifecycle management."""
    
    def __init__(self, headless: bool = False, detach: bool = True):
        self.headless = headless
        self.detach = detach
        self.driver: Optional[webdriver.Chrome] = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Initialize logging for driver operations."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _configure_chrome_options(self) -> Options:
        """Configure Chrome options with professional defaults."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        
        if self.detach:
            options.add_experimental_option("detach", True)
            
        # Performance and stability enhancements
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-logging")
        options.add_argument("--silent")
        options.add_argument("--log-level=3")
        
        return options
    
    @contextmanager
    def get_driver(self):
        """Context manager for safe driver lifecycle management."""
        try:
            options = self._configure_chrome_options()
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(Config.TIMEOUTS['implicit_wait'])
            self.driver.maximize_window()
            
            self.logger.info("Chrome driver initialized successfully")
            yield self.driver
            
        except Exception as e:
            self.logger.error(f"Driver initialization failed: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Ensure proper driver cleanup."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome driver cleaned up successfully")
            except Exception as e:
                self.logger.warning(f"Driver cleanup warning: {e}")


class iPlusInteractifNavigator:
    """High-level navigation and interaction with iPlus Interactif website."""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, Config.TIMEOUTS['page_load'])
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, email: str = Config.DEFAULT_EMAIL, 
                    password: str = Config.DEFAULT_PASSWORD) -> bool:
        """Perform user authentication with enhanced error handling."""
        try:
            self.logger.info("Starting authentication process")
            self.driver.get(Config.BASE_URL)
            
            # Email input
            email_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, Config.SELECTORS['login_email']))
            )
            email_element.clear()
            email_element.send_keys(email)
            
            # Password input
            password_element = self.driver.find_element(By.XPATH, Config.SELECTORS['login_password'])
            password_element.clear()
            password_element.send_keys(password)
            
            # Submit login
            login_button = self.driver.find_element(By.XPATH, Config.SELECTORS['login_button'])
            login_button.click()
            
            time.sleep(Config.TIMEOUTS['post_click'])
            
            # Handle cookies popup if present
            self._handle_cookies_popup()
            
            self.logger.info("Authentication completed successfully")
            return True
            
        except TimeoutException:
            self.logger.error("Authentication timeout - UI elements not found")
            return False
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def _handle_cookies_popup(self):
        """Handle cookies popup with graceful fallback."""
        try:
            cookies_button = self.driver.find_element(By.ID, Config.SELECTORS['cookies_reject'])
            if cookies_button.is_displayed():
                cookies_button.click()
                self.logger.info("Cookies popup handled")
        except NoSuchElementException:
            self.logger.info("No cookies popup detected")
    
    def discover_books(self) -> List[BookInfo]:
        """Discover and catalog available books."""
        time.sleep(Config.TIMEOUTS['navigation'])  # Allow page to stabilize
        
        try:
            book_elements = self.driver.find_elements(By.XPATH, Config.SELECTORS['book_containers'])
            books = []
            
            for index, element in enumerate(book_elements):
                try:
                    title_element = element.find_element(By.XPATH, Config.SELECTORS['book_title'])
                    title = title_element.text.strip()
                    
                    books.append(BookInfo(
                        index=index,
                        title=title,
                        element=element
                    ))
                    
                except NoSuchElementException:
                    self.logger.warning(f"Could not extract title for book at index {index}")
                    continue
            
            self.logger.info(f"Discovered {len(books)} books")
            return books
            
        except Exception as e:
            self.logger.error(f"Book discovery failed: {e}")
            return []
    
    def select_book_and_volume(self, book: BookInfo) -> Optional[str]:
        """Select a book and handle volume selection if necessary."""
        try:
            book.element.click()
            time.sleep(Config.TIMEOUTS['navigation'])
            
            # Switch to new window
            self.driver.switch_to.window(self.driver.window_handles[1])
            
            # Handle commercial popup
            self._handle_commercial_popup()
            
            # Check for multiple volumes
            selected_volume = self._handle_volume_selection()
            if selected_volume is False:  # User cancelled volume selection
                return None
                
            book.selected_volume = selected_volume
            return selected_volume
            
        except Exception as e:
            self.logger.error(f"Book selection failed: {e}")
            return None
    
    def _handle_commercial_popup(self):
        """Handle commercial popup with graceful fallback."""
        try:
            close_popup = self.driver.find_element(By.XPATH, Config.SELECTORS['popup_close'])
            close_popup.click()
            self.logger.info("Commercial popup closed")
        except NoSuchElementException:
            self.logger.info("No commercial popup detected")
    
    def _handle_volume_selection(self) -> Optional[str]:
        """Handle volume selection for multi-volume books."""
        try:
            nav_volumes = self.driver.find_elements(By.XPATH, Config.SELECTORS['nav_volumes'])
            
            if not nav_volumes:
                return "None"  # Single volume book
                
            print(f"\nMultiple volumes detected. Please select:")
            
            for volume in nav_volumes:
                try:
                    vol_title = volume.find_element(By.XPATH, Config.SELECTORS['volume_title']).text
                    choice = input(f"Save volume '{vol_title}'? (yes/no): ").lower().strip()
                    
                    if choice == 'yes':
                        volume.click()
                        self.logger.info(f"Selected volume: {vol_title}")
                        return vol_title
                    elif choice == 'no':
                        print("Volume skipped.")
                        continue
                        
                except Exception as e:
                    self.logger.warning(f"Error processing volume: {e}")
                    continue
            
            print("No volumes selected.")
            return False  # Signal user cancellation
            
        except Exception as e:
            self.logger.error(f"Volume selection failed: {e}")
            return None
    
    def open_book_viewer(self) -> bool:
        """Open the book viewer and navigate to first page."""
        try:
            time.sleep(Config.TIMEOUTS['post_click'])
            
            open_book_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, Config.SELECTORS['open_book']))
            )
            open_book_button.click()
            
            time.sleep(Config.TIMEOUTS['navigation'])
            
            # Navigate to cover page (C1)
            page_input = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, Config.SELECTORS['page_input']))
            )
            page_input.clear()
            page_input.send_keys('C1')
            page_input.send_keys(u'\ue007')  # Enter key
            
            time.sleep(Config.TIMEOUTS['navigation'])
            
            self.logger.info("Book viewer opened successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to open book viewer: {e}")
            return False


# ============================================================================
# IMAGE PROCESSING ENGINE
# ============================================================================

class ImageProcessor:
    """Professional image extraction and processing system."""
    
    def __init__(self, driver: webdriver.Chrome, output_dir: str = Config.TEMP_DIR):
        self.driver = driver
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        self.stats = ProcessingStats()
        self._ensure_output_directory()
    
    def _ensure_output_directory(self):
        """Ensure output directory exists."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Created output directory: {self.output_dir}")
    
    def process_book_pages(self) -> ProcessingStats:
        """Process all pages in the current book."""
        self.stats = ProcessingStats()
        self.stats.start_time = time.time()
        
        try:
            while True:
                success = self._process_current_page()
                if not success:
                    break
                    
                if not self._navigate_to_next_page():
                    self.logger.info("Reached end of book")
                    break
                    
                self.stats.pages_processed += 1
                time.sleep(Config.TIMEOUTS['post_click'])
            
        except Exception as e:
            self.logger.error(f"Page processing error: {e}")
            self.stats.errors_encountered += 1
        finally:
            self.stats.end_time = time.time()
            
        self.logger.info(f"Processing complete: {self.stats.pages_processed} pages processed")
        return self.stats
    
    def _process_current_page(self) -> bool:
        """Process the current page image."""
        try:
            # Locate main image
            image_element = self.driver.find_element(By.XPATH, Config.SELECTORS['main_image'])
            img_src = image_element.get_attribute("src")
            
            if not img_src:
                self.logger.warning("No image source found")
                return False
            
            # Open image in new tab
            self.driver.execute_script(f'window.open("{img_src}","_blank");')
            self.driver.switch_to.window(self.driver.window_handles[2])
            
            time.sleep(Config.TIMEOUTS['post_click'])
            
            # Click to ensure image is loaded
            page_image = self.driver.find_element(By.XPATH, "//img")
            page_image.click()
            time.sleep(0.3)
            
            # Extract image using JavaScript canvas technique
            base64_data = self._extract_image_as_base64()
            if not base64_data:
                return False
            
            # Save image
            self._save_base64_image(base64_data, self.stats.pages_processed)
            
            # Cleanup - close current tab and return to book viewer
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[1])
            
            print(f'Page #{self.stats.pages_processed} saved successfully')
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing page {self.stats.pages_processed}: {e}")
            self.stats.errors_encountered += 1
            return False
    
    def _extract_image_as_base64(self) -> Optional[str]:
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
            base64_img = self.driver.execute_script(js_script)
            return base64_img.split(',')[1] if base64_img else None
        except Exception as e:
            self.logger.error(f"JavaScript extraction failed: {e}")
            return None
    
    def _save_base64_image(self, base64_data: str, page_number: int):
        """Save base64 image data to file."""
        try:
            image_data = base64.b64decode(base64_data)
            file_path = os.path.join(self.output_dir, f"{page_number}.{Config.IMAGE_FORMAT}")
            
            with open(file_path, 'wb') as f:
                f.write(image_data)
                
        except Exception as e:
            self.logger.error(f"Failed to save image {page_number}: {e}")
            raise
    
    def _navigate_to_next_page(self) -> bool:
        """Navigate to the next page if available."""
        try:
            next_element = self.driver.find_element(By.XPATH, Config.SELECTORS['next_arrow'])
            self.driver.execute_script("arguments[0].click();", next_element)
            return True
        except NoSuchElementException:
            return False  # No more pages
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False


# ============================================================================
# OUTPUT PROCESSING SYSTEM
# ============================================================================

class OutputProcessor:
    """Professional output processing and file management."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_output(self, book_name: str, page_count: int) -> bool:
        """Process output based on user preference."""
        print("\nOutput Options:")
        print("1. Generate PDF from pages")
        print("2. Keep as image directory")
        print("3. Save backup and quit")
        
        choice = input("\nSelect option (1, 2, or 3): ").strip()
        
        try:
            if choice == OutputFormat.PDF.value:
                return self._create_pdf(book_name)
            elif choice == OutputFormat.IMAGES.value:
                return self._preserve_as_images(book_name, page_count)
            elif choice == OutputFormat.QUIT.value:
                print("Session completed successfully!")
                return True
            else:
                print("Invalid option. Please choose 1, 2, or 3.")
                return self.process_output(book_name, page_count)  # Recursive retry
                
        finally:
            self._create_backup(book_name)
    
    def _create_pdf(self, book_name: str) -> bool:
        """Create PDF from processed images."""
        try:
            print("Generating PDF... This may take a while.")
            
            # Collect and sort image files
            image_files = self._collect_image_files()
            if not image_files:
                self.logger.error("No image files found for PDF creation")
                return False
            
            # Create PDF
            pdf = FPDF(format=Config.PDF_DIMENSIONS)
            
            for image_path in image_files:
                try:
                    pdf.add_page("P")
                    pdf.image(image_path, 0, 0, *Config.PDF_DIMENSIONS)
                except Exception as e:
                    self.logger.warning(f"Failed to add image {image_path} to PDF: {e}")
                    continue
            
            # Save PDF
            pdf_filename = f"{book_name}.pdf"
            pdf.output(pdf_filename, "F")
            
            self._cleanup_temp_files()
            
            print(f"PDF '{pdf_filename}' created successfully!")
            self.logger.info(f"PDF created: {pdf_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"PDF creation failed: {e}")
            return False
    
    def _preserve_as_images(self, book_name: str, page_count: int) -> bool:
        """Preserve images as directory."""
        try:
            target_dir = self._sanitize_filename(book_name) or Config.DEFAULT_BOOK_NAME
            
            if os.path.exists(target_dir):
                target_dir = f"{target_dir}_backup"
                
            os.rename(Config.TEMP_DIR, target_dir)
            
            print(f"Images preserved in '{target_dir}/' directory ({page_count} pages)")
            self.logger.info(f"Images preserved: {target_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to preserve images: {e}")
            # Fallback to generic name
            try:
                os.rename(Config.TEMP_DIR, Config.DEFAULT_BOOK_NAME)
                print(f"Images preserved in '{Config.DEFAULT_BOOK_NAME}/' directory")
                return True
            except Exception as fallback_error:
                self.logger.error(f"Fallback preservation failed: {fallback_error}")
                return False
    
    def _collect_image_files(self) -> List[str]:
        """Collect and sort image files numerically."""
        try:
            image_files = []
            
            for filename in os.listdir(Config.TEMP_DIR):
                if filename.endswith(f".{Config.IMAGE_FORMAT}") and filename[:-4].isdigit():
                    image_files.append(os.path.join(Config.TEMP_DIR, filename))
            
            # Sort numerically by filename
            image_files.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
            
            return image_files
            
        except Exception as e:
            self.logger.error(f"Failed to collect image files: {e}")
            return []
    
    def _create_backup(self, book_name: str):
        """Create backup of processed images."""
        try:
            if not os.path.exists(Config.SAVE_DIR):
                os.makedirs(Config.SAVE_DIR)
            
            if os.path.exists(Config.TEMP_DIR):
                backup_name = self._sanitize_filename(book_name) or f"backup_{int(time.time())}"
                backup_path = os.path.join(Config.SAVE_DIR, backup_name)
                
                # Handle existing backup
                counter = 1
                original_backup_path = backup_path
                while os.path.exists(backup_path):
                    backup_path = f"{original_backup_path}_{counter}"
                    counter += 1
                
                shutil.copytree(Config.TEMP_DIR, backup_path)
                self.logger.info(f"Backup created: {backup_path}")
                
        except Exception as e:
            self.logger.warning(f"Backup creation failed: {e}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            if os.path.exists(Config.TEMP_DIR):
                shutil.rmtree(Config.TEMP_DIR)
                self.logger.info("Temporary files cleaned up")
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        if not filename:
            return ""
            
        # Remove or replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Limit length and strip whitespace
        return filename.strip()[:200]


# ============================================================================
# MAIN APPLICATION ORCHESTRATOR
# ============================================================================

class iPlusInteractifBackupUtility:
    """Main application orchestrator - The conductor of our automation symphony."""
    
    def __init__(self):
        self.driver_manager = SeleniumDriverManager()
        self.output_processor = OutputProcessor()
        self.logger = logging.getLogger(__name__)
        
        print("🎨 iPlus Interactif Professional Backup Utility v2.0")
        print("=" * 50)
    
    def run(self):
        """Execute the complete backup workflow."""
        try:
            with self.driver_manager.get_driver() as driver:
                navigator = iPlusInteractifNavigator(driver)
                
                # Step 1: Authentication
                if not navigator.authenticate():
                    print("❌ Authentication failed. Please check credentials.")
                    return False
                
                # Step 2: Book Discovery and Selection
                books = navigator.discover_books()
                if not books:
                    print("❌ No books found. Please check website availability.")
                    return False
                
                selected_book = self._display_and_select_books(books)
                if not selected_book:
                    print("👋 No book selected. Goodbye!")
                    return True
                
                # Step 3: User Confirmation
                if not self._confirm_book_selection(selected_book):
                    print("👋 Operation cancelled. Goodbye!")
                    return True
                
                # Step 4: Book and Volume Selection
                volume_name = navigator.select_book_and_volume(selected_book)
                if volume_name is None:
                    print("❌ Book selection failed or cancelled.")
                    return False
                elif volume_name == "None":
                    volume_name = None  # Single volume book
                
                # Update book name with volume if applicable
                final_book_name = volume_name or selected_book.title
                
                # Step 5: Open Book Viewer
                if not navigator.open_book_viewer():
                    print("❌ Failed to open book viewer.")
                    return False
                
                # Step 6: Process Images
                processor = ImageProcessor(driver)
                stats = processor.process_book_pages()
                
                if stats.pages_processed == 0:
                    print("❌ No pages were processed successfully.")
                    return False
                
                print(f"\n✅ Successfully processed {stats.pages_processed} pages")
                print(f"⏱️  Processing time: {stats.duration:.2f} seconds")
                
                if stats.errors_encountered > 0:
                    print(f"⚠️  Warnings: {stats.errors_encountered} pages had issues")
                
                # Step 7: Output Processing
                self.output_processor.process_output(final_book_name, stats.pages_processed)
                
                print("\n🎉 Backup operation completed successfully!")
                return True
                
        except KeyboardInterrupt:
            print("\n⏹️  Operation cancelled by user.")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            print(f"❌ An unexpected error occurred: {e}")
            return False
    
    def _display_and_select_books(self, books: List[BookInfo]) -> Optional[BookInfo]:
        """Display available books and handle user selection."""
        print("\n📚 Available Books:")
        print("-" * 30)
        
        for book in books:
            print(f"({book.index}) → {book.title}")
        
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
    
    def _confirm_book_selection(self, book: BookInfo) -> bool:
        """Confirm book selection with user."""
        confirmation = input(f"\n📖 Backup '{book.title}'? (yes/no): ").lower().strip()
        return confirmation in ('yes', 'y')


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

def main():
    """Application entry point with professional error handling."""
    try:
        utility = iPlusInteractifBackupUtility()
        success = utility.run()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
