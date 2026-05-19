import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.settings_service import SettingsService
from domain.services.pruefung_service import PruefungService

def main():
    s = SettingsService()
    print("Settings:", s.get_all())
    ps = PruefungService(
        base_limit=s.get("BASE_LIMIT"),
        additional_adult_limit=s.get("ADDITIONAL_ADULT_LIMIT"),
        child_limit=s.get("CHILD_LIMIT"),
        hardship_factor=s.get("HARDSHIP_FACTOR"),
    )
    res = ps.evaluate_claim({"salary":1000}, {"rent":300}, 1, 0, "Sonstige")
    print("Entitlement limit:", res.entitlement_limit, "Hardship limit:", res.hardship_limit, "Free income:", res.free_income)

if __name__ == "__main__":
    main()
