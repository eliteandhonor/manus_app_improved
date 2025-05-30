"""
Test configuration for the Automated Login Application.
"""

import os
import sys
import tempfile
import pytest

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

@pytest.fixture
def config_manager():
    """Create a ConfigManager instance with a temporary directory and isolated data_dir."""
    from src.utils.config_manager import ConfigManager
    import os
    with tempfile.TemporaryDirectory() as tmpdirname:
        config = ConfigManager(tmpdirname)
        # Set data_dir to a subdirectory of the temp directory for test isolation
        data_dir = os.path.join(tmpdirname, "data")
        os.makedirs(data_dir, exist_ok=True)
        config.set("data_dir", data_dir)
        yield config

@pytest.fixture
def logger():
    """Create a Logger instance with a temporary directory."""
    from src.utils.logger import Logger
    with tempfile.TemporaryDirectory() as tmpdirname:
        logger = Logger("TestLogger", log_dir=tmpdirname)
        yield logger

@pytest.fixture
def credential_manager(config_manager):
    """Create a CredentialManager instance with a test password."""
    from src.core.credential_manager import CredentialManager
    credential_manager = CredentialManager(config_manager, "TestPassword123!")
    yield credential_manager
    # Clean up sensitive data
    credential_manager.clear_memory()

@pytest.fixture
def mock_browser_page():
    """Create a mock Playwright page for testing."""
    class MockPage:
        def __init__(self):
            self.url = "https://example.com"
            self.content_html = "<html><body>Test Page</body></html>"
            self.selectors = {}
            self.clicked = []
            self.filled = {}
            self.navigated_to = None
            
        async def goto(self, url):
            self.navigated_to = url
            self.url = url
            
        async def content(self):
            return self.content_html
            
        async def wait_for_load_state(self, state):
            pass
            
        async def query_selector(self, selector):
            if selector in self.selectors:
                return self.selectors[selector]
            return None
            
        async def query_selector_all(self, selector):
            return []
            
        def set_default_timeout(self, timeout):
            self.timeout = timeout
            
        def add_selector(self, selector, element):
            self.selectors[selector] = element
            
    return MockPage()

@pytest.fixture
def mock_browser_element():
    """Create a mock Playwright element for testing."""
    class MockElement:
        def __init__(self, tag="div", text="Test Element"):
            self.tag = tag
            self.text_content = text
            self.attributes = {}
            self.is_connected = True
            self.filled_value = None
            self.clicked = False
            self.pressed_keys = []
            
        async def inner_text(self):
            return self.text_content
            
        async def get_attribute(self, name):
            return self.attributes.get(name)
            
        async def evaluate(self, js):
            if "isConnected" in js:
                return self.is_connected
            if "closest" in js:
                return None
            return None
            
        async def fill(self, value):
            self.filled_value = value
            
        async def click(self):
            self.clicked = True
            
        async def press(self, key):
            self.pressed_keys.append(key)
            
    return MockElement()

@pytest.fixture
def app_core(config_manager):
    """Create an AppCore instance for testing."""
    from src.core.app_core import AppCore
    app_core = AppCore(config_manager)
    app_core.initialize("TestPassword123!")
    yield app_core
    # Clean up
    app_core.close()
