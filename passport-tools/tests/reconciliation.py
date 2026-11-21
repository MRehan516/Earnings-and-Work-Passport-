import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())

def calculate_event_key(payer: Optional[str], period_start: Optional[str], period_end: Optional[str], net_amount: Optional[float], reference: Optional[str]) -> str:
    norm_payer = normalize_text(payer)
    norm_period = f"{period_start or ''}_{period_end or ''}"
    norm_net = f"{net_amount:.2f}" if net_amount is not None else ""
    norm_ref = normalize_text(reference)
    return f"{norm_payer}:{norm_period}:{norm_net}:{norm_ref}"

class PermissionError(Exception):
    pass

class StatusTransitions:
    WORKER_ALLOWED_PARTY_STATUSES = {"added_by_worker", "invitation_sent", "archived"}
    WORKER_ALLOWED_RELATIONSHIPS = {"worker_declared", "counterparty_invited", "ended", "disputed"}
    WORKER_ALLOWED_PAYMENTS = {"declared", "document_uploaded", "payment_claimed", "disputed"}

    @staticmethod
    def worker_change_party_contact_status(current: str, target: str, reason: str = "", step_up_verified: bool = False) -> str:
        if target in {"contact_verified", "organisation_checked", "integration_connected"}:
            raise PermissionError(f"Worker cannot set party status to {target}")
        if target == "archived":
            if not step_up_verified or not reason:
                raise PermissionError("Archiving a party requires a valid reason and step-up verification")
        return target

    @staticmethod
    def worker_change_relationship_status(current: str, target: str, reason: str = "", step_up_verified: bool = False) -> str:
        if target in {"counterparty_acknowledged"}:
            raise PermissionError(f"Worker cannot set relationship status to {target}")
        if target in {"ended", "disputed"}:
            if not step_up_verified or not reason:
                raise PermissionError(f"Transitioning relationship to {target} requires a reason and step-up verification")
        return target

    @staticmethod
    def worker_change_payment_status(current: str, target: str, reason: str = "", step_up_verified: bool = False) -> str:
        if target in {"payer_confirmed", "bank_matched", "platform_payout"}:
            raise PermissionError(f"Worker cannot directly set payment status to {target}")
        if target == "disputed" and not reason:
            raise PermissionError("Disputing a payment requires a reason")
        return target

    @staticmethod
    def counterparty_confirm(question: str, answer: str, corrected_amount: Optional[float] = None) -> Dict[str, Any]:
        valid_answers = {"yes", "no", "unsure", "corrected_amount", "declined"}
        if answer not in valid_answers:
            raise ValueError(f"Invalid confirmation answer: {answer}")
        
        status_update = {}
        if question == "work_happened":
            status_update["relationship_status"] = "counterparty_acknowledged" if answer == "yes" else "disputed"
        elif question == "payment_made":
            if answer == "yes":
                status_update["payment_status"] = "payer_confirmed"
            elif answer == "no":
                status_update["payment_status"] = "disputed"
            elif answer == "corrected_amount":
                status_update["payment_status"] = "disputed"
                status_update["corrected_amount"] = corrected_amount
        return status_update

