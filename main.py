from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import base64
import os
import shutil
from fpdf import FPDF

from dotenv import load_dotenv
load_dotenv()


def main():
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')

    print("Initializing...")

    options = Options()
    # options.add_argument("--headless")  # Add this line to run Chrome in headless mode
    options.add_experimental_option("detach", True)

    # remove useless console logs
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager('').install()), options=options)

    driver.get("https://www.iplusinteractif.com/")
    driver.maximize_window()

    emailElement = driver.find_element("xpath", "//*[@id='loginId']")
    emailElement.click()
    emailElement.send_keys(email)

    passwordElement = driver.find_element("xpath", "//*[@id='password']")
    passwordElement.click()
    passwordElement.send_keys(password)

    sendButton = driver.find_element(
        "xpath", "//*[contains(@class, 'blue button')]")
    sendButton.click()

    time.sleep(1)

    cookiesElement = driver.find_element("id", "onetrust-reject-all-handler")
    if cookiesElement: 
        cookiesElement.click()
    
    time.sleep(4)

    accessListElements = driver.find_elements(
        "xpath", "//div[contains(@class, 'accessContainer')]")
    
    
    print("Books found:")
    for index, element in enumerate(accessListElements):
        bookName = element.find_element("xpath", ".//h2[@class='access__title']").text
        print(f"({index}) -> {bookName}")
    
    print("\n")
    try:
        bookIndex = int(input("Which book do you want to copy? (Enter the number): "))
    except:
        print("Please enter a number retard.")
        quit()

    element = accessListElements[bookIndex]
    bookName = element.find_element("xpath", ".//h2[@class='access__title']").text

    question1 = input(f"Do you want to copy {bookName}? (yes/no): ")
    if question1 == "yes":

        element.click()
        time.sleep(3)

        driver.switch_to.window(driver.window_handles[1])

        try:
            closePopup = driver.find_element(
                "xpath", "//*[@class='iplus-l-confBook__commercialPopupCloseBtnTop']")
            closePopup.click()
            print("popup closed")
        except:
            print("no popup")
        
        try:
            anotherClosePopup = driver.find_element(
                "xpath", '//*[@id="commercialpopup"]/div[1]/span[2]')
            anotherClosePopup.click()
            print("another popup closed")
        except:
            print("another no popup")

        navVolumes = driver.find_elements("xpath", '//*[@id="iplus-R-confBook"]/div[1]/div/ul/li')
        if navVolumes:
            print(f"Multiple volumes found for {bookName}. Please select the volume you want to copy.")
            volSelected = False
            for volume in navVolumes:
                volName = volume.find_element("xpath", ".//h3").text
                q = input(f"Do you want to copy {volName}? (yes/no): ")
                if q == "yes":
                    bookName = volName
                    volume.click()
                    volSelected = True
                    break
                else:
                    print("Volume skipped.")

            if not volSelected:
                print("There are no volumes left for this book. Try again.")   
                quit()

        time.sleep(1)
        openBook = driver.find_element(
            "xpath", "//a[@class='iplus-l-confBook__itemVolumeCouv coverEffect']")
        openBook.click()
        time.sleep(3)
        pageInput = driver.find_element(
            "xpath", "//input[@class='iplus-R-ReactPreviewFrame__pagination_input']")
        pageInput.send_keys('C1')
        pageInput.send_keys(u'\ue007')
        time.sleep(3)

        # Create the directory if it doesn't exist
        if not os.path.exists("imgs"):
            os.makedirs("imgs")

        img_count = 1
        while True:

            image = driver.find_element(
                "xpath", '//*[@id="iplus-R-ReactPreviewFrame"]/div/div[2]/div/div/div[1]/img')
            img_src = image.get_attribute("src")

            driver.execute_script(
                f'''window.open("{img_src}","_blank");''')
            driver.switch_to.window(driver.window_handles[2])
            time.sleep(1)
            page = driver.find_element("xpath", "//img")
            page.click()
            time.sleep(0.3)
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

            # Specify the file name and format (e.g., 'output.png' for PNG)
            file_path = os.path.join("imgs", f"{img_count}.png")

            # Save the image to a file
            with open(file_path, 'wb') as f:
                f.write(image_data)

            print(f'Page #{img_count} saved in {file_path}')

            driver.close()
            driver.switch_to.window(driver.window_handles[1])

            try:
                next_element = driver.find_element(
                    "xpath", "//div[@class='sc-hKMtZM ehqEaE iplus-l-ReactPreviewFrame__paginationArrow__arrowRight']")
            except:
                print(
                    f"{img_count} pages from {bookName} was copied successfully!")
                break
            driver.execute_script("arguments[0].click();", next_element)

            img_count += 1

            time.sleep(3)

        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        driver.quit()
        png_to_pdf(bookName, img_count)

    else:
        print("ok, bye!")
        quit()
    time.sleep(1)


def png_to_pdf(bookName, img_count):
    question = input(
        "\nWhat would you prefer?\nMake a pdf with the copied pages (1)\nKeep the copied pages as a directory of images (2)\nQuit (3)\n\nAnswer (1, 2 or 3): ")

    if question == "1":

        print("loading ...\nThis could take a while. Please wait.")

        # Initialize a list to store image file paths
        image_files = []

        # Iterate through the files in the directory and add numeric names to the list
        for filename in os.listdir("imgs"):
            if filename.endswith(".png") and filename[:-4].isnumeric():
                image_files.append(os.path.join("imgs", filename))

        # Sort the image file paths based on their names (which are assumed to be integers)
        image_files.sort(key=lambda x: int(os.path.basename(x)[:-4]))

        # test_images = [ os.path.join("imgs", "1.png"), os.path.join("imgs", "2.png"), os.path.join("imgs", "3.png")]
        # # imagelist is the list with all image filenames
        # print(test_images)

        pdf = FPDF()

        for image in image_files:
            pdf.add_page("P", (2640, 3263))
            pdf.image(image, 0, 0, 2640, 3263)
        pdf.output(f"{bookName}.pdf")

        save_progress(bookName)
        clear_imgs()
        print(f"PDF file '{bookName}' created successfully.")

    elif question == "2":

        save_progress(bookName)

        try:
            os.rename("imgs", bookName)
            print(f"You can find {img_count} pages in /{bookName}")
        except:
            os.rename("imgs", "book")
            print(
                f"Your book has a weird name.\nYou can find {img_count} pages in /book")

    elif question == "3":
        print("You successfully quited!")
        save_progress(bookName)
        clear_imgs()

    else:
        print("Chose an option between 1, 2 and 3")
        png_to_pdf()


def save_progress(bookName):

    # Create the directory if it doesn't exist
    if not os.path.exists("save"):
        os.makedirs("save")

    try:
        shutil.copytree("imgs", os.path.join("save", bookName))

    except shutil.Error as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def clear_imgs():
    try:
        shutil.rmtree("imgs")

    except Exception as e:
        print(f"Error: {e}")


main()


# png_to_pdf("bookName", num_of_pages)   
