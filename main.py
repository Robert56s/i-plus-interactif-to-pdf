from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import base64
import os
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, PageTemplate, PageBreak, Image
import io


email = "robertnelea56@gmail.com"
password = "Stonksr10056!"

options = Options()
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.iplusinteractif.com/")
driver.maximize_window()

emailElement = driver.find_element("xpath", "//*[@id='loginId']")
emailElement.click()
emailElement.send_keys(email)

passwordElement = driver.find_element("xpath", "//*[@id='password']")
passwordElement.click()
passwordElement.send_keys(password)

sendButton = driver.find_element("xpath", "//*[contains(@class, 'blue button')]")
sendButton.click()

time.sleep(5)
accessListElements = driver.find_elements("xpath", "//div[contains(@class, 'accessContainer')]")
for element in accessListElements:
    bookName = element.find_element("xpath", ".//h2[@class='access__title']").text
    question = input(f"Do you want to copy {bookName}? (yes/no):")
    if question == "yes":
        element.click()
        time.sleep(3)

        driver.switch_to.window(driver.window_handles[1])

        try:
            closePopup = driver.find_element("xpath", "//*[@class='iplus-l-confBook__commercialPopupCloseBtnTop']")
            closePopup.click()
            print("popup closed")
        except:
            print("no popup")
         
        time.sleep(1)
        openBook = driver.find_element("xpath", "//a[@class='iplus-l-confBook__itemVolumeCouv coverEffect']")
        openBook.click()
        time.sleep(3)
        pageInput = driver.find_element("xpath", "//input[@class='iplus-R-ReactPreviewFrame__pagination_input']")
        pageInput.send_keys('C1')
        pageInput.send_keys(u'\ue007')
        time.sleep(3)

        image = driver.find_element("xpath", "//img[@class='iplus-R-ReactPreviewFrame__page ']")
        img_src = image.get_attribute("src")

        driver.execute_script(f'''window.open("{img_src}","_blank");''')
        driver.switch_to.window(driver.window_handles[2])
        time.sleep(1)
        page = driver.find_element("xpath", "//img")
        page.click()
        time.sleep(1)
        js = '''// Select the image element on the page
                var imgElement = document.querySelector('img');

                // Create a canvas element to draw the image
                var canvas = document.createElement('canvas');
                canvas.width = imgElement.width;
                canvas.height = imgElement.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(imgElement, 0, 0, imgElement.width, imgElement.height);

                // Get the base64 data URL
                var base64Data = canvas.toDataURL('image/png'); // You can change the format as needed

                return base64Data
            '''
        base64_img = driver.execute_script(js)

        # Extract the base64 data part (after the comma)
        base64_data = base64_img.split(',')[1]

        # Decode the base64 data
        image_data = base64.b64decode(base64_data)

        
        # Create the directory if it doesn't exist
        if not os.path.exists("output"):
            os.makedirs("output")     

        # Specify the file name and format (e.g., 'output.png' for PNG)
        file_path = os.path.join("output",f"{bookName}.png" )
    
        # Save the image to a file
        with open(file_path, 'wb') as f:
            f.write(image_data)

        print(f'Image saved as {bookName} in {file_path}')


        #create pdf
        # Create a PDF document
        c = canvas.Canvas(f"{bookName}.pdf", pagesize=letter)

        # Create an image reader from the decoded image data
        img_reader = ImageReader(io.BytesIO(image_data))

        # Get image dimensions using getSize() method
        img_width, img_height = img_reader.getSize()

        # Calculate the aspect ratio
        aspect_ratio = float(img_width) / float(img_height)

        # Set the page size while maintaining the aspect ratio
        if aspect_ratio >= 1.0:
            page_width = letter[0]
            page_height = letter[0] / aspect_ratio
        else:
            page_height = letter[1]
            page_width = letter[1] * aspect_ratio

        c.setPageSize((page_width, page_height))

        # Calculate the scaling factor to fit the entire image on the page
        scaling_factor = min(page_width / img_width, page_height / img_height)

        # Calculate the image dimensions with scaling
        img_width_scaled = img_width * scaling_factor
        img_height_scaled = img_height * scaling_factor

        # Center the image on the page
        x_offset = (page_width - img_width_scaled) / 2
        y_offset = (page_height - img_height_scaled) / 2

        # Draw the image on the page with scaling
        c.drawImage(img_reader, x_offset, y_offset, img_width_scaled, img_height_scaled)

        # # Add a new page for the next image (if not the last one)
        # if base64_image_data != base64_images[-1]:
        c.showPage()

        c.save()

        driver.close()
        driver.switch_to.window(driver.window_handles[1])
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        


    else:
        print(f"{bookName} was successfully skiped.")
    time.sleep(1)