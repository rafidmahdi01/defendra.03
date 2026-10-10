# Isolation Button Fix

## Issue
The "Isolate" button was showing for all online devices, even those that were already isolated. This occurred because the frontend wasn't receiving or checking the isolation status of devices.

## Root Cause
The backend `DeviceRead` schema didn't include isolation fields (like `isolated_at`, `isolation_type`, etc.), even though these fields existed in the `DeviceDoc` model. This meant the API wasn't returning isolation status to the frontend.

## Solution

### 1. Backend Schema Update
**File**: `backend/models/schemas.py`

Added isolation fields to the `DeviceRead` schema:
- `isolated_at`
- `isolated_by_user_id`
- `isolated_by_email`
- `isolation_reason`
- `isolation_type`
- `isolation_grace_period`
- `can_auto_recover`
- `recovered_at`
- `recovered_by_user_id`
- `recovered_by_email`

### 2. Backend Route Update
**File**: `backend/routes/devices.py`

Updated the `_doc_to_read()` function to map all isolation fields from `DeviceDoc` to `DeviceRead`.

### 3. Frontend Type Update
**File**: `frontend/src/pages/DevicesPage.tsx`

Added isolation fields to the `Device` TypeScript type to match the backend schema.

### 4. Frontend Logic Update
**File**: `frontend/src/pages/DevicesPage.tsx`

Updated button rendering logic:
- **Isolate button**: Now only shows when `s === "online" && !device.isolated_at`
- **Recover button**: Now shows when `device.isolated_at && !device.recovered_at`

This ensures:
- Isolated devices won't show the "Isolate" button
- Only currently isolated devices (not yet recovered) show the "Recover" button
- The logic is based on actual isolation state rather than just the status field

## Testing
Both backend and frontend compiled successfully without errors.

## Date
October 7, 2026
