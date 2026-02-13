"""
End-to-end API test script.
Uses urllib (no external deps needed).
"""

import json
import urllib.request
import urllib.error

BASE = 'http://localhost:8000/api'


def api_call(method, url, data=None):
    """Make an API call and return status + body."""
    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method=method,
            )
        else:
            req = urllib.request.Request(url, method=method)

        response = urllib.request.urlopen(req)
        body = json.loads(response.read().decode('utf-8'))
        return response.status, body
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode('utf-8'))
        return e.code, body


def main():
    print('=' * 60)
    print('CREDIT APPROVAL SYSTEM — END-TO-END API TESTS')
    print('=' * 60)

    # ─── Test 1: Register Customer ───
    print('\n--- TEST 1: POST /api/register ---')
    status, body = api_call('POST', f'{BASE}/register', {
        'first_name': 'Rahul',
        'last_name': 'Sharma',
        'age': 28,
        'monthly_income': 50000,
        'phone_number': 9876543210,
    })
    print(f'Status: {status}')
    print(f'Response: {json.dumps(body, indent=2)}')

    customer_id = body.get('customer_id')
    assert status == 201, f'Expected 201, got {status}'
    assert body['approved_limit'] == 1800000, 'Approved limit wrong'
    print('✓ PASSED')

    # ─── Test 2: Check Eligibility ───
    print('\n--- TEST 2: POST /api/check-eligibility ---')
    status, body = api_call('POST', f'{BASE}/check-eligibility', {
        'customer_id': customer_id,
        'loan_amount': 500000,
        'interest_rate': 15.0,
        'tenure': 24,
    })
    print(f'Status: {status}')
    print(f'Response: {json.dumps(body, indent=2)}')

    assert status == 200, f'Expected 200, got {status}'
    assert 'approval' in body, 'Missing approval field'
    assert 'monthly_installment' in body, 'Missing monthly_installment'
    print('✓ PASSED')

    # ─── Test 3: Create Loan ───
    print('\n--- TEST 3: POST /api/create-loan ---')
    status, body = api_call('POST', f'{BASE}/create-loan', {
        'customer_id': customer_id,
        'loan_amount': 500000,
        'interest_rate': 15.0,
        'tenure': 24,
    })
    print(f'Status: {status}')
    print(f'Response: {json.dumps(body, indent=2)}')

    loan_id = body.get('loan_id')
    assert status in [200, 201], f'Expected 200/201, got {status}'
    assert 'loan_approved' in body, 'Missing loan_approved'
    assert 'monthly_installment' in body, 'Missing monthly_installment'
    print('✓ PASSED')

    # ─── Test 4: View Loan ───
    if loan_id:
        print(f'\n--- TEST 4: GET /api/view-loan/{loan_id} ---')
        status, body = api_call('GET', f'{BASE}/view-loan/{loan_id}')
        print(f'Status: {status}')
        print(f'Response: {json.dumps(body, indent=2)}')

        assert status == 200, f'Expected 200, got {status}'
        assert 'customer' in body, 'Missing customer field'
        assert body['customer']['first_name'] == 'Rahul'
        print('✓ PASSED')
    else:
        print('\n--- TEST 4: SKIPPED (loan not approved) ---')

    # ─── Test 5: View Customer Loans ───
    print(f'\n--- TEST 5: GET /api/view-loans/{customer_id} ---')
    status, body = api_call('GET', f'{BASE}/view-loans/{customer_id}')
    print(f'Status: {status}')
    print(f'Response: {json.dumps(body, indent=2)}')

    assert status == 200, f'Expected 200, got {status}'
    assert isinstance(body, list), 'Expected list response'
    print('✓ PASSED')

    # ─── Test 6: 404 for non-existent resources ───
    print('\n--- TEST 6: Error handling (404s) ---')
    status, body = api_call('GET', f'{BASE}/view-loan/9999')
    assert status == 404, f'Expected 404, got {status}'
    print(f'  view-loan/9999 → {status} ✓')

    status, body = api_call('GET', f'{BASE}/view-loans/9999')
    assert status == 404, f'Expected 404, got {status}'
    print(f'  view-loans/9999 → {status} ✓')

    status, body = api_call('POST', f'{BASE}/check-eligibility', {
        'customer_id': 9999,
        'loan_amount': 100000,
        'interest_rate': 12.0,
        'tenure': 12,
    })
    assert status == 404, f'Expected 404, got {status}'
    print(f'  check-eligibility (bad customer) → {status} ✓')
    print('✓ PASSED')

    # ─── Test 7: Validation errors ───
    print('\n--- TEST 7: Validation errors (400s) ---')
    status, body = api_call('POST', f'{BASE}/register', {
        'first_name': 'Bad',
    })
    assert status == 400, f'Expected 400, got {status}'
    print(f'  register (missing fields) → {status} ✓')
    print('✓ PASSED')

    print('\n' + '=' * 60)
    print('ALL 7 TESTS PASSED ✓')
    print('=' * 60)


if __name__ == '__main__':
    main()
