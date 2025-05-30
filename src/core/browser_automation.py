"""
Browser Automation module for the Automated Login Application.
Handles browser control and login automation using Playwright.
"""

import asyncio
import re
import time
import uuid
from typing import Dict, Optional, Any, Callable, List, Tuple, Union, Type
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright
import requests
from bs4 import BeautifulSoup
import webbrowser

from ..utils.logger import Logger
from ..utils.config_manager import ConfigManager
from ..utils.exceptions import BrowserError, LoginError, NetworkError
from ..utils.error_handler import ErrorHandler
error_handler = ErrorHandler(Logger("BrowserAutomation"))

def precheck_google_oauth(url: str, logger: Optional[Logger] = None) -> bool:
    """
    Fetch the login page and scan for Google OAuth options using requests and BeautifulSoup.
    Returns True if Google OAuth is detected, else False.
    Enhanced to be robust to different page structures and element variations.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/113.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            if logger:
                logger.warning(f"[Precheck] Could not fetch login page (status {resp.status_code}) for {url}")
            return False

        # Log the first 500 characters of the fetched HTML for diagnostics
        if logger:
            logger.info(f"[Precheck][DIAG] First 500 chars of fetched HTML for {url}:\n{resp.text[:500]}")

        soup = BeautifulSoup(resp.text, "html.parser")

        # Log all <a> and <form> href/action attributes containing "google"
        google_links = []
        for a in soup.find_all("a", href=True):
            if "google" in a["href"]:
                google_links.append(a["href"])
        for form in soup.find_all("form", action=True):
            if "google" in form["action"]:
                google_links.append(form["action"])
        if logger and google_links:
            logger.info(f"[Precheck][DIAG] Found <a>/<form> href/action(s) containing 'google': {google_links}")

        # Check for hrefs containing Google OAuth (original strict check)
        for a in soup.find_all("a", href=True):
            if "accounts.google.com/o/oauth2" in a["href"]:
                if logger:
                    logger.info("[Precheck] Found Google OAuth href in login page.")
                return True

        # Check for <form> actions pointing to Google OAuth (original strict check)
        for form in soup.find_all("form", action=True):
            if "accounts.google.com/o/oauth2" in form["action"]:
                if logger:
                    logger.info("[Precheck] Found Google OAuth form action in login page.")
                return True

        # Check for buttons/links/divs/spans with Google sign-in text, aria-label, or title
        google_text_patterns = [
            "sign in with google",
            "sign in using google",
            "continue with google",
            "login with google",
            "log in with google",
            "google sign in",
            "google login",
        ]
        found_google_texts = []
        for tag in soup.find_all(["button", "a", "div", "span"]):
            text = tag.get_text(separator=" ", strip=True).lower()
            aria_label = tag.attrs.get("aria-label", "").lower()
            title = tag.attrs.get("title", "").lower()
            # Check for "google" in text, aria-label, or title
            if "google" in text or "google" in aria_label or "google" in title:
                found_google_texts.append({
                    "text": text,
                    "aria-label": aria_label,
                    "title": title
                })
            # Check for any of the patterns in text, aria-label, or title
            for pattern in google_text_patterns:
                if (
                    pattern in text
                    or pattern in aria_label
                    or pattern in title
                ):
                    if logger:
                        logger.info(f"[Precheck] Found Google OAuth pattern '{pattern}' in element: text='{text}', aria-label='{aria_label}', title='{title}'")
                    return True

        if logger and found_google_texts:
            logger.info(f"[Precheck][DIAG] Found element(s) with 'google' in text/aria-label/title: {found_google_texts}")

        # Check for common Google OAuth button class names or data attributes
        google_class_patterns = [
            "google-sign-in", "google-login", "btn-google", "google-auth", "google_oauth", "google"
        ]
        found_google_classes = []
        for tag in soup.find_all(["button", "a", "div", "span"], class_=True):
            classes = " ".join(tag.get("class", [])).lower()
            for pattern in google_class_patterns:
                if pattern in classes:
                    found_google_classes.append(classes)
                    if logger:
                        logger.info(f"[Precheck] Found Google OAuth class pattern '{pattern}' in classes: {classes}")
                    return True

        # Check for data-provider or data-auth attributes
        for tag in soup.find_all(["button", "a", "div", "span"]):
            data_provider = tag.attrs.get("data-provider", "").lower()
            data_auth = tag.attrs.get("data-auth", "").lower()
            if "google" in data_provider or "google" in data_auth:
                if logger:
                    logger.info(f"[Precheck] Found Google OAuth data attribute in element: data-provider='{data_provider}', data-auth='{data_auth}'")
                return True

        if logger and found_google_classes:
            logger.info(f"[Precheck][DIAG] Found element(s) with Google OAuth class: {found_google_classes}")

        if logger:
            logger.info("[Precheck][DIAG] No Google OAuth indicators detected in precheck.")

        return False
    except Exception as e:
        if logger:
            logger.error(f"[Precheck] Error during Google OAuth pre-check: {e}")
        return False

# Abstract base class for login strategies
class LoginStrategy:
    """Base class for different login strategies."""
    
    def __init__(self, browser_automation: 'BrowserAutomation'):
        """
        Initialize login strategy with browser automation instance.
        
        Args:
            browser_automation: Browser automation instance
        """
        self.browser = browser_automation
        self.logger = browser_automation.logger
        self.page = None  # Will be set when needed
    
    async def login(self, url: str, username: str, password: str, 
                   callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Implement login strategy.
        
        Args:
            url: Website URL
            username: Login username
            password: Login password
            callback: Callback function for status updates
            
        Returns:
            Status dictionary with login result
        """
        # Get the page from browser automation when needed
        self.page = await self.browser.get_page()
        if not self.page:
            raise BrowserError("Browser page not available")
            
        raise NotImplementedError("Subclasses must implement login method")

