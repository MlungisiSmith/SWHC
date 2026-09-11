# SWHC v2 - Authentication Error Resolution Guide

## 🔍 You're seeing "Authentication failed" - Here's What This Means

The error `Authentication failed` can occur for several reasons:

### **Most Common Causes**

1. **Switch IP not reachable** - The container can't access 192.168.101.212 or 192.168.101.101
2. **SSH port (22) not open** - Firewall blocks SSH traffic
3. **Wrong credentials** - Username/password incorrect
4. **Switch offline** - Device is powered down or disconnected

---

## 🛠️ Diagnostic Steps

### Step 1: Verify Dashboard is Running
```bash
docker ps
# Should show: switch-health-dashboard (healthy)
```

### Step 2: Check API is Responsive
Visit http://localhost:8787/docs and expand the health endpoint

### Step 3: Test Network Connectivity
From your **host machine** (not inside the container):
```bash
ping 192.168.101.212
ping 192.168.101.101
```

If ping fails → **Network/switch connectivity issue**

### Step 4: Test SSH Access
```bash
ssh networks@192.168.101.212
```

When prompted for password, enter: `w00Lw0rTh$`

**If SSH connects** → Authentication works, issue is with container networking  
**If SSH fails** → Check switch SSH settings or credentials

---

## 🚨 Common Issues & Solutions

### Issue: "Connection timeout"
**Cause:** Switch is unreachable

**Solutions:**
- [ ] Verify IP address: 192.168.101.212 (Cisco) or 192.168.101.101 (Huawei)
- [ ] Ensure switch is powered ON
- [ ] Check physical network cable is connected
- [ ] Verify firewall allows traffic to switch IP
- [ ] Test: `ping 192.168.101.212` from your host

### Issue: "Authentication failed"
**Cause:** Wrong credentials or switch rejects SSH

**Solutions:**
- [ ] Verify username: `networks`
- [ ] Verify password: `w00Lw0rTh$` (note the capitalization)
- [ ] Test SSH manually: `ssh networks@192.168.101.212`
- [ ] Check switch SSH is enabled: `show ip ssh` (Cisco)
- [ ] Verify .env file has correct credentials

### Issue: Dashboard loads but "API Offline"
**Cause:** FastAPI not responding

**Solutions:**
```bash
docker logs switch-health-dashboard
# Look for error messages during startup

docker restart switch-health-dashboard
# Restart the service
```

---

## 🔧 Environment Configuration

Your `.env` file should contain:

```bash
SWITCH_USERNAME=networks
SWITCH_PASSWORD=w00Lw0rTh$
SWITCH_ENABLE_SECRET=w00Lw0rTh$
APP_ENV=production
APP_DEBUG=false
```

**Location:** `/home/user/SWHC/.env` (or your project root)

---

## 🎯 What Should Work

After successful connection, you should see:

```
✅ Hostname: [Switch name]
✅ Vendor: Cisco / Huawei
✅ IP Address: 192.168.101.212
✅ Status: online
```

---

## 📞 Getting More Information

### View Application Logs
```bash
docker logs switch-health-dashboard -f
# -f means "follow" (live updates)
```

Look for these messages:
- `[AUTH ERROR]` → Authentication problem
- `[TIMEOUT ERROR]` → Network unreachable
- `Application startup complete` → App is ready

### View Database Activity
```bash
# Check if database exists
ls -la data/swch.db

# Database stores: switches, health metrics, config audit trail
```

### Test Individual Endpoints

**Health Check:**
```bash
curl http://localhost:8787/api/v1/health
```

**List Switches:**
```bash
curl http://localhost:8787/api/v1/switches
```

**Test Health Check (from API):**
```bash
curl -X POST http://localhost:8787/api/v1/switches/check-health \
  -H "Content-Type: application/json" \
  -d '{"ip_address":"192.168.101.212","vendor":"cisco"}'
```

---

## 🌐 Docker Network Troubleshooting

The container runs in an isolated Docker network. Sometimes it can't reach external switches.

### Check Container's Network Access
```bash
# From inside the container
docker exec switch-health-dashboard ping 192.168.101.212

# If this fails, the Docker network can't reach your switch network
```

### Solution: Use Host Network (Advanced)
Edit `docker-compose.yml` and add `network_mode: host` under the web service:

```yaml
services:
  web:
    ...
    network_mode: host
    ...
```

Then restart:
```bash
docker compose down
docker compose up -d
```

---

## 📊 Dashboard Tabs Explained

### **Health Check Tab**
- Enter a switch IP address
- Select vendor (auto-detect available)
- Shows real-time CPU, Memory, Fan, Power, Temperature data

### **Configuration Tab**
- Browse 5 pre-built configuration templates
- Generate command configs without applying them
- (Apply feature coming soon)

### **Help & Support Tab**
- Troubleshooting guide
- Switch configuration details
- Common error solutions

### **API Tab**
- Link to Swagger UI (/docs)
- Full API endpoint reference

---

## ✅ Next Steps

1. **Verify Network Connectivity**
   - Can your host machine reach 192.168.101.212?
   - Can you SSH to that IP with the provided credentials?

2. **Check Switch Configuration**
   - Is SSH enabled on the switches?
   - Are the credentials correct?
   - Can the switch network route back to your Docker host?

3. **Enable Debug Logging**
   ```bash
   # Edit docker-compose.yml and change APP_DEBUG to true
   # Then rebuild: docker compose up --build -d
   docker logs switch-health-dashboard -f
   ```

4. **Test with Mock Data** (coming soon)
   - We can add test endpoints that don't require actual switches

---

## 🎓 Architecture Reminder

```
Your Computer
    ↓
http://localhost:8787 (Dashboard UI)
    ↓
FastAPI Backend (Port 8787)
    ↓
Network Layer (Docker Network)
    ↓
Switch at 192.168.101.212 (SSH Port 22)
```

For the dashboard to work, each hop must succeed.

---

## 💬 Still Having Issues?

Check the logs for specific error messages:
```bash
docker logs switch-health-dashboard | grep -i "error"
```

Common log indicators:
- `NetmikoAuthenticationException` → Wrong credentials
- `NetmikoTimeoutException` → Can't reach switch
- `Connection refused` → SSH port not open

---

**Your v2 Dashboard is ready! Just needs network/credential verification.** ✅
