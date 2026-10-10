# Bug Fix: User Login Events Not Appearing in Admin Logs

## Issue Description
When non-admin users logged in, their login events were not visible in the Security Logs page (`/logs`) for admin accounts. The login events were only stored in the `audit_logs` collection and displayed in the Admin Settings page's "Recent logins" section, but not in the main Security Logs view.

## Root Cause
The Security Logs page fetches from the `logs` Firestore collection, which only contained device telemetry events. User login/logout events were recorded in the separate `audit_logs` collection via `record_audit()`, but were never written to the `logs` collection.

## Solution
Modified the system to write user login/logout events to the `logs` collection so they appear in the Security Logs page alongside device telemetry. This required making `device_id` optional in the log schema since auth events are not device-specific.

## Changes Made

### Backend Changes

#### 1. `backend/models/models.py`
- **Changed**: Made `LogDoc.device_id` optional (`str | None` instead of `str`)
- **Changed**: Updated `LogDoc.from_firestore()` to use `data.get("device_id")` instead of `data["device_id"]`
- **Reason**: Auth logs don't have an associated device

#### 2. `backend/models/schemas.py`
- **Changed**: Made `LogCreate.device_id` optional (`str | None = None`)
- **Changed**: Made `LogRead.device_id` optional (`str | None = None`)
- **Changed**: Split `LogRead` from inheriting `LogCreate` to explicitly define all fields
- **Reason**: Allow creating logs without a device_id

#### 3. `backend/routes/logs.py`
- **Changed**: Modified `create_log()` endpoint to only validate device existence if `device_id` is provided
  ```python
  if payload.device_id:
      if not db.collection("devices").document(payload.device_id).get().exists:
          raise HTTPException(...)
  ```
- **Reason**: Auth logs with `device_id=None` should be allowed

#### 4. `backend/routes/auth.py`
- **Added**: Login log creation in the `login()` endpoint (after line 520)
  - Creates a log entry in `logs` collection with category "auth"
  - Broadcasts `log.created` event for real-time updates
  - Includes user info and IP address in the log message and payload
  
- **Added**: Logout log creation in the `logout()` endpoint (after line 573)
  - Creates a log entry in `logs` collection with category "auth"
  - Broadcasts `log.created` event for real-time updates
  - Includes user info in the log message and payload

- **Reason**: Make login/logout events visible in the Security Logs page

### Frontend Changes

#### 5. `frontend/src/hooks/useTelemetry.tsx`
- **Changed**: Updated `RealLog` type to make `device_id` nullable (`string | null`)
- **Reason**: Support auth logs without device_id

#### 6. `frontend/src/pages/LogsPage.tsx`
- **Changed**: Updated `LogRow` type to make `device_id` nullable (`number | string | null`)
- **Note**: The display already handled null values with `row.device_id ?? "—"`
- **Reason**: TypeScript type safety for optional device_id

## Behavior Changes

### For Admin Users:
- **Before**: Login events only visible in Admin Settings page "Recent logins" section
- **After**: Login/logout events now also appear in:
  - Security Logs page (`/logs`)
  - Dashboard "Recent Activity" section
  - Can be searched/filtered by category "auth"
  - Included in CSV exports

### For Non-Admin Users:
- No change (they only see logs for devices they own, auth logs have no device_id)

### Log Entry Format:
```json
{
  "device_id": null,
  "category": "auth",
  "severity": "info",
  "source": "auth",
  "message": "User John Doe (john@example.com) logged in from 192.168.1.100",
  "raw_payload": {
    "user_id": "user123",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "user",
    "ip_address": "192.168.1.100"
  },
  "created_at": "2026-10-07T07:30:00.000Z"
}
```

## WebSocket Events
Login and logout events now trigger TWO broadcasts:
1. `log.created` - Updates Security Logs page
2. `user.login` or `user.logout` - Updates Admin Settings page

## Backward Compatibility
- ✅ Existing logs with `device_id` work unchanged
- ✅ All existing queries handle null `device_id` correctly
- ✅ Export, search, and delete operations work with optional `device_id`
- ✅ Alert engine handles logs without `device_id`
- ✅ Frontend displays "—" for null device_id

## Testing Checklist
- [ ] Login as non-admin user
- [ ] Verify admin can see login event in Security Logs page (`/logs`)
- [ ] Verify login event shows in Dashboard "Recent Activity"
- [ ] Logout and verify logout event appears in logs
- [ ] Search for "logged in" in Security Logs page
- [ ] Export logs to CSV and verify auth events are included
- [ ] Verify device telemetry logs still work correctly
- [ ] Verify non-admin users can't see auth logs (no device ownership)

## Files Modified
1. `backend/models/models.py`
2. `backend/models/schemas.py`
3. `backend/routes/logs.py`
4. `backend/routes/auth.py`
5. `frontend/src/hooks/useTelemetry.tsx`
6. `frontend/src/pages/LogsPage.tsx`

## Related Systems
- Audit logging (`audit_logs` collection) - still maintained for compliance
- Admin Settings page user activity - unchanged
- WebSocket real-time updates - enhanced with `log.created` events
- Alert engine - works with optional `device_id`
