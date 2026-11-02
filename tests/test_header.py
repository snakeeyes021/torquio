"""The header's clock check against the inline Python the Bash header ran before (v0.5.0)."""
import contextlib
import datetime
import email.utils
import io
import unittest
import urllib.request
from unittest import mock

from torquio.cli import header

# print_header's clock check as of v0.5.0 (the python3 -c body, Bash's quoting undone)
OLD_CLOCK_CODE = r'''import urllib.request, email.utils, datetime
try:
    req = urllib.request.Request('https://www.google.com', method='HEAD')
    with urllib.request.urlopen(req, timeout=3) as response:
        srv_date_str = response.headers.get('Date')
    if srv_date_str:
        srv_dt = email.utils.parsedate_to_datetime(srv_date_str)
        local_dt = datetime.datetime.now(datetime.timezone.utc)
        diff = abs((srv_dt - local_dt).total_seconds())
        if diff > 180:
            print('')
            print('\033[38;5;179mSystem Clock Status:\033[0m')
            print(f'  \033[38;5;167mWARNING: System clock is out of sync by {int(diff)} seconds!\033[0m')
            print(f'  Server Time (UTC): {srv_dt.strftime("%Y-%m-%d %H:%M:%S")}')
            print(f'  System Time (UTC): {local_dt.strftime("%Y-%m-%d %H:%M:%S")}')
            print('  This is \033[38;5;167mHIGHLY LIKELY\033[0m to cause errors in the Steinberg Activation Manager.')
except Exception:
    print('')
    print('\033[38;5;244mSystem Clock Status:\033[0m')
    print('  \033[38;5;179mWARNING: Torquio attempts to verify that your system clock is\033[0m')
    print('  \033[38;5;179maccurate in order to prevent SAM licensing issues. Offline or\033[0m')
    print('  \033[38;5;179munable to contact time server. System clock could not be verified.\033[0m')
'''


class FakeResponse:
    def __init__(self, date):
        self.headers = {"Date": date} if date else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def outputs(urlopen):
    old, new = io.StringIO(), io.StringIO()
    with mock.patch.object(urllib.request, "urlopen", urlopen):
        with contextlib.redirect_stdout(old):
            exec(OLD_CLOCK_CODE, {})
        with contextlib.redirect_stdout(new):
            header.check_clock()
    return old.getvalue(), new.getvalue()


class ClockCheckMatchesOld(unittest.TestCase):
    def check(self, urlopen):
        old, new = outputs(urlopen)
        self.assertEqual(new, old)
        return new

    def server_time(self, offset):
        when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=offset)
        return lambda *a, **k: FakeResponse(email.utils.format_datetime(when, usegmt=True))

    def test_in_sync(self):
        self.assertEqual(self.check(self.server_time(30)), "")

    def test_out_of_sync(self):
        self.assertIn("out of sync", self.check(self.server_time(-3600)))

    def test_offline(self):
        def fail(*a, **k):
            raise OSError("offline")
        self.assertIn("could not be verified", self.check(fail))

    def test_no_date_header(self):
        self.assertEqual(self.check(lambda *a, **k: FakeResponse(None)), "")


if __name__ == "__main__":
    unittest.main()
