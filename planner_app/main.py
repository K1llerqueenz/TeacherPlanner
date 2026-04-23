from planner_app.storage import ensure_storage
from planner_app.Ui.primary_screen import PrimaryScreen

import platform

if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("teacherplanner.app")
    except Exception:
        pass


def main() -> None:
    ensure_storage()
    app = PrimaryScreen()
    app.mainloop()


if __name__ == "__main__":
    main()
