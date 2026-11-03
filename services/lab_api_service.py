import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


class LabApiService:
    """
    Client service for direct, secure REST API communication between
    the Hospital Management Portal and the Diagnostic Laboratory Processing Portal.
    """

    def __init__(self, app=None):
        self.app = app or current_app
        base = self.app.config.get('LAB_API_URL') or self.app.config.get('LAB_API_BASE_URL', 'http://127.0.0.1:5000')
        self.base_url = str(base).rstrip('/')
        self.api_key = self.app.config.get('LAB_API_KEY', '').strip()
        self.timeout = int(self.app.config.get('LAB_API_TIMEOUT', 15))
        if not self.api_key:
            logger.warning("LAB_API_KEY is not set. Outgoing requests to Laboratory Portal may be unauthorized.")

    def _get_headers(self):
        """Construct secure server-to-server authorization headers."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def create_test_request(self, payload):
        """
        Send a new test request JSON payload to the Laboratory Portal:
        POST /api/requests

        Returns:
            (success: bool, data: dict, error_message: str, status_code: int)
        """
        url = f"{self.base_url}/api/requests"
        headers = self._get_headers()

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            status_code = response.status_code

            try:
                resp_json = response.json()
            except ValueError:
                resp_json = {}

            if status_code == 201:
                logger.info(f"Test request {payload.get('test_id')} successfully accepted by Laboratory Portal.")
                return True, resp_json, "", status_code

            error_msg = resp_json.get("message")
            if not error_msg:
                if status_code == 400:
                    error_msg = "Validation failed in Laboratory Portal."
                elif status_code == 409:
                    error_msg = f"Test request {payload.get('test_id')} already exists in Laboratory Portal."
                elif status_code == 401:
                    error_msg = "Laboratory API authorization failed. Check LAB_API_KEY configuration."
                else:
                    error_msg = f"Laboratory API returned HTTP {status_code}."

            logger.warning(f"Laboratory API rejected request {payload.get('test_id')}: HTTP {status_code} - {error_msg}")
            return False, resp_json, error_msg, status_code

        except requests.exceptions.Timeout:
            err = f"Connection to Laboratory Portal timed out ({self.timeout}s). Request was not confirmed."
            logger.error(err)
            return False, {}, err, 0

        except requests.exceptions.ConnectionError:
            err = f"Unable to reach Laboratory Portal at {self.base_url}. Verify that the Laboratory Portal is running."
            logger.error(err)
            return False, {}, err, 0

        except requests.exceptions.RequestException as e:
            err = f"Laboratory API communication failed: {str(e)}"
            logger.error(err)
            return False, {}, err, 0

    def get_test_result(self, test_id):
        """
        Retrieve a specific test result from the Laboratory Portal:
        GET /api/results/<test_id>

        Returns:
            (success: bool, data: dict, error_message: str, is_pending: bool)
        """
        url = f"{self.base_url}/api/results/{test_id}"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            status_code = response.status_code

            try:
                resp_json = response.json()
            except ValueError:
                resp_json = {}

            if status_code == 200 and resp_json.get("success"):
                result_data = resp_json.get("data", {})
                return True, result_data, "", False

            if status_code == 404:
                status = resp_json.get("status", "")
                msg = resp_json.get("message", f"Test result for ID '{test_id}' not found.")
                # Distinguish pending/in-progress vs totally non-existent
                if status in ["Pending", "Processing", "Validated"] or "not yet completed" in msg.lower():
                    return False, {}, msg, True
                return False, {}, msg, False

            if status_code == 401:
                return False, {}, "Laboratory API authorization failed.", False

            msg = resp_json.get("message", f"Laboratory API returned HTTP {status_code}.")
            return False, {}, msg, False

        except requests.exceptions.Timeout:
            return False, {}, f"Connection to Laboratory Portal timed out while fetching result for {test_id}.", False
        except requests.exceptions.ConnectionError:
            return False, {}, f"Unable to connect to Laboratory Portal at {self.base_url}.", False
        except requests.exceptions.RequestException as e:
            return False, {}, f"Error querying Laboratory API: {str(e)}", False

    def get_all_completed_results(self):
        """
        Retrieve all completed test results from the Laboratory Portal:
        GET /api/results

        Returns:
            (success: bool, results_list: list, error_message: str)
        """
        url = f"{self.base_url}/api/results"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get("success"):
                    return True, resp_json.get("data", []), ""
                return False, [], resp_json.get("message", "Unexpected response from Laboratory API.")
            elif response.status_code == 401:
                return False, [], "Laboratory API authorization failed. Check LAB_API_KEY."
            else:
                return False, [], f"Laboratory API returned HTTP {response.status_code}."

        except requests.exceptions.Timeout:
            return False, [], f"Connection to Laboratory Portal timed out ({self.timeout}s)."
        except requests.exceptions.ConnectionError:
            return False, [], f"Unable to connect to Laboratory Portal at {self.base_url}."
        except requests.exceptions.RequestException as e:
            return False, [], f"Error contacting Laboratory API: {str(e)}"
