"""Tests bổ sung cho cải tiến Bài 4: kiểm tra liên kết incident dẫn chiếu và lỗi provider."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent import run_agent
from bonus.tools import BonusTools
from status_tools import StatusTools
from tests.test_lab import FakeProvider, final, tool_call


class FailingProvider:
    def complete(self, messages, schemas):
        raise RuntimeError('Simulated network error')


class ImprovementTests(unittest.TestCase):
    def test_unfollowed_incident_reference_triggers_revision(self):
        fake = FakeProvider([
            tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"h02n9572mx9y"}'),
            final('Đã đọc h02n9572mx9y. Nguồn: https://stspg.io/7pwv28hvkmz8'),
            tool_call('2', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
            final('Đã đọc cả xr3myzj7ms51. Nguồn: https://stspg.io/pjgptg3cfc6n'),
        ])
        result = run_agent('Kiểm tra h02n9572mx9y và liên kết của nó', fake, StatusTools(), max_steps=6)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(e['event'] == 'validation_unfollowed_reference' for e in result['trace']))
        tool_ids = [e['arguments']['incident_id'] for e in result['trace'] if e['event'] == 'tool']
        self.assertEqual(tool_ids, ['h02n9572mx9y', 'xr3myzj7ms51'])

    def test_cross_provider_reference_uses_target_host_provider(self):
        fake = FakeProvider([
            tool_call('1', 'get_incident_details', '{"provider":"vercel","incident_id":"sps6n39gm4sg","offset":2,"limit":3}'),
            final('Chưa đọc incident GitHub liên quan. Nguồn: https://stspg.io/cfrfjg8fqxfr'),
            final('Giữ nguyên kết quả. Nguồn: https://stspg.io/cfrfjg8fqxfr'),
        ])
        result = run_agent('Kiểm tra Vercel sps6n39gm4sg', fake, BonusTools(), max_steps=5)
        self.assertEqual(result['status'], 'completed')
        events = [e for e in result['trace'] if e['event'] == 'validation_unfollowed_reference']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['references'], [{'provider': 'github', 'incident_id': '93njd414rpbx'}])

    def test_provider_exception_returns_error_status(self):
        result = run_agent('Kiểm tra', FailingProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertTrue(any(e['event'] == 'error' for e in result['trace']))


if __name__ == '__main__':
    unittest.main()

