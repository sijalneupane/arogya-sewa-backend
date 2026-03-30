# Khalti Payment Integration for Appointment Booking

## Overview

This system implements a **two-step payment process** for appointment booking:

1. **Advance Payment (10% non-refundable)** - Required to complete appointment booking
2. **Remaining Payment (90%)** - Can be paid later via Khalti or Cash

## Payment Flow

### Step 1: Initiate Appointment with Khalti Payment

**Endpoint:** `POST /api/v1/payments/khalti/initiate`

**Request:**
```json
{
  "appointment_id": "AP123456",
  "doctor_fee": 1000,
  "customer_phone": "9800000001"
}
```

**Response:**
```json
{
  "pidx": "bZQLD9wRVWo4CdESSfuSsB",
  "payment_url": "https://test-pay.khalti.com/?pidx=bZQLD9wRVWo4CdESSfuSsB",
  "expires_at": "2026-03-29T16:26:16.471649+05:45",
  "expires_in": 1800
}
```

**What happens:**
- ✅ 10% advance amount calculated: Rs. 100 (1000 paisa)
- ✅ Payment record created with status `PENDING`
- ✅ Khalti payment initiated, returns payment link
- ✅ Frontend redirects user to `payment_url`

**Backend Calculation:**
- Doctor Fee: Rs. 1000
- Advance (10%): Rs. 100 (in paisa: 10000)
- Due Amount: Rs. 900 (90%)

---

### Step 2: User Completes Payment on Khalti

User is redirected to Khalti payment gateway where they:
1. Enter Khalti credentials (Test: 9800000000, MPIN: 1111, OTP: 987654)
2. Complete payment
3. Khalti redirects back to return_url with payment status

---

### Step 3: Verify Payment & Complete Booking

**Endpoint:** `POST /api/v1/payments/khalti/verify`

**Query Parameters:**
```
pidx=bZQLD9wRVWo4CdESSfuSsB&appointment_id=AP123456
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Payment verified and appointment booking confirmed",
  "payment": {
    "payment_id": "PAY789456",
    "appointment_id": "AP123456",
    "paid_by_user_id": "USR123456",
    "amount": 100,
    "payment_method": "Khalti",
    "status": "Success",
    "transaction_id": "4H7AhoXDJWg5WjrcPT9ixW",
    "gateway_ref": "bZQLD9wRVWo4CdESSfuSsB",
    "paid_at": "2026-03-29T10:30:00Z",
    "created_at": "2026-03-29T10:20:00Z",
    "updated_at": "2026-03-29T10:30:00Z"
  }
}
```

**What happens:**
- ✅ Khalti payment verified via lookup API
- ✅ Payment record updated with transaction details
- ✅ Appointment payment_status changed to `PARTIAL`
- ✅ Appointment booking confirmed
- ✅ paid_amount = 100, due_amount = 900

**Database Updates:**
```sql
-- Appointment table
UPDATE appointment 
SET payment_status = 'Partial', 
    paid_amount = 100.0,
    due_amount = 900.0
WHERE appointment_id = 'AP123456';

-- Payment table
UPDATE payment 
SET status = 'Success',
    transaction_id = '4H7AhoXDJWg5WjrcPT9ixW',
    paid_at = NOW()
WHERE gateway_ref = 'bZQLD9wRVWo4CdESSfuSsB';
```

---

## Future: Record Remaining Payment

### Option 1: Khalti Payment for Remaining 90%

**Endpoint:** `POST /api/v1/payments/khalti/initiate`

```json
{
  "appointment_id": "AP123456",
  "doctor_fee": 900,
  "customer_phone": "9800000001"
}
```

Repeat the verification flow. This will:
- ✅ Create new payment record for remaining amount
- ✅ Update appointment to `PAID` status
- ✅ paid_amount becomes 1000, due_amount = 0

### Option 2: Cash Payment at Hospital

**Endpoint:** `POST /api/v1/payments/cash/record`

**Query Parameters:**
```
appointment_id=AP123456&amount=900&user_id=USR123456&remarks=Paid at counter
```

