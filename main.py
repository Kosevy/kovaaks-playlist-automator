import sys
import os

# Asegurar que el directorio raíz del proyecto esté en sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import KPAApp


def main():
    app = KPAApp()
    app.mainloop()


if __name__ == "__main__":
    main()

