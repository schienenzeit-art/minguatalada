from pathlib import Path
from services.pdf_service import PDFService


class DummyClaimService:
    def get_claim_by_id(self, claim_id: int):
        return {
            "id": claim_id,
            "case_number": f"AS-2026-{claim_id:06d}",
            "person_display_name": "Max Mustermann",
            "location_name": "Zentrale",
            "category_name": "Basis",
            "status": "ANSPRUCHSBERECHTIGT",
            "examiner_name": "Prüfer 1",
            "examiner_id": 1,
            "evaluation_date": "2026-05-19",
            "description": "Testfall",
            "incomes": [{"type": "Gehalt", "amount": 1200}],
            "expenses": [{"type": "Miete", "amount": 500, "has_proof": True}],
            "free_income": 300.0,
            "entitlement_limit": 820.0,
            "hardship_limit": 902.0,
            "evaluation_reason": "Automatischer Test",
        }


def run_test():
    pdf_root = Path(__file__).resolve().parent.parent / "data" / "pdfs"
    pdf_root.mkdir(parents=True, exist_ok=True)
    out = pdf_root / "test_pruefung.pdf"

    svc = PDFService()
    svc.claim_service = DummyClaimService()

    path = svc.generate_claim_evaluation_pdf(claim_id=1, file_path=str(out))
    print("PDF generated:", path)


if __name__ == "__main__":
    run_test()
