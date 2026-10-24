#include <windows.h>
#include <stdio.h>

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // lpCmdLine contains the arguments passed by wineserver: "%ld %ld" (PID and Event handle)
    DWORD pid = 0;
    ULONG_PTR event_handle = 0;
    
    if (sscanf(lpCmdLine, "%lu %Iu", &pid, &event_handle) != 2) {
        if (sscanf(lpCmdLine, "%lx %Ix", &pid, &event_handle) != 2) {
            return 1;
        }
    }

    // Set up stdout/stderr redirection to C:\winedbg_crash_<pid>.log
    char log_path[MAX_PATH];
    sprintf(log_path, "C:\\winedbg_crash_%lu.log", pid);

    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(sa);
    sa.lpSecurityDescriptor = NULL;
    sa.bInheritHandle = TRUE; // Enable handle inheritance for the file handle

    HANDLE hFile = CreateFileA(log_path, GENERIC_WRITE, FILE_SHARE_READ, &sa,
                               CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        return 2;
    }

    // Prepare winedbg command line: "winedbg.exe --auto <pid> <event>"
    char cmd[512];
    sprintf(cmd, "winedbg.exe --auto %lu %Iu", pid, event_handle);

    // Set up startup info for the child process
    STARTUPINFOA si;
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE); // Inherit stdin
    si.hStdOutput = hFile; // Redirect stdout to file
    si.hStdError = hFile;  // Redirect stderr to file

    PROCESS_INFORMATION pi;
    memset(&pi, 0, sizeof(pi));

    // Start winedbg.exe. Enable handle inheritance so it gets the event handle and the file handle
    // Use CREATE_NO_WINDOW to suppress console window spawning
    if (CreateProcessA(NULL, cmd, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        // Wait for winedbg to finish
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        // If launching winedbg failed, write an error message to the log
        char err_msg[128];
        sprintf(err_msg, "Error: Failed to launch winedbg.exe. Error code: %lu\n", GetLastError());
        DWORD written = 0;
        WriteFile(hFile, err_msg, strlen(err_msg), &written, NULL);
    }

    CloseHandle(hFile);
    return 0;
}