**Response:**
```json
{
  "payment_id": "PAY789457",
  "appointment_id": "AP123456",
  "paid_by_user_id": "USR123456",
  "amount": 900,
  "payment_method": "Cash",
  "status": "Success",
  "paid_at": "2026-03-29T11:30:00Z",
  "created_at": "2026-03-29T11:30:00Z"
}
```

---

## View Payment History

**Endpoint:** `GET /api/v1/payments/appointment/{appointment_id}`

**Response:**
```json
[
  {
    "payment_id": "PAY789456",
    "appointment_id": "AP123456",
    "amount": 100,
    "payment_method": "Khalti",
    "status": "Success",
    "paid_at": "2026-03-29T10:30:00Z"
  },
  {
    "payment_id": "PAY789457",
    "appointment_id": "AP123456",
    "amount": 900,
    "payment_method": "Cash",
    "status": "Success",
    "paid_at": "2026-03-29T11:30:00Z"
  }
]
```

---

## Enum Values (Word Case)

### Payment Status (Appointment Level)
- `Unpaid` - No payment made
- `Partial` - Advance 10% paid
- `Paid` - Full payment received
- `Refunded` - Payment refunded

### Payment Method
- `Khalti` - Khalti gateway
- `Esewa` - Esewa gateway (future)
- `Cash` - Cash payment

### Payment Transaction Status
- `Pending` - Payment initiated, awaiting verification
- `Success` - Payment completed successfully
- `Failed` - Payment failed
- `Refunded` - Payment refunded

---

## Configuration

Add these environment variables:

```bash
# Khalti Payment Gateway
KHALTI_SECRET_KEY=<your_sandbox_secret_key>
KHALTI_PUBLIC_KEY=<your_sandbox_public_key>
KHALTI_API_URL=https://dev.khalti.com/api/v2  # Sandbox
# KHALTI_API_URL=https://khalti.com/api/v2  # Production
ADVANCE_PAYMENT_PERCENTAGE=10.0
APP_DOMAIN=http://localhost:8000  # or production domain
```

---

## Complete Appointment Booking Flow (Updated)

### Current Flow (Before Payment)
```
1. POST /appointments/book
   ├─ Create appointment
   ├─ Return appointment_id
   └─ Appointment status: SCHEDULED
```

### New Flow (With Payment)
```
1. POST /payments/khalti/initiate
   ├─ Validate appointment
   ├─ Calculate 10% advance
   ├─ Call Khalti API
   ├─ Create payment record
   └─ Return: pidx, payment_url

2. Frontend redirects to payment_url
   └─ User completes payment on Khalti

3. POST /payments/khalti/verify
   ├─ Verify with Khalti
   ├─ Update payment record (SUCCESS)
   ├─ Update appointment.payment_status = PARTIAL
   └─ Booking confirmed!

4. [Later] Record remaining payment:
   ├─ Option A: POST /payments/khalti/initiate (for 90%)
   ├─ Option B: POST /payments/cash/record (for 90%)
   └─ Appointment payment_status = PAID
```

---

## Error Handling

### Payment Verification Failures

| Status | HTTP Code | Action |
|--------|-----------|--------|
| Success | 200 | Booking confirmed |
| Pending | 202 | Ask user to retry verification |
| User canceled | 400 | Show error, allow rebooking |
| Expired | 400 | Payment link expired, start over |
| Failed | 400 | Payment declined, try again |

---

## Testing with Khalti Sandbox

**Test Credentials:**
- Khalti ID: `9800000000`
- MPIN: `1111`
- OTP: `987654`
- Amount: Any value (minimum Rs. 10)

**Test Steps:**
1. Call `/payments/khalti/initiate` with doctor_fee
2. Copy the returned `payment_url`
3. Open in browser and use test credentials
4. You'll be redirected to return_url with callback params
5. Call `/payments/khalti/verify` with pidx from URL
6. Payment should be verified and appointment confirmed!

---

## Future Enhancements

- [ ] Webhook support for instant payment notifications
- [ ] Refund API integration
- [ ] Multiple payment methods (Esewa, Bank transfer)
- [ ] Payment reminders for due amounts
- [ ] Admin payment dashboard
- [ ] Receipt generation and email