class ReconciliationEngine:
    def __init__(self):
        pass

    @staticmethod
    def check_internal_dispute(income: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        gross = income.get("gross")
        deductions = income.get("deductions") or 0.0
        net = income.get("net")
        if gross is not None and net is not None:
            if abs(gross - deductions - net) > 1.0:
                return True, f"Discrepancy: gross ({gross}) - deductions ({deductions}) != net ({net})"
        
        client_amount = income.get("client_confirmed_amount")
        invoice_amount = income.get("invoice_amount")
        if client_amount is not None and invoice_amount is not None:
            if abs(client_amount - invoice_amount) > 1.0:
                return True, f"Disputed amount: client confirmed {client_amount} vs invoice {invoice_amount}"
        return False, None

    @staticmethod
    def determine_evidence_label(income: Dict[str, Any], is_bank_matched: bool = False) -> str:
        is_disputed, _ = ReconciliationEngine.check_internal_dispute(income)
        if is_disputed or income.get("payment_status") == "disputed":
            return "disputed"
        
        acq_method = income.get("acquisition_method", "upload")
        if acq_method in {"simulated_api", "simulated_aa"}:
            return "source_verified_simulated"
        
        if is_bank_matched:
            return "source_matched"
        
        if acq_method == "upload" and income.get("worker_confirmed", False):
            return "document_extracted"
            
        return "self_declared"

    @staticmethod
    def compute_expected_amount(income: Dict[str, Any]) -> float:
        if income.get("client_confirmed_amount") is not None:
            return float(income["client_confirmed_amount"])
        if income.get("invoice_amount") is not None:
            return float(income["invoice_amount"])
        if income.get("net") is not None:
            return float(income["net"])
        if income.get("gross") is not None:
            return float(income["gross"])
        return 0.0

    @staticmethod
    def parse_date(date_val: Any) -> Optional[datetime]:
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val
        try:
            return datetime.strptime(str(date_val)[:10], "%Y-%m-%d")
        except Exception:
            return None

    @staticmethod
    def is_date_in_window(credit_date_str: str, income: Dict[str, Any]) -> bool:
        credit_date = ReconciliationEngine.parse_date(credit_date_str)
        if not credit_date:
            return False

        # Platform payout window: +/-3 days of payout_date
        payout_date = ReconciliationEngine.parse_date(income.get("payout_date") or income.get("record_date"))
        if income.get("source_type") == "platform" or income.get("platform"):
            if payout_date:
                diff = abs((credit_date - payout_date).days)
                return diff <= 3
        
        # Client invoice window: +/-7 days of stated payment date, or 0 to 30 days after invoice date
        stated_payment_date = ReconciliationEngine.parse_date(income.get("client_payment_date"))
        if stated_payment_date:
            diff = abs((credit_date - stated_payment_date).days)
            return diff <= 7

        invoice_date = ReconciliationEngine.parse_date(income.get("record_date") or income.get("invoice_date"))
        if invoice_date:
            diff = (credit_date - invoice_date).days
            return 0 <= diff <= 30

        return False

    @staticmethod
    def calculate_name_overlap(descriptor: str, income: Dict[str, Any]) -> float:
        norm_desc = normalize_text(descriptor)
        names_to_check = [
            income.get("payer"),
            income.get("client_name"),
            income.get("platform"),
            income.get("reference")
        ]
        
        score = 0.0
        for name in names_to_check:
            if not name:
                continue
            norm_name = normalize_text(name)
            if not norm_name:
                continue
            
            # Substring match or token overlap
            if norm_name in norm_desc or norm_desc in norm_name:
                score = max(score, 1.0)
            else:
                tokens = [t for t in re.split(r"[^a-z0-9]", name.lower()) if len(t) >= 3]
                desc_tokens = [t for t in re.split(r"[^a-z0-9]", descriptor.lower()) if len(t) >= 3]
                overlap = set(tokens).intersection(set(desc_tokens))
                if overlap:
                    score = max(score, len(overlap) / max(len(tokens), 1))
        return score

    @classmethod
    def match_credits(cls, income_records: List[Dict[str, Any]], bank_credits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deduplicates income records, matches 1 credit to 1 income deterministically,
        classifies credits, assigns labels and returns full reconciliation.
        """
        # Deduplication
        deduped_incomes = []
        seen_keys = set()
        duplicates = []
        
        for inc in income_records:
            key = inc.get("event_key") or calculate_event_key(
                inc.get("payer"), inc.get("period_start"), inc.get("period_end"),
                inc.get("net"), inc.get("reference")
            )
            file_hash = inc.get("file_hash")
            dedupe_id = file_hash or key
            if dedupe_id in seen_keys:
                duplicates.append(inc)
            else:
                seen_keys.add(dedupe_id)
                inc_copy = dict(inc)
                inc_copy["event_key"] = key
                deduped_incomes.append(inc_copy)

        # Match credits
        matched_income_ids = set()
        matched_credit_indices = set()
        matches = []
        reconciliations = []

        for inc in deduped_incomes:
            inc_id = inc.get("id") or inc.get("event_key")
            
            # If internally disputed, never auto-match to bank
            is_disputed, reason = cls.check_internal_dispute(inc)
            if is_disputed:
                inc["evidence_label"] = "disputed"
                inc["payment_status"] = "disputed"
                inc["dispute_reason"] = reason
                continue

            expected_amt = cls.compute_expected_amount(inc)
            candidates = []

            for idx, credit in enumerate(bank_credits):
                if idx in matched_credit_indices:
                    continue
                c_amt = float(credit.get("credit", credit.get("amount", 0)))
                if c_amt <= 0:
                    continue
                
                # Rule 1: abs(amount - expected) <= 1
                if abs(c_amt - expected_amt) <= 1.0:
                    # Rule 2: Date window
                    if cls.is_date_in_window(credit.get("date"), inc):
                        overlap = cls.calculate_name_overlap(credit.get("descriptor", ""), inc)
                        candidates.append((idx, credit, overlap))

            if not candidates:
                inc["evidence_label"] = cls.determine_evidence_label(inc, is_bank_matched=False)
                reconciliations.append({"income_id": inc_id, "outcome": "none", "reason": "No matching credit found"})
            elif len(candidates) == 1:
                idx, credit, overlap = candidates[0]
                matched_credit_indices.add(idx)
                matched_income_ids.add(inc_id)
                outcome = "strong" if overlap > 0 else "possible"
                inc["evidence_label"] = "source_matched"
                inc["payment_status"] = "bank_matched"
                credit["matched_income_id"] = inc_id
                credit["classification"] = "work_payment"
                matches.append({"income": inc, "credit": credit, "outcome": outcome})
                reconciliations.append({"income_id": inc_id, "credit_index": idx, "outcome": outcome, "overlap": overlap})
            else:
                # Rank candidates by name overlap
                candidates.sort(key=lambda x: x[2], reverse=True)
                if candidates[0][2] > 0 and candidates[0][2] > candidates[1][2]:
                    # Clear winner
                    idx, credit, overlap = candidates[0]
                    matched_credit_indices.add(idx)
                    matched_income_ids.add(inc_id)
                    inc["evidence_label"] = "source_matched"
                    inc["payment_status"] = "bank_matched"
                    credit["matched_income_id"] = inc_id
                    credit["classification"] = "work_payment"
                    matches.append({"income": inc, "credit": credit, "outcome": "strong"})
                    reconciliations.append({"income_id": inc_id, "credit_index": idx, "outcome": "strong", "overlap": overlap})
                else:
                    inc["evidence_label"] = cls.determine_evidence_label(inc, is_bank_matched=False)
                    reconciliations.append({"income_id": inc_id, "outcome": "multiple", "candidates": [c[0] for c in candidates]})

        # Classify remaining credits
        unclassified_credits = []
        for idx, credit in enumerate(bank_credits):
            if idx not in matched_credit_indices:
                c_amt = float(credit.get("credit", credit.get("amount", 0)))
                if c_amt <= 0:
                    credit["classification"] = "not_income"
                else:
                    desc = credit.get("descriptor", "").upper()
                    if "UPI" in desc and not any(kw in desc for kw in ["PVT", "LTD", "TECH", "SERVICES", "STUDIO", "STORE"]):
                        credit["classification"] = "unclassified"
                        credit["flag"] = "possible personal transfer"
                    else:
                        credit["classification"] = "unclassified"
                    unclassified_credits.append(credit)

        return {
            "deduped_incomes": deduped_incomes,
            "duplicates": duplicates,
            "matches": matches,
            "reconciliations": reconciliations,
            "unclassified_credits": unclassified_credits
        }
