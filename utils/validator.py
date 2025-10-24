"""
Data validation utilities for bank statement data
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import MAX_TRANSACTION_AMOUNT, MIN_TRANSACTION_AMOUNT, REQUIRED_FIELDS


class Validator:
    """
    Validator for bank statement data.
    """

    @staticmethod
    def validate_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in transaction or transaction[field] is None:
                errors.append(f"Missing required field: {field}")

        # Validate date
        if 'date' in transaction:
            date_str = transaction['date']
            try:
                datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid date format: {date_str}")

        # Validate amount
        if 'amount' in transaction:
            amount = transaction['amount']
            try:
                amount = float(amount)

                if abs(amount) > MAX_TRANSACTION_AMOUNT:
                    warnings.append(f"Suspiciously high amount: {amount}")

                if abs(amount) < MIN_TRANSACTION_AMOUNT and amount != 0:
                    warnings.append(f"Suspiciously low amount: {amount}")

            except (ValueError, TypeError):
                errors.append(f"Invalid amount: {amount}")

        # Validate description
        if 'description' in transaction:
            desc = transaction['description']
            if not desc or not isinstance(desc, str):
                warnings.append("Empty or invalid description")
            elif len(desc) < 3:
                warnings.append("Very short description")

        # Validate balance_after if present
        if 'balance_after' in transaction:
            balance = transaction['balance_after']
            try:
                balance = float(balance)
                if balance < 0:
                    warnings.append(f"Negative balance: {balance}")
            except (ValueError, TypeError):
                errors.append(f"Invalid balance: {balance}")

        # Check for merchant info
        if 'merchant' not in transaction or not transaction['merchant'].get('name'):
            warnings.append("Missing merchant information")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    @staticmethod
    def validate_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a list of transactions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with overall validation results
        """
        if not transactions:
            return {
                "status": "error",
                "message": "No transactions to validate",
                "errors": ["Empty transaction list"],
                "warnings": []
            }

        all_errors = []
        all_warnings = []
        valid_count = 0

        for i, txn in enumerate(transactions):
            result = Validator.validate_transaction(txn)

            if result['valid']:
                valid_count += 1

            for error in result['errors']:
                all_errors.append(f"Transaction {i}: {error}")

            for warning in result['warnings']:
                all_warnings.append(f"Transaction {i}: {warning}")

        # Check for date ordering
        dates = [txn.get('date') for txn in transactions if txn.get('date')]
        if dates and dates != sorted(dates):
            all_warnings.append("Transactions are not in chronological order")

        status = "valid" if len(all_errors) == 0 else "invalid"

        return {
            "status": status,
            "total_transactions": len(transactions),
            "valid_transactions": valid_count,
            "errors": all_errors,
            "warnings": all_warnings
        }

    @staticmethod
    def validate_balance(balance: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate balance information.

        Args:
            balance: Balance dictionary

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        required_fields = ['opening', 'closing']
        for field in required_fields:
            if field not in balance:
                errors.append(f"Missing balance field: {field}")
            else:
                try:
                    val = float(balance[field])
                    if val < 0:
                        warnings.append(f"Negative {field} balance: {val}")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {field} balance: {balance[field]}")

        # Check if closing = opening + net change (if we have transactions)
        if 'opening' in balance and 'closing' in balance:
            opening = float(balance['opening'])
            closing = float(balance['closing'])
            net_change = closing - opening

            if 'net_change' in balance:
                expected = float(balance['net_change'])
                if abs(net_change - expected) > 0.01:  # Allow small rounding errors
                    warnings.append(
                        f"Balance mismatch: expected net change {expected}, "
                        f"calculated {net_change}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate metadata.

        Args:
            metadata: Metadata dictionary

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        required_fields = ['bank', 'account_number', 'statement_period']
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing metadata field: {field}")

        # Validate statement period
        if 'statement_period' in metadata:
            period = metadata['statement_period']
            if not isinstance(period, dict):
                errors.append("Invalid statement_period format")
            else:
                if 'start_date' not in period:
                    errors.append("Missing start_date in statement_period")
                if 'end_date' not in period:
                    errors.append("Missing end_date in statement_period")

                # Check date order
                if 'start_date' in period and 'end_date' in period:
                    try:
                        start = datetime.fromisoformat(period['start_date'])
                        end = datetime.fromisoformat(period['end_date'])
                        if start > end:
                            errors.append("start_date is after end_date")
                    except (ValueError, AttributeError):
                        errors.append("Invalid date format in statement_period")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    @classmethod
    def validate_statement(cls, statement: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate entire statement data.

        Args:
            statement: Statement dictionary

        Returns:
            Dictionary with comprehensive validation results
        """
        all_errors = []
        all_warnings = []

        # Validate structure
        required_sections = ['metadata', 'balance', 'transactions']
        for section in required_sections:
            if section not in statement:
                all_errors.append(f"Missing section: {section}")

        # Validate each section
        if 'metadata' in statement:
            meta_result = cls.validate_metadata(statement['metadata'])
            all_errors.extend(meta_result['errors'])
            all_warnings.extend(meta_result['warnings'])

        if 'balance' in statement:
            balance_result = cls.validate_balance(statement['balance'])
            all_errors.extend(balance_result['errors'])
            all_warnings.extend(balance_result['warnings'])

        if 'transactions' in statement:
            txn_result = cls.validate_transactions(statement['transactions'])
            all_errors.extend(txn_result['errors'])
            all_warnings.extend(txn_result['warnings'])

        status = "valid" if len(all_errors) == 0 else "invalid"

        return {
            "status": status,
            "errors": all_errors,
            "warnings": all_warnings
        }


def validate_statement(statement: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate a statement.

    Args:
        statement: Statement dictionary

    Returns:
        Validation results
    """
    return Validator.validate_statement(statement)
