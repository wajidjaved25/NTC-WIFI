# RADIUS Integration - Implementation Summary

## What Was Integrated

### 1. RADIUS Helper Module (`app/utils/radius.py`)

**Functions Added:**
- `create_radius_user()` - Creates RADIUS user with session timeout
- `delete_radius_user()` - Removes RADIUS user
- `get_active_radius_sessions()` - Returns list of active WiFi sessions
- `get_user_session_history()` - Returns session history for a user
- `disconnect_user_session()` - Sends disconnect request to Omada
- `get_radius_statistics()` - Returns overall RADIUS statistics
- `update_user_session_timeout()` - Updates timeout for existing user

### 2. Updated Public Routes (`app/routes/public.py`)

**Modified `/register` endpoint:**
- Now creates RADIUS user automatically when user registers
- Uses mobile number as username
- Uses CNIC/Passport as password
- Sets default session timeout to 1 hour (3600 seconds)

**Authentication Flow:**
1. User registers → Creates record in `users` table
2. RADIUS user created → Creates records in `radcheck` and `radreply` tables
3. User connects to WiFi → Omada authenticates via RADIUS
4. User gets internet access for 1 hour

### 3. New Admin Routes (`app/routes/radius_admin.py`)

**New API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/radius/sessions/active` | GET | Get all active sessions |
| `/api/radius/sessions/user/{username}` | GET | Get session history for user |
| `/api/radius/sessions/disconnect/{username}` | POST | Disconnect user immediately |
| `/api/radius/statistics` | GET | Get RADIUS statistics |
| `/api/radius/users/{username}/timeout` | PATCH | Update session timeout |
| `/api/radius/users/{username}` | DELETE | Delete RADIUS user |

### 4. Updated Main App (`app/main.py`)

- Registered `radius_admin` router
- All RADIUS admin endpoints available at `/api/radius/*`

---

## How It Works

### User Registration Flow

```
1. User enters mobile, CNIC, name on portal
2. Verifies OTP
3. Registers → POST /api/public/register
4. Backend creates:
   - User record in `users` table
   - RADIUS user in `radcheck` table (username=mobile, password=CNIC)
   - Session timeout in `radreply` table (3600 seconds)
5. User can now authenticate on WiFi
```

### WiFi Authentication Flow

```
1. User connects to WiFi SSID
2. Omada shows captive portal
3. User enters credentials:
   - Username: 03001234567 (mobile)
   - Password: 12345-1234567-1 (CNIC)
4. Omada sends RADIUS request to FreeRADIUS server
5. FreeRADIUS queries database, validates credentials
6. Returns Access-Accept with Session-Timeout=3600
7. User gets internet for 1 hour
8. After 1 hour, automatic disconnect
```

### Session Management (Admin Portal)

Admins can:
- **View active sessions** - See who's online right now
- **View session history** - See past connections per user
- **Disconnect users** - Kick users off WiFi immediately
- **Change timeout** - Extend or reduce session time
- **Delete users** - Remove RADIUS accounts

---

## Database Tables Used

### Existing Tables (Your Portal)
- `users` - User registration data
- `otps` - OTP verification

### RADIUS Tables (New)
- `radcheck` - User authentication credentials
- `radreply` - User attributes (session timeout, bandwidth)
- `radacct` - Session accounting (start/stop time, data usage)
- `radpostauth` - Authentication logs

---

## Configuration Required on Production

### 1. FreeRADIUS Setup
```bash
# Already completed on server
- FreeRADIUS installed ✓
- PostgreSQL integration ✓
- Client configuration (Omada) ✓
```

### 2. Omada Configuration
```
Settings → Authentication → RADIUS:
- Server IP: 192.168.3.252
- Port: 1812
- Secret: testing123
- Accounting Port: 1813
```

### 3. Environment Variables
No new environment variables needed - uses existing database connection.

---

## Testing the Integration

### Test 1: User Registration
```bash
# Register new user via portal
# Check RADIUS user was created:
sudo -u postgres psql -d ntc_wifi_admin
SELECT * FROM radcheck WHERE username = '03001234567';
SELECT * FROM radreply WHERE username = '03001234567';
```

### Test 2: WiFi Authentication
```bash
# From Ubuntu server:
radtest 03001234567 12345-1234567-1 127.0.0.1 0 testing123
# Should return: Access-Accept with Session-Timeout = 3600
```

### Test 3: Admin API
```bash
# Get active sessions
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/radius/sessions/active

# Disconnect user
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/radius/sessions/disconnect/03001234567
```

---

## Next Steps for Production

1. **Deploy Backend Changes**
   ```bash
   cd /opt/ntc-wifi/backend
   git pull origin main
   sudo systemctl restart ntc-wifi-backend
   ```

2. **Test Full Flow**
   - Register new user on portal
   - Connect to WiFi
   - Authenticate with mobile/CNIC
   - Verify internet access

3. **Monitor RADIUS**
   ```bash
   sudo tail -f /var/log/syslog | grep radius
   ```

4. **(Optional) Build Admin UI**
   - Add "Active Sessions" page to admin portal
   - Add "Disconnect" button for each session
   - Add session statistics dashboard

---

## Files Changed

```
backend/
├── app/
│   ├── main.py                    # Added radius_admin router
│   ├── routes/
│   │   ├── public.py              # Updated register endpoint
│   │   └── radius_admin.py        # NEW - Admin session management
│   └── utils/
│       └── radius.py              # NEW - RADIUS helper functions
```

---

## Benefits of RADIUS Integration

✅ **Automatic Session Control** - Users disconnect after time limit
✅ **Real-time Disconnect** - Kick users off instantly from admin panel
✅ **Usage Tracking** - See exactly how long each user was online
✅ **Data Accounting** - Track bandwidth usage per user
✅ **Standard Protocol** - Industry-standard authentication
✅ **Better Performance** - Native Omada RADIUS support

---

## Support & Troubleshooting

**Issue: User can't connect to WiFi**
```bash
# Check RADIUS logs
sudo tail -f /var/log/freeradius/radius.log

# Check if user exists in RADIUS
sudo -u postgres psql -d ntc_wifi_admin -c \
  "SELECT * FROM radcheck WHERE username='03001234567';"
```

**Issue: Session not ending after timeout**
```bash
# Check radreply timeout value
sudo -u postgres psql -d ntc_wifi_admin -c \
  "SELECT * FROM radreply WHERE username='03001234567';"
```

**Issue: Disconnect not working**
```bash
# Test disconnect manually
echo "User-Name=03001234567" | \
  radclient 192.168.3.50:3799 disconnect testing123
```

---

## Contact

For issues or questions about RADIUS integration, check:
- FreeRADIUS logs: `/var/log/freeradius/radius.log`
- Backend logs: `sudo journalctl -u ntc-wifi-backend -f`
- Omada Controller: Settings → Authentication → RADIUS

**RADIUS is now fully integrated and ready for production! 🎉**
