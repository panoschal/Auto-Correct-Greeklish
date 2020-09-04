import ctypes

try:
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    def detect_current_language():
        curr_window = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(curr_window, 0)
        klid = user32.GetKeyboardLayout(thread_id)
        lid = klid & (2 ** 16 - 1)
        if lid == 1033:
            lang = 'en'
        elif lid == 1032:
            lang = 'el'
        else:
            lang = None
        return lang
except:
    def detect_current_language():
        return 'en'

