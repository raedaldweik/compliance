import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Dict, Optional

# Function to get updates from the website
def get_updates() -> List[Dict[str, str]]:
    """
    Retrieves a list of the most recent updates from the UAE Central Bank rulebook website.
    """
    updates_list = []
    try:
        # URL to fetch updates from the last 5 days
        url = "https://rulebook.centralbank.ae/en/view-revision-updates?f_days=on&changed=-5+day&changed_1%5Bmin%5D=&changed_1%5Bmax%5D="
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all update entries
        headlines = soup.find_all("div", class_="book-detail")
        trails = soup.find_all("div", class_="book-trail")

        # Check if there are any updates
        if not headlines:
            return updates_list

        # Iterate over the updates and extract details
        for headline, trail in zip(headlines, trails):
            title = headline.find("a").text.strip()
            date = headline.find("time").text.strip()
            link = headline.find("a")["href"]
            full_link = f"https://rulebook.centralbank.ae{link}"
            body = trail.find("span", class_="field-content").text.strip()

            updates_list.append({
                "title": title,
                "date": date,
                "link": full_link,
                "body": body
            })

    except requests.exceptions.RequestException as e:
        print(f"Error fetching updates: {e}")
        sys.exit(1)

    return updates_list

# Function to load the last saved updates
def load_last_updates(filename: str = "last_updates.json") -> Optional[List[Dict[str, str]]]:
    """
    Loads the last saved updates from a JSON file.
    """
    file_path = Path(filename)
    if file_path.exists():
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    return None

# Function to get new updates by comparing with the last saved updates
def get_new_updates(current_updates: List[Dict[str, str]], last_updates: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """
    Compares current updates with the last saved updates to find new updates.
    """
    if not last_updates:
        return current_updates

    # Assuming updates are sorted by date in descending order
    last_update_titles = {update['title'] for update in last_updates}
    new_updates = [update for update in current_updates if update['title'] not in last_update_titles]
    return new_updates

# Function to save the current updates
def save_updates(updates: List[Dict[str, str]], filename: str = "last_updates.json"):
    """
    Saves the current updates to a JSON file.
    """
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(updates, file, ensure_ascii=False, indent=4)

# Function to send email notifications
def send_email(new_updates: List[Dict[str, str]], recipients: List[str]):
    """
    Sends an email notification to the specified recipients about new updates.
    """
    # Import inside the function to prevent import error if not needed
    from postmarker.core import PostmarkClient
    from dotenv import dotenv_values

    # Load Postmark API key from .env file
    config = dotenv_values(".env")
    pm_api_key = config.get("POSTMARK_API_KEY")

    if not pm_api_key:
        print("Error: POSTMARK_API_KEY not found in .env file.")
        sys.exit(1)

    client = PostmarkClient(server_token=pm_api_key)

    subject = f"UAE Central Bank Rulebook Updates - {datetime.now().strftime('%d %B %Y')}"
    message_plural = "updates" if len(new_updates) > 1 else "update"

    # Construct the email content
    content = f"""
    <html>
    <body>
        <p>We found {len(new_updates)} new {message_plural} added to the Central Bank Rulebook:</p>
    """

    for update in new_updates:
        content += f"""
        <p>
            <strong>{update['title']}</strong><br>
            {update['body']}<br>
            Date: {update['date']}<br>
            <a href="{update['link']}">Read more</a>
        </p>
        """

    content += """
        <p>
            <em>
                You are receiving this email as part of an initiative to keep stakeholders informed of updates to the Central Bank Rulebook.
                If you'd like to be removed from this mailing list, please contact us.
            </em>
        </p>
    </body>
    </html>
    """

    # Send the email
    try:
        response = client.emails.send(
            From="raed.aldweik@sas.com",
            To=recipients,
            Subject=subject,
            HtmlBody=content,
        )
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        sys.exit(1)

# Main execution
if __name__ == "__main__":
    print("Starting script...")
    current_updates = get_updates()
    if not current_updates:
        print("No updates found.")
        sys.exit(0)

    last_updates = load_last_updates()
    new_updates = get_new_updates(current_updates, last_updates)

    if not new_updates:
        print("No new updates since last check.")
        sys.exit(0)

    print(f"Found {len(new_updates)} new updates.")

    # Save the current updates
    save_updates(current_updates)

    # Define the list of recipients
    recipients = [
        "raed.aldweik@sas.com"
        # Add more recipients as needed
    ]

    # Send email notifications
    send_email(new_updates, recipients)
    print("Script completed successfully.")