# Standard form login strategy
class FormLoginStrategy(LoginStrategy):
    """Strategy for standard form-based login."""
    
    async def login(self, url: str, username: str, password: str,
                   callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Login using standard form.

        Args:
            url: Website URL
            username: Login username
            password: Login password
            callback: Callback function for status updates

        Returns:
            Status dictionary with login result
        """
        # Get the page from browser automation when needed
        self.page = await self.browser.get_page()
        if not self.page:
            raise BrowserError("Browser page not available")

        status = {
            "url": url,
            "stage": "navigating",
            "success": None,
            "message": f"Navigating to {url}..."
        }

        if callback:
            callback(status)

        # Navigate to URL
        try:
            self.logger.info(f"Navigating to {url}")
            await self.page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error navigating to {url}: {e}"
            })
            return status

        # Wait for page to load
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for page to load: {e}")
            # Continue anyway, page might still be usable

        # Update status
        status.update({
            "stage": "detecting_form",
            "message": "Detecting login form..."
        })

        if callback:
            callback(status)

        # Use the browser's _detect_login_form method (mocked in tests)
        try:
            form_info = await self.browser._detect_login_form()
            username_field = form_info.get("username_field")
            password_field = form_info.get("password_field")
            ambiguous = form_info.get("ambiguous", False)
            # If ambiguous, signal for manual override (UI should prompt user)
            if ambiguous:
                self.logger.warning("Ambiguous login form detection: manual field selection required")
                status.update({
                    "stage": "ambiguous_form",
                    "success": False,
                    "message": (
                        "Ambiguous login form detected. "
                        "Automatic detection could not confidently identify the username and password fields. "
                        "Please select the correct fields manually."
                    ),
                    "form_candidates": form_info.get("all_candidates", [])
                })
                return status
            if not username_field or not password_field:
                self.logger.error("Could not find username or password field")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": "Could not find username or password field"
                })
                return status
        except Exception as e:
            self.logger.error(f"Error detecting login form: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error detecting login form: {e}"
            })
            return status

        # Update status
        status.update({
            "stage": "filling_form",
            "message": "Filling login form..."
        })

        if callback:
            callback(status)

        # Fill the login form using the browser's method (mocked in tests)
        try:
            await self.browser._fill_login_form(form_info, username, password)
        except Exception as e:
            self.logger.error(f"Error filling login form: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error filling login form: {e}"
            })
            return status

        # Update status
        status.update({
            "stage": "submitting",
            "message": "Submitting login form..."
        })

        if callback:
            callback(status)

        # Submit the login form using the browser's method (mocked in tests)
        try:
            await self.browser._submit_login_form(form_info)
        except Exception as e:
            self.logger.error(f"Error submitting login form: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error submitting login form: {e}"
            })
            return status

        # Detect CAPTCHA
        try:
            captcha_present = await self.browser._detect_captcha()
            if captcha_present:
                status.update({
                    "stage": "captcha_detected",
                    "success": False,
                    "message": "CAPTCHA detected. Manual intervention required."
                })
                if callback:
                    callback(status)
                return status
        except Exception as e:
            self.logger.error(f"Error detecting CAPTCHA: {e}")

        # Detect two-factor authentication
        try:
            two_factor_present = await self.browser._detect_two_factor()
            if two_factor_present:
                status.update({
                    "stage": "two_factor_detected",
                    "success": False,
                    "message": "Two-factor authentication detected. Manual intervention required."
                })
                if callback:
                    callback(status)
                return status
        except Exception as e:
            self.logger.error(f"Error detecting two-factor authentication: {e}")

        # Update status
        status.update({
            "stage": "waiting_for_navigation",
            "message": "Waiting for page to load after login..."
        })

        if callback:
            callback(status)

        # Wait for navigation
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for navigation: {e}")
            # Continue anyway, login might still be successful

        # Check if login was successful
        login_success = await self._check_login_success(username)

        # Update status
        if login_success:
            status.update({
                "stage": "success",
                "success": True,
                "message": "Login successful!"
            })
        else:
            status.update({
                "stage": "error",
                "success": False,
                "message": "Login failed. Please check your credentials."
            })

        if callback:
            callback(status)

        return status
    
    async def _check_login_success(self, url: str) -> bool:
        """
        Check if login was successful.
        
        Args:
            url: Website URL
            
        Returns:
            True if login was successful, False otherwise
        """
        # Get the page from browser automation when needed
        self.page = await self.browser.get_page()
        if not self.page:
            raise BrowserError("Browser page not available")
            
        # Check if we're still on the login page
        current_url = self.page.url
        
        # If we're redirected to a different domain, login was probably successful
        parsed_original = urlparse(url)
        parsed_current = urlparse(current_url)
        
        if parsed_original.netloc != parsed_current.netloc:
            self.logger.info(f"Redirected to different domain: {parsed_current.netloc}")
            return True
        
        # Check if URL contains common login failure indicators
        if any(indicator in current_url.lower() for indicator in ["login", "signin", "sign-in", "log-in"]):
            self.logger.info(f"Still on login page: {current_url}")
            return False
        
        # Check for common error messages on the page
        try:
            page_content = await self.page.content()
            error_patterns = [
                "incorrect password",
                "invalid username",
                "invalid email",
                "invalid credentials",
                "login failed",
                "authentication failed"
            ]
            
            for pattern in error_patterns:
                if pattern in page_content.lower():
                    self.logger.info(f"Found error message on page: {pattern}")
                    return False
        except Exception as e:
            self.logger.error(f"Error checking page content: {e}")
        
        # If we got this far, login was probably successful
        return True

# Google OAuth login strategy
class GoogleOAuthStrategy(LoginStrategy):
    """Strategy for Google OAuth login."""
    
    async def login(self, url: str, username: str, password: str, 
                   callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Login using Google OAuth.
        
        Args:
            url: Website URL
            username: Google email
            password: Google password
            callback: Callback function for status updates
            
        Returns:
            Status dictionary with login result
        """
        # Get the page from browser automation when needed
        self.page = await self.browser.get_page()
        if not self.page:
            raise BrowserError("Browser page not available")
            
        status = {
            "url": url,
            "stage": "navigating",
            "success": None,
            "message": f"Navigating to {url}..."
        }
        
        if callback:
            callback(status)
        
        # Navigate to URL
        try:
            self.logger.info(f"Navigating to {url}")
            await self.page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error navigating to {url}: {e}"
            })
            return status
        
        # Wait for page to load
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for page to load: {e}")
            # Continue anyway, page might still be usable
        
        # Update status
        status.update({
            "stage": "detecting_google_oauth",
            "message": "Looking for Google sign-in button..."
        })
        
        if callback:
            callback(status)
        
        # Try to find Google sign-in button with robust, multi-strategy selectors and fallbacks
        google_button = None
        detection_attempts = 0
        max_detection_attempts = 2  # First: normal, Second: slow mode + spoofed UA

        # Define selector strategies (CSS, ARIA, XPath, data attributes, role)
        google_selectors = [
            # CSS/Text
            "button:has-text('Sign in with Google')",
            "button:has-text('Continue with Google')",
            "button:has-text('Login with Google')",
            "button:has-text('Log in with Google')",
            "a:has-text('Sign in with Google')",
            "a:has-text('Continue with Google')",
            "a:has-text('Login with Google')",
            "a:has-text('Log in with Google')",
            "div:has-text('Sign in with Google')",
            "div:has-text('Continue with Google')",
            "div:has-text('Login with Google')",
            "div:has-text('Log in with Google')",
            # ARIA
            "[aria-label*='Google']",
            "[aria-label*='google']",
            # Data attributes
            "[data-provider*='google']",
            "[data-auth*='google']",
            # Role
            "[role='button'][aria-label*='Google']",
            # Class
            ".google-sign-in, .google-login, .btn-google, .google-auth, .google_oauth, .google",
            # XPath (Playwright supports $x via evaluate)
        ]
        # XPath selectors (to be used via evaluate)
        google_xpaths = [
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'google')]",
            "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'google')]",
            "//div[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'google')]",
            "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'google')]"
        ]

        while not google_button and detection_attempts < max_detection_attempts:
            try:
                # 1. Try all CSS/ARIA/data/role/class selectors
                for selector in google_selectors:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        for element in elements:
                            is_visible = await element.is_visible()
                            if is_visible:
                                google_button = element
                                break
                    if google_button:
                        break

                # 2. Try XPath selectors
                if not google_button:
                    for xpath in google_xpaths:
                        elements = await self.page.evaluate(
                            """(xpath) => {
                                const results = [];
                                const nodes = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                for (let i = 0; i < nodes.snapshotLength; i++) {
                                    results.push(nodes.snapshotItem(i));
                                }
                                return results;
                            }""", xpath
                        )
                        # Wrap DOM nodes as Playwright element handles
                        if elements:
                            for node in elements:
                                handle = await self.page.evaluate_handle("(el) => el", node)
                                is_visible = await handle.is_visible()
                                if is_visible:
                                    google_button = handle
                                    break
                        if google_button:
                            break

                # 3. If not found, try broader search: any element with "google" in text, aria-label, or title
                if not google_button:
                    candidates = await self.page.query_selector_all("button, a, div, span")
                    for element in candidates:
                        try:
                            text = (await element.inner_text()).lower()
                        except Exception:
                            text = ""
                        try:
                            aria_label = (await element.get_attribute("aria-label") or "").lower()
                        except Exception:
                            aria_label = ""
                        try:
                            title = (await element.get_attribute("title") or "").lower()
                        except Exception:
                            title = ""
                        if (
                            "google" in text
                            or "google" in aria_label
                            or "google" in title
                        ):
                            is_visible = await element.is_visible()
                            if is_visible:
                                google_button = element
                                break

                # 4. If still not found, search inside iframes
                if not google_button:
                    frames = self.page.frames
                    for frame in frames:
                        if frame == self.page.main_frame:
                            continue
                        try:
                            elements = await frame.query_selector_all("button, a, div, span")
                            for element in elements:
                                try:
                                    text = (await element.inner_text()).lower()
                                except Exception:
                                    text = ""
                                try:
                                    aria_label = (await element.get_attribute("aria-label") or "").lower()
                                except Exception:
                                    aria_label = ""
                                try:
                                    title = (await element.get_attribute("title") or "").lower()
                                except Exception:
                                    title = ""
                                if (
                                    "google" in text
                                    or "google" in aria_label
                                    or "google" in title
                                ):
                                    is_visible = await element.is_visible()
                                    if is_visible:
                                        google_button = element
                                        break
                            if google_button:
                                break
                        except Exception:
                            continue

                # If found, break out of retry loop
                if google_button:
                    break

                # If not found, try fallback: slow mode and spoofed user-agent
                if not google_button and detection_attempts == 0:
                    self.logger.warning("Google sign-in button not found, retrying with slow mode and spoofed user-agent.")
                    # Slow down automation
                    await self.page.wait_for_timeout(2000)
                    # Spoof user-agent and reload
                    await self.page.context.set_extra_http_headers({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
                    })
                    await self.page.reload(wait_until="domcontentloaded")
            except Exception as e:
                self.logger.error(f"Error finding Google sign-in button: {e}")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": f"Error finding Google sign-in button: {e}"
                })
                return status
            detection_attempts += 1

        if not google_button:
            # As a last resort, suggest running in non-headless mode
            self.logger.error("Could not find Google sign-in button after all strategies. Try running in non-headless mode.")
            status.update({
                "stage": "error",
                "success": False,
                "message": "Could not find Google sign-in button. This may be due to overlays, anti-bot measures, or dynamic rendering. Try running in non-headless mode or check your network."
            })
            return status
        
        # Update status
        status.update({
            "stage": "clicking_google_oauth",
            "message": "Clicking Google sign-in button..."
        })
        
        if callback:
            callback(status)
        
        # Robustly handle overlays and click Google sign-in button
        try:
            # Scroll button into view before clicking
            try:
                await google_button.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass

            # Wait for overlays to disappear or forcibly hide them if needed
            overlay_removed = await self._handle_click_intercepting_overlays()
            if not overlay_removed:
                self.logger.warning("Overlay may still be present, attempting click anyway.")

            click_attempts = 0
            max_click_attempts = 2
            while click_attempts < max_click_attempts:
                try:
                    await google_button.click(timeout=10000)
                    self.logger.info("Clicked Google sign-in button")
                    break
                except Exception as click_exc:
                    self.logger.warning(f"Standard click failed due to: {click_exc}. Retrying with JS click and scroll.")
                    try:
                        # Try JS click as a fallback
                        await self.page.evaluate(
                            "(el) => { el.scrollIntoView({behavior: 'smooth', block: 'center'}); el.click(); }", google_button
                        )
                        self.logger.info("Clicked Google sign-in button via JS.")
                        break
                    except Exception as js_exc:
                        if click_attempts == max_click_attempts - 1:
                            self.logger.error(f"Error clicking Google sign-in button (JS fallback): {js_exc}")
                            status.update({
                                "stage": "error",
                                "success": False,
                                "message": f"Error clicking Google sign-in button: {js_exc}"
                            })
                            return status
                        else:
                            # Wait and retry
                            await self.page.wait_for_timeout(1000)
                click_attempts += 1
        except Exception as e:
            self.logger.error(f"Error clicking Google sign-in button: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error clicking Google sign-in button: {e}"
            })
            return status
        
        # Wait for Google sign-in page or popup
        try:
            # Wait for either navigation or popup (new page)
            popup_page = None
            context = self.page.context
            popup_task = asyncio.create_task(context.wait_for_event("page", timeout=7000))
            nav_task = asyncio.create_task(self.page.wait_for_load_state("networkidle", timeout=10000))
            done, pending = await asyncio.wait([popup_task, nav_task], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            if popup_task in done and not popup_task.cancelled():
                try:
                    popup_page = popup_task.result()
                except Exception:
                    popup_page = None
            if popup_page:
                self.logger.info("Detected Google sign-in popup window, switching context.")
                self.page = popup_page
                await self.page.bring_to_front()
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            else:
                await self.page.bring_to_front()
        except Exception as e:
            self.logger.warning(f"Timeout waiting for Google sign-in page or popup: {e}")
            # Continue anyway, page might still be usable

        # Check if we're on Google sign-in page
        current_url = self.page.url
        if "accounts.google.com" not in current_url:
            self.logger.error(f"Not on Google sign-in page: {current_url}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Not on Google sign-in page: {current_url}"
            })
            return status
        
        # Update status
        status.update({
            "stage": "filling_google_form",
            "message": "Filling Google sign-in form..."
        })
        
        if callback:
            callback(status)
        
        # Fill Google email
        try:
            # Look for email field
            email_field = await self.page.query_selector("input[type='email']")
            if not email_field:
                self.logger.error("Could not find Google email field")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": "Could not find Google email field"
                })
                return status
            
            # Fill email field
            await email_field.fill(username)
            
            # Click Next button
            next_button = await self.page.query_selector("button:has-text('Next')")
            if not next_button:
                self.logger.error("Could not find Next button")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": "Could not find Next button"
                })
                return status
            
            await next_button.click()
            
            # Wait for password field
            await self.page.wait_for_selector("input[type='password']", timeout=10000)
        except Exception as e:
            self.logger.error(f"Error filling Google email: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error filling Google email: {e}"
            })
            return status
        
        # Fill Google password
        try:
            # Look for password field
            password_field = await self.page.query_selector("input[type='password']")
            if not password_field:
                self.logger.error("Could not find Google password field")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": "Could not find Google password field"
                })
                return status
            
            # Fill password field
            await password_field.fill(password)
            
            # Click Next button
            next_button = await self.page.query_selector("button:has-text('Next')")
            if not next_button:
                self.logger.error("Could not find Next button")
                status.update({
                    "stage": "error",
                    "success": False,
                    "message": "Could not find Next button"
                })
                return status
            
            await next_button.click()
        except Exception as e:
            self.logger.error(f"Error filling Google password: {e}")
            status.update({
                "stage": "error",
                "success": False,
                "message": f"Error filling Google password: {e}"
            })
            return status
        
        # Update status
        status.update({
            "stage": "waiting_for_google_auth",
            "message": "Waiting for Google authentication..."
        })
        
        if callback:
            callback(status)
        
        # Wait for navigation
        try:
            await self.page.wait_for_load_state("networkidle", timeout=20000)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for Google authentication: {e}")
            # Continue anyway, login might still be successful
        
        # Check if we're still on Google sign-in page
        current_url = self.page.url
        if "accounts.google.com" in current_url:
            # Check for error messages
            try:
                error_message = await self.page.query_selector("div[aria-live='assertive']")
                if error_message:
                    error_text = await error_message.text_content()
                    self.logger.error(f"Google sign-in error: {error_text}")
                    status.update({
                        "stage": "error",
                        "success": False,
                        "message": f"Google sign-in error: {error_text}"
                    })
                    return status
            except Exception as e:
                self.logger.error(f"Error checking for Google sign-in error: {e}")
            
            # Check for 2FA
            try:
                if "challenge/pwd" in current_url or "challenge/ipp" in current_url:
                    self.logger.info("Google 2FA required")
                    status.update({
                        "stage": "waiting_for_2fa",
                        "success": None,
                        "message": "Google 2FA required. Please complete 2FA in the browser."
                    })
                    
                    if callback:
                        callback(status)
                    
                    # Wait for user to complete 2FA
                    await self.browser.wait_for_user_action(300)
                    
                    # Check if we're still on Google sign-in page
                    current_url = self.page.url
                    if "accounts.google.com" in current_url:
                        self.logger.error("Still on Google sign-in page after 2FA")
                        status.update({
                            "stage": "error",
                            "success": False,
                            "message": "Still on Google sign-in page after 2FA"
                        })
                        return status
            except Exception as e:
                self.logger.error(f"Error handling Google 2FA: {e}")
        
        # Wait for final navigation
        try:
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception as e:
            self.logger.warning(f"Timeout waiting for final navigation: {e}")
            # Continue anyway, login might still be successful
        
        # Check if login was successful
        login_success = await self._check_login_success(url)
        
        # Update status
        if login_success:
            status.update({
                "stage": "success",
                "success": True,
                "message": "Login successful!"
            })
        else:
            status.update({
                "stage": "error",
                "success": False,
                "message": "Login failed. Please check your credentials."
            })
        
        if callback:
            callback(status)
        
        return status
    
    async def _handle_click_intercepting_overlays(self, timeout: float = 5.0) -> bool:
        """
        Detect and handle overlays that intercept pointer events before clicking.
        Returns True if overlays are gone or hidden, False if overlays may still be present.
        """
        import time

        overlay_selectors = [
            # Generic Google sign-in overlays and common patterns
            "div[id^='gsi_'][id$='-overlay']",
            "div[class*='overlay']",
            "div[style*='pointer-events: auto']",
            "div[style*='pointer-events:all']",
            "div[style*='z-index']"
        ]
        start = time.time()
        while time.time() - start < timeout:
            overlays = []
            for selector in overlay_selectors:
                found = await self.page.query_selector_all(selector)
                overlays.extend(found)
            # Filter overlays that are visible and intercept pointer events
            intercepting = []
            for overlay in overlays:
                try:
                    visible = await overlay.is_visible()
                    pointer_events = await self.page.evaluate(
                        "(el) => getComputedStyle(el).pointerEvents", overlay
                    )
                    if visible and pointer_events in ("auto", "all"):
                        intercepting.append(overlay)
                except Exception:
                    continue
            if not intercepting:
                return True  # No overlays intercepting
            # Try to hide overlays forcibly
            for overlay in intercepting:
                try:
                    await self.page.evaluate(
                        "(el) => { el.style.display = 'none'; el.style.pointerEvents = 'none'; }", overlay
                    )
                except Exception:
                    continue
            await asyncio.sleep(0.2)
        # After timeout, overlays may still be present
        return False

    async def _check_login_success(self, url: str) -> bool:
        """
        Check if login was successful.
        
        Args:
            url: Website URL
            
        Returns:
            True if login was successful, False otherwise
        """
        # Get the page from browser automation when needed
        self.page = await self.browser.get_page()
        if not self.page:
            raise BrowserError("Browser page not available")
            
        # Check if we're still on Google sign-in page
        current_url = self.page.url
        if "accounts.google.com" in current_url:
            self.logger.info(f"Still on Google sign-in page: {current_url}")
            return False
        
        # If we're back on the original domain, login was probably successful
        parsed_original = urlparse(url)
        parsed_current = urlparse(current_url)
        
        if parsed_original.netloc == parsed_current.netloc:
            self.logger.info(f"Back on original domain: {parsed_current.netloc}")
            return True
        
        # If we're on a different domain, check if it's a common redirect domain
        common_redirect_domains = [
            "accounts.google.com",
            "myaccount.google.com",
            "mail.google.com",
            "drive.google.com",
            "docs.google.com",
            "sheets.google.com",
            "slides.google.com",
            "calendar.google.com"
        ]
        
        if parsed_current.netloc in common_redirect_domains:
            self.logger.info(f"Redirected to Google service: {parsed_current.netloc}")
            return True
        
        # If we got this far, login was probably successful
        return True

