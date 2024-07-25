from flask import Flask, render_template, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import os
import time
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Environment variables for credentials
AZURE_USERNAME = os.getenv('AZURE_USERNAME')
AZURE_PASSWORD = os.getenv('AZURE_PASSWORD')
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.getenv('SLACK_CHANNEL_ID')  # Change to your Slack channel

client = WebClient(token=SLACK_BOT_TOKEN)

def take_screenshot():
    options = Options()
    options.headless = False  # Set to True to run headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1920,1080")
    
    service = Service(executable_path="C:\\webdriver\\chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    screenshot_folder = os.path.join(app.root_path, 'static')
    os.makedirs(screenshot_folder, exist_ok=True)  # Ensure the static directory exists
    screenshot_path = os.path.join(screenshot_folder, 'screenshot.png')

    try:
        driver.get("https://www.microsoftazuresponsorships.com/Balance")
        print("Navigated to Balance page")

        # Wait for the username field to be present
        username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "i0116")))
        username_field.send_keys(AZURE_USERNAME)
        print("Username entered")
        
        driver.find_element(By.ID, "idSIButton9").click()
        print("Clicked next button after entering username")
        time.sleep(2)  # Adjust sleep time if needed

        # Wait for the password field to be present
        password_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "i0118")))
        password_field.send_keys(AZURE_PASSWORD)
        print("Password entered")
        
        driver.find_element(By.ID, "idSIButton9").click()
        print("Clicked next button after entering password")
        
        time.sleep(2)  # Adjust sleep time if needed

        # Wait for the "No" button to be present and click it
        no_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "declineButton")))
        no_button.click()
        print("Clicked 'No' button")
        
        time.sleep(2)  # Adjust sleep time if needed

        # Navigate to the balance page again to ensure it loads correctly
        driver.get("https://www.microsoftazuresponsorships.com/Balance")
        print("Navigated to Balance page again")

        # Wait for the main page to load
        balance_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main-content-section")))  # Adjust the element ID
        print("Balance page loaded")
        
        if driver.save_screenshot(screenshot_path):
            print(f"Screenshot successfully saved at {screenshot_path}")
            # Upload the screenshot to Slack
            send_screenshot_to_slack(screenshot_path)
        else:
            print("Failed to save screenshot.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        driver.quit()

def send_screenshot_to_slack(screenshot_path):
    try:
        with open(screenshot_path, "rb") as file:
            response = client.files_upload_v2(
                channel=SLACK_CHANNEL_ID,
                initial_comment="Here is the latest Azure balance screenshot.",
                file=file
            )
        assert response["file"]  # the uploaded file
        print("Screenshot uploaded to Slack successfully")
    except SlackApiError as e:
        print(f"Failed to upload screenshot to Slack: {e.response['error']}")
        if e.response['error'] == 'not_in_channel':
            print("Invite the bot to the channel by typing '/invite @your-bot-name' in the channel.")
        elif e.response['error'] == 'channel_not_found':
            print("Make sure the channel ID is correct and the bot has access to it.")

@app.route('/show-screenshot')
def show_screenshot():
    return render_template('show_screenshot.html', screenshot_url=url_for('static', filename='screenshot.png'))


take_screenshot()

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(take_screenshot, 'interval', seconds=35)
    scheduler.start()
    
    # To keep the main thread alive and allow the scheduler to run in the background
    try:
        app.run(host='0.0.0.0', port=5000, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
