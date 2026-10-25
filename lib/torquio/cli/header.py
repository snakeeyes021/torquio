"""The banner at the top of the main menu, with the system clock check."""
import datetime
import email.utils
import urllib.request

from ..ui import GRAY, RESET, WINE, echo

LOGO = [
    ' ████████╗  ██████╗  ██████╗   ██████╗  ██╗   ██╗ ██╗  ██████╗ ',
    ' ╚══██╔══╝ ██╔═══██╗ ██╔══██╗ ██╔═══██╗ ██║   ██║ ██║ ██╔═══██╗',
    '    ██║    ██║   ██║ ██████╔╝ ██║   ██║ ██║   ██║ ██║ ██║   ██║',
    '    ██║    ██║   ██║ ██╔══██╗ ██║▄▄ ██║ ██║   ██║ ██║ ██║   ██║',
    '    ██║    ╚██████╔╝ ██║  ██║ ╚██████╔╝ ╚██████╔╝ ██║ ╚██████╔╝',
    '    ╚═╝     ╚═════╝  ╚═╝  ╚═╝  ╚══▀▀═╝   ╚═════╝  ╚═╝  ╚═════╝ ',
    '                              —— B Y  R E D  F O X  L A B S ——',
]


def check_clock():
    """Warn when the system clock is off by more than 3 minutes (the Steinberg Activation Manager fails then),
    or when it can't be checked."""
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


def show():
    echo(f"{GRAY}================================================================{RESET}")
    for line in LOGO:
        echo(f"{WINE}{line}{RESET}")
    echo(f"{GRAY}================================================================{RESET}")
    check_clock()
