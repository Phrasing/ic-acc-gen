import asyncio
import email
import imaplib
import os
import re
from typing import Optional

import names

try:
    from nodriver import *
except (ModuleNotFoundError, ImportError):
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from nodriver import *


async def get_code(mail: imaplib.IMAP4_SSL, email_address: str) -> Optional[str]:
    mail.select("INBOX")

    search_criteria = 'FROM "no-reply@instacart.com" SUBJECT "is your Instacart verification code"'
    _, data = mail.search(None, search_criteria)

    code_pattern = re.compile(r"(\d{6}) is your Instacart verification code")
    email_ids = data[0].split()[::-1][:1]  # Only get the last email

    for num in email_ids:
        _, email_data = mail.fetch(num, "(RFC822)")
        email_message = email.message_from_bytes(email_data[0][1])

        subject = email_message['Subject']
        to_address = email_message['To']

        if to_address == email_address:
            code_match = code_pattern.search(subject)
            return code_match.group(1) if code_match else "Unknown"

    return None


async def search_emails(email_address: str) -> Optional[str]:
    result = None

    imap_server = "imap.gmail.com"
    imap_port = 993

    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(os.getenv("IMAP_EMAIL"), os.getenv("IMAP_PASSWORD"))

    try:
        while result is None:
            print("Waiting for code...")
            result = await get_code(mail, email_address)
            await asyncio.sleep(1)
    finally:
        mail.close()
        mail.logout()

    return result


async def wait_for_code(email_address: str, timeout: int = 30) -> str:
    start_time = asyncio.get_event_loop().time()

    while True:
        code = await search_emails(email_address)
        if code:
            return code

        elapsed_time = asyncio.get_event_loop().time() - start_time
        if elapsed_time > timeout:
            raise TimeoutError("Timed out waiting for code.")

        await asyncio.sleep(1)


async def run():
    browser = await start(
        browser_executable_path=r'C:\Users\Mark\AppData\Local\Chromium\Application\chrome.exe', 
        headless=False
    )

    page = await browser.get('https://www.google.com')
    await page.get_content()
    await page.scroll_down(150)
    await page.wait(2)

    page = await browser.get('https://instacart.com', new_tab=False)
    await page.get_content()
    await page.wait(1)

    sign_up_btn = await page.find("Sign up for 3 free deliveries", best_match=True)
    await sign_up_btn.click()

    email_field = await page.find("input[type='email']", best_match=True)
    email_address = f"{names.get_first_name()}{names.get_last_name()}@{os.getenv("CATCHALL")}".lower()
    await email_field.send_keys(email_address)

    continue_btn = await page.find("continue", best_match=True)
    await continue_btn.click()

    try:
        code = await wait_for_code(email_address)
    except TimeoutError as error:
        print(f"TimeoutError: {error}")
        return

    print(f"Code: {code}")

    code_input = await page.find("//input[@name='code']", best_match=True)
    await code_input.send_keys(code)

    address_input = await page.find("//input[@id='streetAddress']", best_match=True)
    await address_input.send_keys(os.getenv("ADDRESS"))

    await page.get_content()
    await page.wait(2)

    address_btn = await page.find("#address-suggestion-list_0 > button", best_match=True)
    await address_btn.click()
    await page.wait(1)

    confirm_btn = await page.find("//button[@type='submit']", best_match=True)
    await confirm_btn.click()
    await page.wait(2)

    with open("output_emails.txt", "a") as file:
        file.write(email_address + "\n")
    
    await page.reload()
    await page.wait(10)


async def main():
    while True:
        try:
            await run()
        except Exception as error:
            print(f"Main Exception: {error}")


if __name__ == '__main__':
    asyncio.run(main())