# System browser login strategy
class SystemBrowserLoginStrategy(LoginStrategy):
    """Strategy for manual login via the system browser."""

    async def login(self, url: str, username: str, password: str, 
                   callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Open the login URL in the system browser and instruct the user to log in manually.

        Args:
            url: Website URL
            username: Login username (unused)
            password: Login password (unused)
            callback: Callback function for status updates

        Returns:
            Status dictionary indicating manual login is required
        """
        self.logger.info(f"Opening system browser for manual login: {url}")
        webbrowser.open(url)
        status = {
            "url": url,
            "stage": "manual_login",
            "success": None,
            "requires_user_action": True,
            "message": "Please complete the login manually in your system browser."
        }
        if callback:
            callback(status)
        return status
class BrowserAutomation:
    """
    Manages browser automation for website logins using Playwright.
    Handles browser launch, navigation, form filling, and login detection.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize browser automation with configuration.
        
        Args:
            config_manager: Application configuration manager
        """
        self.logger = Logger("BrowserAutomation")
        self.config_manager = config_manager
        self.browser_type = self.config_manager.get("browser", "chromium")
        self.headless = self.config_manager.get("headless", False)
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright: Optional[Playwright] = None
        self._playwright_instance = None
        self.status: Dict[str, Any] = {}
        self.error_handler = ErrorHandler(self.logger)
        self._initialized = False

        # For test/mocking compatibility
        self.browser = None
        self.page = None
        self._check_login_success = None
    
    @property
    def browser(self):
        """Return the injected browser if set, otherwise the internal _browser."""
        return self._browser if self.__dict__["browser"] is None else self.__dict__["browser"]

    @browser.setter
    def browser(self, value):
        self.__dict__["browser"] = value

    @property
    def page(self):
        """Return the injected page if set, otherwise the internal _page."""
        return self._page if self.__dict__["page"] is None else self.__dict__["page"]

    @page.setter
    def page(self, value):
        self.__dict__["page"] = value

    @property
    def context(self):
        """Return the injected context if set, otherwise the internal _context."""
        return self._context if self.__dict__.get("context", None) is None else self.__dict__["context"]

    @context.setter
    def context(self, value):
        self.__dict__["context"] = value

    async def get_browser(self) -> Optional[Browser]:
        """
        Get or initialize browser.
    
        Returns:
            Browser instance
    
        Raises:
            BrowserError: If browser initialization fails
        """
        if not self._browser:
            await self.initialize()
        return self._browser

    async def get_context(self) -> Optional[BrowserContext]:
        """
        Get or initialize browser context.

        Returns:
            Browser context instance

        Raises:
            BrowserError: If browser initialization fails
        """
        if not self._context:
            await self.initialize()
        return self._context

    async def get_page(self) -> Optional[Page]:
        """
        Get or initialize browser page.

        Returns:
            Browser page instance

        Raises:
            BrowserError: If browser initialization fails
        """
        if not self._page:
            await self.initialize()
        return self._page

    def set_page(self, value):
        """
        Set the browser page (for testing/mocking purposes).
        """
        self._page = value

    async def _detect_login_form(self) -> dict:
        """
        Detect the login form on the current page using contextual and rule-based analysis.

        Returns:
            dict: {
                "username_field": Playwright element handle or None,
                "password_field": Playwright element handle or None,
                "form": Playwright element handle or None,
                "score": float,  # confidence score for detection
                "all_candidates": list of dicts with candidate fields and scores
            }

        Precision vs. Recall:
            - This method uses a layered approach: strict (high-precision) checks first, then heuristic (high-recall) checks.
            - If ambiguity remains, the UI should prompt the user for manual selection.
        """
        page = await self.get_page()
        forms = await page.query_selector_all("form")
        candidates = []

        async def get_label_text(field):
            # Try to find a label associated with the field
            try:
                id_attr = await field.get_attribute("id")
                if id_attr:
                    label = await page.query_selector(f"label[for='{id_attr}']")
                    if label:
                        return (await label.inner_text()).strip().lower()
                # Try parent label
                parent = await field.evaluate_handle("el => el.parentElement")
                if parent:
                    tag = await parent.evaluate("el => el.tagName")
                    if tag and tag.lower() == "label":
                        return (await parent.inner_text()).strip().lower()
            except Exception:
                pass
            return ""

        async def score_field(field, field_type):
            # Score based on label, placeholder, name, and type
            score = 0
            try:
                label = (await get_label_text(field)) or ""
                placeholder = (await field.get_attribute("placeholder") or "").lower()
                name = (await field.get_attribute("name") or "").lower()
                input_type = (await field.get_attribute("type") or "").lower()
                # Username/email field
                if field_type == "username":
                    if "user" in label or "user" in placeholder or "user" in name:
                        score += 2
                    if "email" in label or "email" in placeholder or "email" in name:
                        score += 2
                    if input_type == "email":
                        score += 1.5
                # Password field
                if field_type == "password":
                    if "pass" in label or "pass" in placeholder or "pass" in name:
                        score += 2
                    if input_type == "password":
                        score += 2
                # General
                if "login" in label or "login" in placeholder or "login" in name:
                    score += 0.5
            except Exception:
                pass
            return score

        # Consider all forms, not just the first
        for form in forms:
            try:
                # Find all input fields in the form
                inputs = await form.query_selector_all("input")
                username_candidates = []
                password_candidates = []
                for field in inputs:
                    input_type = (await field.get_attribute("type") or "").lower()
                    if input_type in ["text", "email"]:
                        username_candidates.append(field)
                    if input_type == "password":
                        password_candidates.append(field)
                # Score all username/password candidates
                for u in username_candidates:
                    u_score = await score_field(u, "username")
                    for p in password_candidates:
                        p_score = await score_field(p, "password")
                        # Proximity: fields close together get a bonus
                        u_index = inputs.index(u)
                        p_index = inputs.index(p)
                        proximity = 1.0 if abs(u_index - p_index) <= 2 else 0.0
                        total_score = u_score + p_score + proximity
                        # Check for submit button nearby
                        submit_btn = await form.query_selector("button[type='submit'], input[type='submit']")
                        if submit_btn:
                            total_score += 0.5
                        candidates.append({
                            "form": form,
                            "username_field": u,
                            "password_field": p,
                            "score": total_score
                        })
            except Exception:
                continue

        # If no forms, fallback to page-level search (high recall, low precision)
        if not candidates:
            username_fields = await page.query_selector_all("input[type='text'], input[type='email']")
            password_fields = await page.query_selector_all("input[type='password']")
            for u in username_fields:
                u_score = await score_field(u, "username")
                for p in password_fields:
                    p_score = await score_field(p, "password")
                    proximity = 1.0  # Assume close if no form
                    total_score = u_score + p_score + proximity
                    candidates.append({
                        "form": None,
                        "username_field": u,
                        "password_field": p,
                        "score": total_score
                    })

        # Rank candidates by score
        candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)
        best = candidates[0] if candidates else {"username_field": None, "password_field": None, "form": None, "score": 0}

        # If ambiguous (low score or multiple similar scores), signal for manual override
        ambiguous = False
        if not best["username_field"] or not best["password_field"]:
            ambiguous = True
        elif len(candidates) > 1 and abs(candidates[0]["score"] - candidates[1]["score"]) < 1.0:
            ambiguous = True
        elif best["score"] < 2.5:
            ambiguous = True

        result = {
            "username_field": best["username_field"],
            "password_field": best["password_field"],
            "form": best.get("form"),
            "score": best.get("score", 0),
            "all_candidates": candidates,
            "ambiguous": ambiguous
        }
        return result

    async def _detect_captcha(self) -> bool:
        """
        Detect if a CAPTCHA is present on the current page.
        Returns False by default; override or mock in tests as needed.
        """
        return False

    async def _detect_two_factor(self) -> bool:
        """
        Detect if a two-factor authentication prompt is present on the current page.
        Returns False by default; override or mock in tests as needed.
        """
        return False

    async def _fill_login_form(self, form_info, username, password):
        """
        Fill the login form fields with the provided username and password.

        Args:
            form_info: Dictionary containing "username_field" and "password_field" (element handles)
            username: Username to fill
            password: Password to fill

        This method is compatible with both real Playwright element handles and test mocks.
        """
        try:
            await form_info["username_field"].fill(username)
            await form_info["password_field"].fill(password)
            self.logger.info("Filled login form fields.")
        except Exception as e:
            self.logger.error(f"Error filling login form: {e}")
            raise
    async def _submit_login_form(self, form_info):
        """
        Submit the login form after filling credentials.
        Tries pressing Enter in the password field, then clicking a submit button if needed.

        Args:
            form_info: Dictionary containing "username_field" and "password_field" (element handles)

        Raises:
            Exception if unable to submit the form.
        """
        page = await self.get_page()
        password_field = form_info.get("password_field")
        if password_field is None:
            self.logger.error("No password field found for form submission.")
            raise Exception("No password field found for form submission.")

        # Try pressing Enter in the password field
        try:
            await password_field.press("Enter")
            self.logger.info("Submitted login form by pressing Enter in password field.")
            return
        except Exception as e:
            self.logger.warning(f"Failed to submit form by pressing Enter: {e}")

        # Try clicking a submit button
        try:
            # Try to find a submit button within the same form as the password field
            # If not possible, fallback to any visible submit button
            submit_button = await page.query_selector("button[type='submit'], input[type='submit']")
            if submit_button:
                await submit_button.click()
                self.logger.info("Submitted login form by clicking submit button.")
                return
            else:
                self.logger.error("No submit button found for form submission.")
                raise Exception("No submit button found for form submission.")
        except Exception as e:
            self.logger.error(f"Failed to submit form by clicking submit button: {e}")
            raise Exception("Unable to submit login form.") from e

    
    @ErrorHandler.handle_async
    async def initialize(self, headless_override: Optional[bool] = None) -> bool:
        """
        Initialize Playwright and browser.

        Args:
            headless_override: If set, overrides self.headless for this launch.

        Returns:
            True if successful, False otherwise
            
        Raises:
            BrowserError: If browser initialization fails
        """
        if self._initialized and self._browser:
            self.logger.info("Browser already initialized")
            return True
            
        try:
            # Start Playwright
            self._playwright_instance = async_playwright()
            self._playwright = await self._playwright_instance.__aenter__()

            # Select browser based on configuration
            if self.browser_type == "chromium":
                browser_class = self._playwright.chromium
            elif self.browser_type == "firefox":
                browser_class = self._playwright.firefox
            elif self.browser_type == "webkit":
                browser_class = self._playwright.webkit
            else:
                raise BrowserError(f"Unsupported browser type: {self.browser_type}")

            # Determine headless mode
            launch_headless = self.headless if headless_override is None else headless_override

            # Launch browser
            self._browser = await browser_class.launch(headless=launch_headless)
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()

            self.logger.info(f"Initialized {self.browser_type} browser (headless={launch_headless})")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Error initializing browser: {e}")
            raise BrowserError(f"Failed to initialize browser: {str(e)}") from e
    
    @ErrorHandler.handle_async
    async def login_to_website(self, url: str, username: str, password: str, 
                              callback: Optional[Callable[[Dict[str, Any]], None]] = None, 
                              google_login_method: Optional[str] = None, 
                              force_prompt: bool = False) -> Dict[str, Any]:
        """
        Login to a website.
        
        Args:
            url: Website URL
            username: Login username
            password: Login password
            callback: Callback function for status updates
            google_login_method: "playwright" or "system_browser" for Google login, or None
            force_prompt: Force prompt for login method selection
            
        Returns:
            Status dictionary with login result
            
        Raises:
            LoginError: If login fails
            BrowserError: If browser initialization fails
            NetworkError: If network error occurs
        """
        # Initialize browser if needed
        if not self._initialized:
            await self.initialize()
        
        # Determine login strategy
        strategy: LoginStrategy = None
        
        # Check if Google OAuth is available
        has_google_oauth = False
        if not force_prompt and not google_login_method:
            try:
                has_google_oauth = precheck_google_oauth(url, self.logger)
            except Exception as e:
                self.logger.error(f"Error in Google OAuth precheck: {e}")
                has_google_oauth = False
        
        # Use Google OAuth if available and not forced to use standard login
        if has_google_oauth or google_login_method == "playwright":
            self.logger.info("Using Google OAuth login strategy")
            strategy = GoogleOAuthStrategy(self)
        else:
            self.logger.info("Using standard form login strategy")
            strategy = FormLoginStrategy(self)
        
        # Login using selected strategy
        try:
            result = await strategy.login(url, username, password, callback)
        except Exception as e:
            self.logger.error(f"Error in login strategy: {e}")
            raise LoginError(f"Login failed: {str(e)}") from e
        
        # Handle post-login delay if login was successful
        post_login_delay = float(self.config_manager.get("post_login_delay", 5))
        if result.get("success"):
            if callback:
                callback({
                    "stage": "post_login_delay",
                    "success": True,
                    "message": f"Login successful. Waiting {post_login_delay} seconds before closing browser...",
                    "post_login_delay": post_login_delay,
                    "url": url  # Add URL to the status for UI display
                })
            try:
                self.logger.info(f"[DEBUG] Sleeping for post_login_delay: {post_login_delay} seconds")
                # Use a longer sleep time to ensure the browser stays open
                await asyncio.sleep(post_login_delay)
                self.logger.info(f"[DEBUG] Finished sleeping for post_login_delay: {post_login_delay} seconds")
                # Close the browser after the post-login delay
                await self.close()
            except Exception as e:
                self.logger.error(f"[DEBUG] Exception in post_login_delay sleep: {e}, defaulting to 5 seconds")
                await asyncio.sleep(5)
        
        return result
    
    @ErrorHandler.handle_async
    async def wait_for_user_action(self, timeout: int = 300) -> bool:
        """
        Wait for user to complete manual steps (like CAPTCHA or 2FA).
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            True if user completed action, False if timed out
            
        Raises:
            BrowserError: If browser is not initialized
        """
        if not self._initialized or not self._page:
            raise BrowserError("Browser not initialized")
        
        try:
            # Wait for navigation or timeout
            start_time = time.time()
            current_url = self._page.url
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(1)
                
                # Check if URL changed
                new_url = self._page.url
                if new_url != current_url:
                    self.logger.info(f"URL changed from {current_url} to {new_url}")
                    return True
                
                # Check if page content changed significantly
                # This is a simple heuristic and might need improvement
                try:
                    title = await self._page.title()
                    if "success" in title.lower() or "welcome" in title.lower():
                        self.logger.info(f"Page title indicates success: {title}")
                        return True
                except Exception:
                    pass
            
            self.logger.warning(f"Timeout waiting for user action after {timeout} seconds")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for user action: {e}")
            raise BrowserError(f"Error waiting for user action: {str(e)}") from e
    
    @ErrorHandler.handle_async
    async def close(self) -> None:
        """
        Close browser and release resources.

        Raises:
            BrowserError: If error occurs while closing browser
        """
        if not self._initialized:
            return

        try:
            # Always use the property (which prefers injected mocks) for closing
            page = self.page
            context = self.context
            browser = self.browser

            # Close page if it exists
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.logger.warning(f"Error closing page: {e}")
            # Close context if it exists
            if context:
                try:
                    await context.close()
                except Exception as e:
                    self.logger.warning(f"Error closing context: {e}")
            # Close browser
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")
                self._browser = None

            # Close Playwright
            if self._playwright_instance:
                await self._playwright_instance.__aexit__(None, None, None)
                self._playwright_instance = None
                self._playwright = None

            self._context = None
            self._page = None
            self._initialized = False

            # Also clear injected mocks after closing
            if "browser" in self.__dict__:
                self.__dict__["browser"] = None
            if "context" in self.__dict__:
                self.__dict__["context"] = None
            if "page" in self.__dict__:
                self.__dict__["page"] = None

            self.logger.info("Browser closed")
        except RuntimeError as e:
            if "Event loop is closed" in str(e):
                self.logger.warning(f"Suppressed RuntimeError during browser close: {e}")
            else:
                self.logger.error(f"Error closing browser: {e}")
                raise BrowserError(f"Error closing browser: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
            raise BrowserError(f"Error closing browser: {str(e)}") from e
