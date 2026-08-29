import unittest
from types import SimpleNamespace
from unittest.mock import patch

import worker


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "test response"


class FakeConnection:
    def __init__(self):
        self.callbacks = []

    def add_callback_threadsafe(self, callback):
        self.callbacks.append(callback)


class FakeChannel:
    def __init__(self):
        self.acknowledged_tags = []

    def basic_ack(self, delivery_tag):
        self.acknowledged_tags.append(delivery_tag)


class WorkerReliabilityTests(unittest.TestCase):
    @patch("worker.delete_s3_object")
    @patch("worker.generate_integration_plan")
    @patch("worker.requests.put")
    def test_backend_failure_does_not_ack_or_delete_s3_file(
        self,
        mock_put,
        mock_generate_plan,
        mock_delete_s3_object,
    ):
        mock_generate_plan.return_value = {
            "note_filename": "test-note",
            "note_content": "# Test note",
            "index_entry": "| [[test-note]] | Test | General |",
            "cross_links": [],
            "index_category": "General",
        }

        mock_put.side_effect = [
            FakeResponse(200),
            FakeResponse(500),
        ]

        connection = FakeConnection()
        channel = FakeChannel()
        method = SimpleNamespace(delivery_tag=123)

        ticket = {
            "jobId": "test-job-id",
            "original_filename": "test-document.pdf",
            "userApiKey": "fake-gemini-key",
            "s3Bucket": "test-bucket",
            "s3Key": "ingest/test-document.pdf",
            "schemaText": "test schema",
            "indexText": "test index",
            "logTail": "",
        }

        worker.process_job_async(
            channel,
            connection,
            method,
            ticket,
        )

        mock_delete_s3_object.assert_not_called()
        self.assertEqual(connection.callbacks, [])
        self.assertEqual(channel.acknowledged_tags, [])

    @patch("worker.delete_s3_object")
    @patch("worker.generate_integration_plan")
    @patch("worker.requests.put")
    def test_success_updates_backend_deletes_file_and_acks_message(
        self,
        mock_put,
        mock_generate_plan,
        mock_delete_s3_object,
    ):
        mock_generate_plan.return_value = {
            "note_filename": "test-note",
            "note_content": "# Test note",
            "index_entry": "| [[test-note]] | Test | General |",
            "cross_links": [],
            "index_category": "General",
        }

        mock_put.side_effect = [
            FakeResponse(200),
            FakeResponse(200),
        ]

        connection = FakeConnection()
        channel = FakeChannel()
        method = SimpleNamespace(delivery_tag=456)

        ticket = {
            "jobId": "successful-job-id",
            "original_filename": "successful-document.pdf",
            "userApiKey": "fake-gemini-key",
            "s3Bucket": "test-bucket",
            "s3Key": "ingest/successful-document.pdf",
            "schemaText": "test schema",
            "indexText": "test index",
            "logTail": "",
        }

        worker.process_job_async(
            channel,
            connection,
            method,
            ticket,
        )

        mock_delete_s3_object.assert_called_once_with(
            "test-bucket",
            "ingest/successful-document.pdf",
        )

        self.assertEqual(len(connection.callbacks), 1)

        connection.callbacks[0]()

        self.assertEqual(channel.acknowledged_tags, [456])

    @patch("worker.delete_s3_object")
    @patch("worker.generate_integration_plan")
    @patch("worker.requests.put")
    def test_ai_failure_is_reported_to_backend(
        self,
        mock_put,
        mock_generate_plan,
        mock_delete_s3_object,
    ):
        friendly_error = (
            "Your Gemini API key is invalid. "
            "Please check it and try again."
        )

        mock_generate_plan.side_effect = Exception(friendly_error)

        mock_put.side_effect = [
            FakeResponse(200),  # starting progress update
            FakeResponse(200),  # failed status update
        ]

        connection = FakeConnection()
        channel = FakeChannel()
        method = SimpleNamespace(delivery_tag=789)

        ticket = {
            "jobId": "failed-ai-job-id",
            "original_filename": "failed-document.pdf",
            "userApiKey": "invalid-gemini-key",
            "s3Bucket": "test-bucket",
            "s3Key": "ingest/failed-document.pdf",
            "schemaText": "test schema",
            "indexText": "test index",
            "logTail": "",
        }

        worker.process_job_async(
            channel,
            connection,
            method,
            ticket,
        )

        failure_request = mock_put.call_args_list[1]
        failure_payload = failure_request.kwargs["json"]

        self.assertEqual(failure_payload["status"], "failed")
        self.assertEqual(failure_payload["stage"], "failed")
        self.assertEqual(
            failure_payload["stage_message"],
            friendly_error,
        )
        self.assertEqual(
            failure_payload["error"],
            friendly_error,
        )

        mock_delete_s3_object.assert_called_once_with(
            "test-bucket",
            "ingest/failed-document.pdf",
        )

        self.assertEqual(len(connection.callbacks), 1)

        connection.callbacks[0]()

        self.assertEqual(channel.acknowledged_tags, [789])


if __name__ == "__main__":
    unittest.main()